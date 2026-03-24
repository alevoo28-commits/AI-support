"""
Configuración de UI y mapeo de departamentos a áreas.

Este módulo gestiona:
- Normalización de claves y nombres
- Mapeo de departamentos a áreas
- Configuración por entorno
"""

import os
import json
import re


def normalize_key(value: str) -> str:
    """Normaliza keys eliminando espacios, caracteres especiales y convirtiendo a minúsculas."""
    value = (value or "").strip().lower()
    value = re.sub(r"\s+", "_", value)
    return re.sub(r"[^a-z0-9_]", "", value)


def allowed_area_ids() -> set[str]:
    """Retorna el conjunto de IDs de áreas permitidas en el sistema."""
    return {
        "tesoreria",
        "arquitectura",
        "infraestructura",
        "proyectos",
        "atencion_alumnos",
        "postgrado",
        "sustentabilidad",
        "comunicaciones",
        "vinculacion",
        "rrhh",
        "contabilidad",
        "direccion_economica",
        "direccion_academica",
        "diversidad",
        "decanato",
    }


def department_env_map() -> dict[str, str]:
    """Mapeo de departamento a área configurable por entorno.

    Soporta dos formatos:
    - AI_SUPPORT_DEPARTMENT_AREA_MAP_JSON='{"informatica":"infraestructura"}'
    - AI_SUPPORT_DEPARTMENT_AREA_MAP='informatica=infraestructura;aranceles=tesoreria'
    """
    result: dict[str, str] = {}
    allowed = allowed_area_ids()

    raw_json = (os.getenv("AI_SUPPORT_DEPARTMENT_AREA_MAP_JSON") or "").strip()
    if raw_json:
        try:
            payload = json.loads(raw_json)
            if isinstance(payload, dict):
                for k, v in payload.items():
                    nk = normalize_key(str(k))
                    nv = normalize_key(str(v))
                    if nk and nv in allowed:
                        result[nk] = nv
        except Exception:
            pass

    raw_pairs = (os.getenv("AI_SUPPORT_DEPARTMENT_AREA_MAP") or "").strip()
    if raw_pairs:
        for item in raw_pairs.split(";"):
            pair = item.strip()
            if not pair or "=" not in pair:
                continue
            left, right = pair.split("=", 1)
            nk = normalize_key(left)
            nv = normalize_key(right)
            if nk and nv in allowed:
                result[nk] = nv

    return result


