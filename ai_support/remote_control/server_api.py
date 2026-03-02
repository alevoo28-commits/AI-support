from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from ai_support.core.ip_pool_mysql import (
    fetch_assigned_ipv4_from_mysql,
    fetch_candidate_ipv4_pool_from_mysql,
    mysql_enabled,
    register_user_ipv4_in_mysql,
)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def _db_path() -> str:
    return _env("AI_SUPPORT_REMOTE_CONTROL_DB", os.path.join(os.getcwd(), "remote_control.db")) or "remote_control.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), timeout=8, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agents (
              agent_id TEXT PRIMARY KEY,
              hostname TEXT,
              user_key TEXT,
              last_seen REAL,
              meta_json TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
              job_id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              job_type TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL,
              result_json TEXT,
              error_text TEXT,
              FOREIGN KEY(agent_id) REFERENCES agents(agent_id)
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_agent_status ON jobs(agent_id, status, created_at);")
        conn.commit()
    finally:
        conn.close()


@dataclass(frozen=True)
class AuthContext:
    is_admin: bool


def _check_agent_token(x_ai_support_agent_token: Optional[str]) -> None:
    expected = _env("AI_SUPPORT_AGENT_TOKEN")
    if not expected:
        raise RuntimeError("Falta AI_SUPPORT_AGENT_TOKEN en el servidor de control remoto")
    got = (x_ai_support_agent_token or "").strip()
    if not got or got != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _check_admin_token(x_ai_support_admin_token: Optional[str]) -> None:
    expected = _env("AI_SUPPORT_ADMIN_TOKEN")
    if not expected:
        raise RuntimeError("Falta AI_SUPPORT_ADMIN_TOKEN en el servidor de control remoto")
    got = (x_ai_support_admin_token or "").strip()
    if not got or got != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def agent_auth(x_ai_support_agent_token: Optional[str] = Header(default=None)) -> None:
    _check_agent_token(x_ai_support_agent_token)


def admin_auth(x_ai_support_admin_token: Optional[str] = Header(default=None)) -> AuthContext:
    _check_admin_token(x_ai_support_admin_token)
    return AuthContext(is_admin=True)


app = FastAPI(title="AI Support Remote Control API", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    _init_db()


class AgentRegisterRequest(BaseModel):
    agent_id: str = Field(..., min_length=3, max_length=128)
    hostname: str = Field(default="", max_length=256)
    user_key: str = Field(default="", max_length=256)
    meta: dict[str, Any] = Field(default_factory=dict)


class JobCreateRequest(BaseModel):
    agent_id: str = Field(..., min_length=3, max_length=128)
    job_type: str = Field(..., min_length=3, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)


class JobReportRequest(BaseModel):
    job_id: str = Field(..., min_length=6, max_length=128)
    ok: bool = True
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "ts": time.time()}


@app.post("/agent/register")
def register_agent(req: AgentRegisterRequest, _: None = Depends(agent_auth)) -> dict[str, Any]:
    now = time.time()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agents(agent_id, hostname, user_key, last_seen, meta_json)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
              hostname=excluded.hostname,
              user_key=excluded.user_key,
              last_seen=excluded.last_seen,
              meta_json=excluded.meta_json
            """,
            (req.agent_id.strip(), req.hostname.strip(), req.user_key.strip(), now, json.dumps(req.meta or {})),
        )
        conn.commit()
        return {"ok": True, "agent_id": req.agent_id, "ts": now}
    finally:
        conn.close()


@app.get("/agent/poll")
def poll(agent_id: str, _: None = Depends(agent_auth)) -> dict[str, Any]:
    agent_id = (agent_id or "").strip()
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id requerido")

    now = time.time()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE agents SET last_seen=? WHERE agent_id=?", (now, agent_id))

        # Seleccionar el job pendiente más antiguo
        cur.execute(
            """
            SELECT job_id, job_type, payload_json
            FROM jobs
            WHERE agent_id=? AND status='queued'
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (agent_id,),
        )
        row = cur.fetchone()
        if not row:
            conn.commit()
            return {"job": None}

        job_id = str(row["job_id"])
        job_type = str(row["job_type"])
        payload = json.loads(row["payload_json"] or "{}")

        cur.execute(
            "UPDATE jobs SET status='in_progress', updated_at=? WHERE job_id=?",
            (now, job_id),
        )
        conn.commit()

        return {"job": {"job_id": job_id, "job_type": job_type, "payload": payload}}
    finally:
        conn.close()


