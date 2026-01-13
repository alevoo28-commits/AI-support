from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional

import ipaddress

from ai_support.core.local_powershell import ensure_ipv4


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


def _iter_ipv4_from_rows(rows: Iterable[object]) -> set[str]:
    out: set[str] = set()
    for r in rows:
        if r is None:
            continue
        ip_raw: Optional[str]
        if isinstance(r, (list, tuple)) and r:
            ip_raw = str(r[0] or "").strip()
        else:
            ip_raw = str(r).strip()
        if not ip_raw:
            continue
        try:
            out.add(ensure_ipv4(ip_raw))
        except Exception:
            # Silencioso: la tabla puede contener valores no IPv4
            continue
    return out


def fetch_assigned_ipv4_from_mysql(
    *,
    query: Optional[str] = None,
    limit: int = 10000,
) -> set[str]:
    """Obtiene IPs ya asignadas/registradas en MySQL.

    Por defecto usa env `AI_SUPPORT_MYSQL_ASSIGNED_IPS_QUERY`.
    Si no está configurada, intenta un default razonable para `personal.IP`.

    Recomendación: define explícitamente el query en env para ajustarse a tu esquema.

    Ejemplo:
    AI_SUPPORT_MYSQL_ASSIGNED_IPS_QUERY=SELECT IP FROM personal WHERE IP IS NOT NULL AND IP <> ''
    """

    q = (
        _env("AI_SUPPORT_MYSQL_ASSIGNED_IPS_QUERY", query)
        or query
        or "SELECT IP FROM personal WHERE IP IS NOT NULL AND IP <> ''"
    )

    if "limit" not in q.lower():
        q = f"{q} LIMIT {int(limit)}"

    conn = _mysql_connect()
    try:
        cur = conn.cursor()
        try:
            cur.execute(q)
            rows = cur.fetchall() or []
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

    return _iter_ipv4_from_rows(rows)


def fetch_candidate_ipv4_pool_from_mysql(
    *,
    query: Optional[str] = None,
    limit: int = 20000,
) -> list[str]:
    """Obtiene el pool de IPs candidatas desde MySQL.

    Debe devolver una columna con IPv4 (una IP por fila).

    Env:
      - AI_SUPPORT_MYSQL_IP_POOL_QUERY

    Si no se define query, levanta error (para evitar asumir tablas).
    """

    q = _env("AI_SUPPORT_MYSQL_IP_POOL_QUERY", query) or query
    if not q:
        # Fallback: pool definido por entorno (sin tabla MySQL)
        pool = _candidate_pool_from_env()
        if pool:
            return pool
        raise RuntimeError(
            "Falta pool de IPs candidatas. Define AI_SUPPORT_MYSQL_IP_POOL_QUERY (MySQL) "
            "o AI_SUPPORT_IP_POOL_CIDR / AI_SUPPORT_IP_POOL_RANGE_START+END (env)."
        )

    if "limit" not in q.lower():
        q = f"{q} LIMIT {int(limit)}"

    conn = _mysql_connect()
    try:
        cur = conn.cursor()
        try:
            cur.execute(q)
            rows = cur.fetchall() or []
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

    ips = sorted(_iter_ipv4_from_rows(rows))
    return ips


def _candidate_pool_from_env() -> list[str]:
    """Genera IPs candidatas desde env, sin depender de una tabla.

    Soporta:
    - AI_SUPPORT_IP_POOL_CIDR     (ej. 172.17.87.0/24)
    - AI_SUPPORT_IP_POOL_RANGE_START / AI_SUPPORT_IP_POOL_RANGE_END (ej. 172.17.87.50 .. 172.17.87.200)
    """

    cidr = (_env("AI_SUPPORT_IP_POOL_CIDR") or "").strip()
    if cidr:
        try:
            net = ipaddress.ip_network(cidr, strict=False)
            if net.version != 4:
                return []
            # hosts() excluye red/broadcast
            return [str(ip) for ip in net.hosts()]
        except Exception:
            return []

    start = (_env("AI_SUPPORT_IP_POOL_RANGE_START") or "").strip()
    end = (_env("AI_SUPPORT_IP_POOL_RANGE_END") or "").strip()
    if start and end:
        try:
            s = ipaddress.ip_address(ensure_ipv4(start))
            e = ipaddress.ip_address(ensure_ipv4(end))
            if int(e) < int(s):
                s, e = e, s
            out: list[str] = []
            cur = int(s)
            last = int(e)
            # límite defensivo
            if (last - cur) > 65536:
                return []
            while cur <= last:
                out.append(str(ipaddress.ip_address(cur)))
                cur += 1
            return out
        except Exception:
            return []

    return []


def register_user_ipv4_in_mysql(
    *,
    user_key: str,
    ip: str,
    query: Optional[str] = None,
) -> int:
    """Registra la IP asignada al usuario en MySQL.

    Para no asumir esquema, esta operación se habilita por env/query.

    Env:
      - AI_SUPPORT_MYSQL_REGISTER_USER_IP_QUERY

        La query debe ser parametrizada con %s (primero IP, luego user_key), por ejemplo:
            UPDATE personal SET IP=%s WHERE email=%s

    Retorna rows afectadas.
    """

    q = (
        _env("AI_SUPPORT_MYSQL_REGISTER_USER_IP_QUERY", query)
        or query
        or "UPDATE personal SET IP=%s WHERE email=%s"
    )

    user_key = (user_key or "").strip()
    if not user_key:
        raise ValueError("user_key vacío")

    ip = ensure_ipv4(ip)

    conn = _mysql_connect()
    try:
        cur = conn.cursor()
        try:
            cur.execute(q, (ip, user_key))
            conn.commit()
            return int(cur.rowcount or 0)
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
