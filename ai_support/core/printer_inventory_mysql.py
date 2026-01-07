from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PrinterRecord:
    nombre: str
    ip: str
    nombre_departamento: str
    ubicacion: str


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    import os

    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def mysql_enabled() -> bool:
    raw = (_env("AI_SUPPORT_MYSQL_ENABLE", "false") or "false").lower()
    return raw in {"1", "true", "yes", "y", "on"}


def fetch_printers_from_mysql(
    *,
    query: str = "SELECT nombre, ip, nombre_departamento, ubicacion FROM impresoras",
    limit: int = 500,
) -> list[PrinterRecord]:
    """Obtiene impresoras desde MySQL.

    Config por env:
    - AI_SUPPORT_MYSQL_HOST
    - AI_SUPPORT_MYSQL_PORT (default 3306)
    - AI_SUPPORT_MYSQL_USER
    - AI_SUPPORT_MYSQL_PASSWORD
    - AI_SUPPORT_MYSQL_DATABASE

    Nota: el query por defecto asume una tabla `impresoras`.
    Si tu tabla/vista se llama diferente, cambia AI_SUPPORT_MYSQL_PRINTERS_QUERY.
    """

    if not mysql_enabled():
        raise RuntimeError("MySQL deshabilitado (AI_SUPPORT_MYSQL_ENABLE=false)")

    host = _env("AI_SUPPORT_MYSQL_HOST")
    user = _env("AI_SUPPORT_MYSQL_USER")
    password = _env("AI_SUPPORT_MYSQL_PASSWORD")
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

    try:
        import mysql.connector  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Falta dependencia mysql-connector-python. Instala requirements."
        ) from e

    q = _env("AI_SUPPORT_MYSQL_PRINTERS_QUERY", query) or query

    # Aplicar límite simple si el query no lo trae
    if "limit" not in q.lower():
        q = f"{q} LIMIT {int(limit)}"

    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connection_timeout=8,
    )
    try:
        cur = conn.cursor()
        cur.execute(q)
        rows = cur.fetchall() or []
    finally:
        try:
            conn.close()
        except Exception:
            pass

    out: list[PrinterRecord] = []
    for r in rows:
        try:
            nombre, ip, nombre_departamento, ubicacion = r
        except Exception:
            continue
        out.append(
            PrinterRecord(
                nombre=str(nombre or "").strip(),
                ip=str(ip or "").strip(),
                nombre_departamento=str(nombre_departamento or "").strip(),
                ubicacion=str(ubicacion or "").strip(),
            )
        )

    # Filtrar registros sin IP
    return [p for p in out if p.ip]
