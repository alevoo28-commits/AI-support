from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class MySQLConnConfig:
    host: str
    user: str
    password: str
    database: str
    port: int = 3306


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def mysql_enabled() -> bool:
    raw = (_env("AI_SUPPORT_MYSQL_ENABLE", "false") or "false").lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _mysql_conn_config() -> MySQLConnConfig:
    host = _env("AI_SUPPORT_MYSQL_HOST")
    user = _env("AI_SUPPORT_MYSQL_USER")
    password = os.getenv("AI_SUPPORT_MYSQL_PASSWORD")
    database = _env("AI_SUPPORT_MYSQL_DATABASE")

    port_raw = _env("AI_SUPPORT_MYSQL_PORT", "3306")
    try:
        port = int(port_raw or "3306")
    except Exception:
        port = 3306

    if not host or not user or password is None or not database:
        raise RuntimeError(
            "Faltan variables MySQL: AI_SUPPORT_MYSQL_HOST/USER/PASSWORD/DATABASE"
        )

    return MySQLConnConfig(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
    )


def _mysql_connect():
    if not mysql_enabled():
        raise RuntimeError("MySQL deshabilitado (AI_SUPPORT_MYSQL_ENABLE=false)")

    try:
        import mysql.connector  # type: ignore
    except Exception as e:
        raise RuntimeError("Falta dependencia mysql-connector-python. Instala requirements.") from e

    cfg = _mysql_conn_config()
    return mysql.connector.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        connection_timeout=8,
    )


def _users_table() -> str:
    t = (_env("AI_SUPPORT_MYSQL_USERS_TABLE", "personal") or "personal").strip()
    # sanitizar simple
    safe = "".join(c for c in t if c.isalnum() or c == "_")
    return safe or "personal"


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    email = (email or "").strip().lower()
    if not email:
        raise ValueError("email vacío")

    table = _users_table()
    conn = _mysql_connect()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                f"SELECT id, nombre, apellido, apellido_2, rut, departamento_id, tui, email, IP "
                f"FROM `{table}` WHERE email=%s LIMIT 1",
                (email,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            try:
                cur.close()
            except Exception:
                pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def upsert_user_by_email(
    *,
    email: str,
    nombre: Optional[str] = None,
    apellido: Optional[str] = None,
    apellido_2: Optional[str] = None,
    rut: Optional[str] = None,
    departamento_id: Optional[int] = None,
    tui: Optional[str] = None,
) -> dict[str, Any]:
    """Crea el usuario si no existe, o actualiza campos si ya existe.

    Asume un esquema tipo:
      usuarios(id, nombre, apellido, departamento_id, apellido_2, rut, nom_ape_ape2, fecha, tui, email, IP)

    Solo actualiza campos provistos (no pisa con vacío/None).
    """

    email_n = (email or "").strip().lower()
    if not email_n:
        raise ValueError("email vacío")

    nombre_v = (nombre or "").strip() or None
    apellido_v = (apellido or "").strip() or None
    apellido2_v = (apellido_2 or "").strip() or None
    rut_v = (rut or "").strip() or None
    tui_v = (tui or "").strip() or None

    # nom_ape_ape2: best-effort
    parts = [p for p in [nombre_v, apellido_v, apellido2_v] if p]
    nom_ape_ape2 = " ".join(parts) if parts else None

    table = _users_table()

    existing = get_user_by_email(email_n)

    conn = _mysql_connect()
    try:
        cur = conn.cursor()
        try:
            if not existing:
                cols: list[str] = ["email", "fecha"]
                vals: list[Any] = [email_n]
                placeholders: list[str] = ["%s", "CURDATE()"]

                def add(col: str, value: Any):
                    nonlocal cols, vals, placeholders
                    if value is None:
                        return
                    cols.append(col)
                    vals.append(value)
                    placeholders.append("%s")

                add("nombre", nombre_v)
                add("apellido", apellido_v)
                add("apellido_2", apellido2_v)
                add("rut", rut_v)
                add("departamento_id", int(departamento_id) if departamento_id is not None else None)
                add("tui", tui_v)
                add("nom_ape_ape2", nom_ape_ape2)

                q = (
                    f"INSERT INTO `{table}` (" + ",".join(f"`{c}`" for c in cols) + ") "
                    f"VALUES (" + ",".join(placeholders) + ")"
                )
                cur.execute(q, tuple(vals))
                conn.commit()
            else:
                sets: list[str] = []
                vals_u: list[Any] = []

                def set_if(col: str, value: Any):
                    nonlocal sets, vals_u
                    if value is None:
                        return
                    sets.append(f"`{col}`=%s")
                    vals_u.append(value)

                set_if("nombre", nombre_v)
                set_if("apellido", apellido_v)
                set_if("apellido_2", apellido2_v)
                set_if("rut", rut_v)
                if departamento_id is not None:
                    set_if("departamento_id", int(departamento_id))
                set_if("tui", tui_v)
                set_if("nom_ape_ape2", nom_ape_ape2)

                if sets:
                    q = f"UPDATE `{table}` SET {', '.join(sets)} WHERE email=%s"
                    vals_u.append(email_n)
                    cur.execute(q, tuple(vals_u))
                    conn.commit()

        finally:
            try:
                cur.close()
            except Exception:
                pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # devolver el estado actualizado
    row = get_user_by_email(email_n)
    return row or {"email": email_n}