def department_name_to_area_id(department_name: str | None) -> str | None:
    """Convierte el nombre de un departamento a su ID de área asociada."""
    key = normalize_key(department_name or "")
    if not key:
        return None

    env_map = department_env_map()
    if key in env_map:
        return env_map.get(key)

    aliases = {
        "tesoreria": "tesoreria",
        "arquitectura": "arquitectura",
        "infraestructura": "infraestructura",
        "informatica": "infraestructura",
        "unidad_de_informatica": "infraestructura",
        "cec": "infraestructura",
        "centro_de_computacion": "infraestructura",
        "centro_de_computacion_cec": "infraestructura",
        "prevencion_de_riesgos": "infraestructura",
        "administracion_de_campus": "infraestructura",
        "proyectos": "proyectos",
        "centro_de_energia": "proyectos",
        "centro_de_biotecnologia_y_bioingenieria": "proyectos",
        "centro_de_modelamiento_matematico": "proyectos",
        "centro_sismologico_nacional": "proyectos",
        "amtc": "proyectos",
        "atencion_alumnos": "atencion_alumnos",
        "atencion_de_alumnos": "atencion_alumnos",
        "secretaria_de_estudio": "direccion_academica",
        "escuela_de_ingenieria": "direccion_academica",
        "escuela_de_ingenieria_y_ciencias": "direccion_academica",
        "escuela_de_verano": "direccion_academica",
        "postgrado": "postgrado",
        "sustentabilidad": "sustentabilidad",
        "comunicaciones": "comunicaciones",
        "vinculacion": "vinculacion",
        "vinculacion_externa": "vinculacion",
        "relaciones_institucionales": "vinculacion",
        "dirvex": "vinculacion",
        "rrhh": "rrhh",
        "recursos_humanos": "rrhh",
        "administracion": "rrhh",
        "adquisiciones": "rrhh",
        "desarrollo_organizacional": "rrhh",
        "contabilidad": "contabilidad",
        "aranceles": "tesoreria",
        "direccion_economica": "direccion_economica",
        "direconimica": "direccion_economica",
        "dir_econimica": "direccion_economica",
        "direccion_academica": "direccion_academica",
        "diversidad": "diversidad",
        "decanato": "decanato",
        "vicedecanato": "decanato",
        "juridica": "decanato",
        "otros": "decanato",
    }
    if key in aliases:
        return aliases.get(key)

    # Heurística para nombres institucionales largos (ej: unidad_de_tesoreria)
    compact = key
    compact = compact.replace("unidad_de_", "")
    compact = compact.replace("unidad_", "")
    compact = compact.replace("direccion_de_", "")
    compact = compact.replace("direccion_", "")
    compact = compact.replace("escuela_de_", "")

    if "tesorer" in compact:
        return "tesoreria"
    if "arquitect" in compact:
        return "arquitectura"
    if "infraestructura" in compact:
        return "infraestructura"
    if "informat" in compact:
        return "infraestructura"
    if compact == "cec" or "computacion" in compact:
        return "infraestructura"
    if "proyecto" in compact:
        return "proyectos"
    if compact.startswith("departamento_de_"):
        return "direccion_academica"
    if compact.startswith("centro_de_"):
        return "proyectos"
    if "alumno" in compact or "estudiant" in compact:
        return "atencion_alumnos"
    if "postgrado" in compact or "posgrado" in compact:
        return "postgrado"
    if "sustentab" in compact or "sostenib" in compact:
        return "sustentabilidad"
    if "comunic" in compact:
        return "comunicaciones"
    if "vincul" in compact:
        return "vinculacion"
    if "rrhh" in compact or "recurso_humano" in compact:
        return "rrhh"
    if "contabil" in compact:
        return "contabilidad"
    if "econom" in compact:
        return "direccion_economica"
    if "academ" in compact:
        return "direccion_academica"
    if "divers" in compact or "genero" in compact:
        return "diversidad"
    if "decan" in compact:
        return "decanato"

    fallback = normalize_key((os.getenv("AI_SUPPORT_DEPARTMENT_FALLBACK_AREA") or "").strip())
    if fallback in allowed_area_ids():
        return fallback

    return None


def department_matches_area_name(department_name: str | None, area_name: str | None) -> bool:
    """Verifica si un nombre de departamento coincide con un nombre de área."""
    dept = normalize_key(department_name or "")
    area = normalize_key(area_name or "")
    if not dept or not area:
        return False
    return dept == area or dept in area or area in dept


def department_catalog_seed_area_ids(department_name: str | None) -> list[str]:
    """Busca áreas semilla asociadas al departamento desde knowledge_base/departments.json."""
    dept_key = normalize_key(department_name or "")
    if not dept_key:
        return []

    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dep_path = os.path.join(base, "knowledge_base", "departments.json")
        if not os.path.exists(dep_path):
            return []

        with open(dep_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            return []

        seeds: list[str] = []
        for meta in payload.values():
            if not isinstance(meta, dict):
                continue
            name = normalize_key(str(meta.get("name") or ""))
            if name != dept_key:
                continue
            mapped = str(meta.get("mapped_area_id") or "").strip()
            if mapped:
                seeds.append(mapped)
        return seeds
    except Exception:
        return []


def extract_ipv4(text: str) -> str | None:
    """Extrae una dirección IPv4 de un texto."""
    ipv4_regex = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")
    m = ipv4_regex.search(text or "")
    if not m:
        return None
    return m.group(0)