@app.post("/agent/report")
def report(req: JobReportRequest, _: None = Depends(agent_auth)) -> dict[str, Any]:
    now = time.time()
    conn = _connect()
    try:
        cur = conn.cursor()
        # Obtener agent_id del job para poder (opcionalmente) registrar IP al usuario.
        cur.execute("SELECT agent_id FROM jobs WHERE job_id=?", (req.job_id.strip(),))
        job_row = cur.fetchone()
        agent_id = str(job_row[0]) if job_row and job_row[0] else ""
        cur.execute(
            """
            UPDATE jobs
            SET status=?, updated_at=?, result_json=?, error_text=?
            WHERE job_id=?
            """,
            (
                "done" if req.ok else "error",
                now,
                json.dumps(req.result or {}),
                (req.error or "").strip()[:4000],
                req.job_id.strip(),
            ),
        )

        # Si el job fue exitoso y reporta una IP nueva, intentamos registrarla en MySQL (best-effort).
        # Requiere:
        # - agente registrado con user_key
        # - MySQL habilitado y query AI_SUPPORT_MYSQL_REGISTER_USER_IP_QUERY correcta
        try:
            if req.ok and isinstance(req.result, dict):
                new_ip = str(req.result.get("new_ip") or "").strip()
                changed = bool(req.result.get("changed", False))
                if changed and new_ip and agent_id and mysql_enabled():
                    cur.execute("SELECT user_key FROM agents WHERE agent_id=?", (agent_id,))
                    arow = cur.fetchone()
                    user_key = str(arow[0]) if arow and arow[0] else ""
                    if user_key:
                        # Ejecuta fuera de SQL transaction de sqlite? lo dejamos aquí como best-effort.
                        register_user_ipv4_in_mysql(user_key=user_key, ip=new_ip)
        except Exception:
            # No rompe el reporte; queda en result_json/error_text
            pass

        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.get("/admin/job/{job_id}")
def get_job(job_id: str, _: AuthContext = Depends(admin_auth)) -> dict[str, Any]:
    job_id = (job_id or "").strip()
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id requerido")

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT job_id, agent_id, job_type, status, created_at, updated_at, result_json, error_text
            FROM jobs WHERE job_id=?
            """,
            (job_id,),
        )
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="job no encontrado")
        return {
            "job": {
                "job_id": r["job_id"],
                "agent_id": r["agent_id"],
                "job_type": r["job_type"],
                "status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "result": json.loads(r["result_json"] or "{}") if r["result_json"] else None,
                "error": r["error_text"],
            }
        }
    finally:
        conn.close()


@app.post("/admin/job")
def create_job(req: JobCreateRequest, _: AuthContext = Depends(admin_auth)) -> dict[str, Any]:
    now = time.time()
    job_id = f"job_{uuid.uuid4().hex}"

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO jobs(job_id, agent_id, job_type, payload_json, status, created_at, updated_at)
            VALUES(?, ?, ?, ?, 'queued', ?, ?)
            """,
            (job_id, req.agent_id.strip(), req.job_type.strip(), json.dumps(req.payload or {}), now, now),
        )
        conn.commit()
        return {"ok": True, "job_id": job_id}
    finally:
        conn.close()


@app.get("/admin/agents")
def list_agents(_: AuthContext = Depends(admin_auth)) -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT agent_id, hostname, user_key, last_seen, meta_json FROM agents ORDER BY last_seen DESC")
        rows = cur.fetchall() or []
        agents: list[dict[str, Any]] = []
        for r in rows:
            agents.append(
                {
                    "agent_id": r["agent_id"],
                    "hostname": r["hostname"],
                    "user_key": r["user_key"],
                    "last_seen": r["last_seen"],
                    "meta": json.loads(r["meta_json"] or "{}"),
                }
            )
        return {"agents": agents}
    finally:
        conn.close()


@app.get("/admin/jobs")
def list_jobs(agent_id: Optional[str] = None, _: AuthContext = Depends(admin_auth)) -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        if agent_id and agent_id.strip():
            cur.execute(
                """
                SELECT job_id, agent_id, job_type, status, created_at, updated_at, result_json, error_text
                FROM jobs WHERE agent_id=? ORDER BY created_at DESC LIMIT 200
                """,
                (agent_id.strip(),),
            )
        else:
            cur.execute(
                """
                SELECT job_id, agent_id, job_type, status, created_at, updated_at, result_json, error_text
                FROM jobs ORDER BY created_at DESC LIMIT 200
                """
            )
        rows = cur.fetchall() or []
        jobs: list[dict[str, Any]] = []
        for r in rows:
            jobs.append(
                {
                    "job_id": r["job_id"],
                    "agent_id": r["agent_id"],
                    "job_type": r["job_type"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "result": json.loads(r["result_json"] or "{}") if r["result_json"] else None,
                    "error": r["error_text"],
                }
            )
        return {"jobs": jobs}
    finally:
        conn.close()


@app.get("/agent/ip-pool")
def ip_pool(limit: int = 2000, _: None = Depends(agent_auth)) -> dict[str, Any]:
    """Devuelve pool de IPs candidatas y el set de IPs ya asignadas.

    El cliente puede elegir una IP libre (probando con ping local) y aplicarla.
    """
    try:
        candidates = fetch_candidate_ipv4_pool_from_mysql(limit=int(limit))
        assigned = sorted(fetch_assigned_ipv4_from_mysql())
        return {"candidates": candidates, "assigned": assigned}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo obtener pool: {e}")
