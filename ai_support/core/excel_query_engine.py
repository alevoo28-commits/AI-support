from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any, Callable, Iterable, Optional

import pandas as pd


def _norm_text(value: str) -> str:
    """Normaliza texto para matching (minúsculas, sin tildes, espacios colapsados)."""
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s+", " ", value)
    return value


def _best_match(needle: str, haystack: Iterable[str]) -> str | None:
    """Devuelve el mejor match por similitud aproximada (stdlib-only)."""
    needle_n = _norm_text(needle)
    if not needle_n:
        return None

    best: tuple[float, str] | None = None
    for cand in haystack:
        cand_n = _norm_text(str(cand))
        if not cand_n:
            continue
        # Score rápido: contains > prefix > token overlap > fallback
        score = 0.0
        if needle_n == cand_n:
            score = 1.0
        elif needle_n in cand_n or cand_n in needle_n:
            score = 0.92
        elif cand_n.startswith(needle_n) or needle_n.startswith(cand_n):
            score = 0.85
        else:
            # token overlap
            nset = set(needle_n.split())
            cset = set(cand_n.split())
            inter = len(nset & cset)
            union = len(nset | cset) or 1
            score = inter / union

        if best is None or score > best[0]:
            best = (score, str(cand))

    if best is None:
        return None
    if best[0] < 0.34:
        return None
    return best[1]


def _score_column_against_question(column_name: str, question: str) -> float:
    """Score simple de relevancia de una columna respecto a la pregunta."""
    q = _norm_text(question)
    c = _norm_text(column_name)
    if not q or not c:
        return 0.0
    if c == q:
        return 1.0
    if c in q:
        return 0.95
    # token overlap
    cset = set(c.split())
    qset = set(q.split())
    inter = len(cset & qset)
    union = len(cset | qset) or 1
    return inter / union


def _infer_relevant_columns(df: pd.DataFrame, question: str, *, max_cols: int = 2) -> list[str]:
    """Infiera columnas mencionadas en la pregunta (best-effort)."""
    cols = [str(c) for c in df.columns]
    scored = [(float(_score_column_against_question(c, question)), c) for c in cols if not str(c).startswith("_")]
    scored.sort(key=lambda x: x[0], reverse=True)
    picked: list[str] = []
    for score, col in scored:
        if score < 0.20:
            continue
        picked.append(col)
        if len(picked) >= max_cols:
            break
    return picked


def _is_numeric_enough(series: pd.Series) -> bool:
    s = pd.to_numeric(series, errors="coerce")
    return int(s.notna().sum()) > 0


def _make_arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Reduce problemas de serialización Arrow en Streamlit.

    Normaliza columnas object/mix a dtype string.
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    for col in out.columns:
        try:
            if out[col].dtype == object:
                out[col] = out[col].astype("string")
        except Exception:
            try:
                out[col] = out[col].map(lambda x: None if pd.isna(x) else str(x)).astype("string")
            except Exception:
                pass
    return out


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    dtype: str
    example_values: list[str]


@dataclass(frozen=True)
class SheetProfile:
    name: str
    nrows: int
    ncols: int
    columns: list[ColumnProfile]


@dataclass
class WorkbookIndex:
    """Excel/CSV multi-hoja listo para consulta sin enviar datos al LLM."""

    sheets: dict[str, pd.DataFrame]
    profiles: dict[str, SheetProfile]

    @staticmethod
    def from_bytes(filename: str, data: bytes) -> "WorkbookIndex":
        ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()

        if ext == "csv":
            df = _read_csv_best_effort(BytesIO(data))
            sheets = {"CSV": df}
        elif ext in {"xlsx", "xls"}:
            sheets = _read_excel_all_sheets(BytesIO(data))
        else:
            # Intentar como Excel primero, luego CSV
            try:
                sheets = _read_excel_all_sheets(BytesIO(data))
            except Exception:
                sheets = {"DATA": _read_csv_best_effort(BytesIO(data))}

        profiles: dict[str, SheetProfile] = {}
        for sheet_name, df in sheets.items():
            profiles[sheet_name] = _profile_sheet(sheet_name, df)

        return WorkbookIndex(sheets=sheets, profiles=profiles)

    def list_sheets(self) -> list[str]:
        return list(self.sheets.keys())

    def schema_summary(self, max_values_per_column: int = 4) -> str:
        """Resumen compacto para planificación (tokens bajos)."""
        parts: list[str] = []
        for sheet_name in self.list_sheets():
            prof = self.profiles.get(sheet_name)
            if not prof:
                continue
            parts.append(f"- Hoja: {prof.name} (filas={prof.nrows}, cols={prof.ncols})")
            for col in prof.columns[:60]:
                examples = col.example_values[:max_values_per_column]
                ex = ", ".join(examples)
                if ex:
                    parts.append(f"  - {col.name} [{col.dtype}] ejemplos: {ex}")
                else:
                    parts.append(f"  - {col.name} [{col.dtype}]")
        return "\n".join(parts)


@dataclass(frozen=True)
class FilterSpec:
    column: str
    op: str  # eq|contains|in|gt|gte|lt|lte
    value: Any


@dataclass(frozen=True)
class SortSpec:
    column: str
    asc: bool = True


@dataclass(frozen=True)
class QueryPlan:
    target_sheets: list[str] | str  # "auto" | "all" | ["Sheet1", ...]
    select: list[str] | str  # "auto" | ["col", ...]
    filters: list[FilterSpec]
    group_by: list[str]
    order_by: list[SortSpec]
    limit: int
    output: dict[str, Any]


_DEFAULT_PLAN = QueryPlan(
    target_sheets="auto",
    select="auto",
    filters=[],
    group_by=[],
    order_by=[],
    limit=200,
    output={"format": "table"},
)


def heuristic_plan(index: WorkbookIndex, question: str) -> QueryPlan | None:
    """Heurística para casos comunes sin usar LLM (tokens=0)."""
    q = _norm_text(question)
    if not q:
        return None

    # Consultas analíticas típicas (tokens=0): sumas, moda, duplicados, etc.
    analysis_op: str | None = None
    if any(k in q for k in ["mas se repite", "más se repite", "valor mas repet", "valor más repet", "mas frecuente", "más frecuente", "moda"]):
        analysis_op = "mode"
    elif any(k in q for k in ["duplicad", "repetid", "repetidos", "repetidas", "duplicados", "duplicadas"]):
        # Ej: "códigos repetidos", "IDs duplicados"
        analysis_op = "duplicates"
    elif any(k in q for k in ["sumar", "suma", "sumatoria", "total", "totalizar"]):
        analysis_op = "sum"
    elif any(k in q for k in ["promedio", "media", "average", "mean"]):
        analysis_op = "mean"
    elif any(k in q for k in ["maximo", "máximo", "mayor", "más alto", "mas alto"]):
        analysis_op = "max"
    elif any(k in q for k in ["minimo", "mínimo", "menor", "más bajo", "mas bajo"]):
        analysis_op = "min"
    elif any(k in q for k in ["valores unicos", "valores únicos", "unicos", "únicos", "distinct", "diferentes"]):
        analysis_op = "nunique"
    elif any(k in q for k in ["contar", "cuantos", "cuántos", "cantidad", "numero de", "número de"]):
        analysis_op = "count"

    if analysis_op:
        return QueryPlan(
            target_sheets="all",
            select="auto",
            filters=[],
            group_by=[],
            order_by=[],
            limit=200,
            output={"format": "table", "analysis": {"op": analysis_op, "columns": "auto"}},
        )

    # Detectar intención típica de malla/horarios
    wants_schedule = any(k in q for k in ["horario", "hora", "bloque", "dia", "lunes", "martes", "miercoles", "jueves", "viernes", "sabado"])
    wants_courses = any(k in q for k in ["ramo", "ramos", "asignatura", "asignaturas", "curso", "cursos", "modulo", "modulos"])
    wants_career = any(k in q for k in ["carrera", "programa", "plan"])

    jornada_value: str | None = None
    if "vespert" in q:
        jornada_value = "vespert"
    elif "diurn" in q:
        jornada_value = "diurn"

    # Buscar columnas candidatas
    all_columns: dict[str, set[str]] = {}
    for sheet_name, df in index.sheets.items():
        all_columns[sheet_name] = {str(c) for c in df.columns}

    def _find_col(sheet: str, candidates: list[str]) -> str | None:
        cols = all_columns.get(sheet, set())
        for c in candidates:
            m = _best_match(c, cols)
            if m:
                return m
        return None

    # Selección y filtros por hoja (buscamos en todas las hojas, ejecutamos en union)
    select_cols: list[str] = []
    if wants_career:
        select_cols.extend(["carrera", "programa", "plan", "nombre carrera"])
    if wants_courses:
        select_cols.extend(["ramo", "asignatura", "curso", "modulo", "materia"])
    if wants_schedule:
        select_cols.extend(["horario", "hora", "dia", "bloque", "inicio", "fin", "desde", "hasta", "jornada"])

    filters: list[FilterSpec] = []

    # Jornada: aplicar como contains sobre columna jornada/turno/modalidad si existe.
    if jornada_value:
        # No sabemos la hoja aún, dejamos la columna en "auto" y resolvemos luego.
        filters.append(FilterSpec(column="jornada", op="contains", value=jornada_value))

    if not filters and not select_cols:
        return None

    return QueryPlan(
        target_sheets="all",
        select="auto" if not select_cols else select_cols,
        filters=filters,
        group_by=["carrera"] if (wants_career or wants_courses or wants_schedule) else [],
        order_by=[],
        limit=200,
        output={"format": "grouped"} if (wants_courses or wants_schedule) else {"format": "table"},
    )


def build_llm_prompt(schema_summary: str, question: str) -> str:
    return (
        "Eres un asistente experto en análisis de datos tabulares (Excel/CSV). "
        "NO inventes datos. Debes responder generando un PLAN JSON para consultar datos.\n\n"
        "Reglas:\n"
        "- Devuelve SOLO JSON válido (sin markdown, sin texto extra).\n"
        "- No incluyas filas ni contenido completo del archivo, solo el plan.\n"
        "- Usa estas operaciones: op ∈ {eq, contains, in, gt, gte, lt, lte}.\n"
        "- Para análisis (sumas, duplicados, etc.) usa output.analysis con operaciones permitidas.\n"
        "- Si el usuario pide 'mostrar', selecciona columnas relevantes.\n"
        "- Si no hay columna exacta, usa el nombre más cercano según el esquema.\n\n"
        "Esquema del workbook:\n"
        f"{schema_summary}\n\n"
        "Formato esperado:\n"
        "{\n"
        "  \"target_sheets\": \"auto\" | \"all\" | [\"Hoja\"],\n"
        "  \"select\": \"auto\" | [\"columna\", ...],\n"
        "  \"filters\": [{\"column\": \"...\", \"op\": \"...\", \"value\": ...}],\n"
        "  \"group_by\": [\"columna\"],\n"
        "  \"order_by\": [{\"column\": \"...\", \"asc\": true}],\n"
        "  \"limit\": 200,\n"
        "  \"output\": {\n"
        "    \"format\": \"table\" | \"grouped\",\n"
        "    \"analysis\": {\n"
        "      \"op\": \"sum\"|\"mean\"|\"min\"|\"max\"|\"mode\"|\"count\"|\"nunique\"|\"duplicates\"|\"value_counts\"|\"groupby_agg\",\n"
        "      \"columns\": \"auto\" | [\"col\", ...],\n"
        "      \"group_by\": \"auto\" | [\"col\", ...],\n"
        "      \"metrics\": [{\"column\": \"...\", \"agg\": \"sum\"|\"mean\"|\"min\"|\"max\"|\"count\"|\"nunique\"}]\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        "Pregunta del usuario:\n"
        f"{question}\n"
    )


def _log_unhandled_excel_request(question: str, schema_summary: str, reason: str) -> None:
    """Log best-effort de solicitudes no resueltas para mejorar capacidades.

    No interrumpe la ejecución si falla.
    """
    try:
        os.makedirs("logs", exist_ok=True)
        path = os.path.join("logs", "excel_unhandled_requests.jsonl")
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "reason": reason,
            "question": (question or "")[:2000],
            "schema_summary": (schema_summary or "")[:6000],
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}\s*$")


def parse_plan(text: str) -> QueryPlan:
    raw = (text or "").strip()
    m = _JSON_OBJECT_RE.search(raw)
    if not m:
        raise ValueError("El modelo no devolvió JSON válido.")

    payload = json.loads(m.group(0))

    target_sheets = payload.get("target_sheets", "auto")
    select = payload.get("select", "auto")

    filters_payload = payload.get("filters", [])
    filters: list[FilterSpec] = []
    if isinstance(filters_payload, list):
        for item in filters_payload:
            if not isinstance(item, dict):
                continue
            filters.append(
                FilterSpec(
                    column=str(item.get("column") or "").strip(),
                    op=str(item.get("op") or "").strip().lower(),
                    value=item.get("value"),
                )
            )

    group_by_payload = payload.get("group_by", [])
    group_by: list[str] = [str(c) for c in group_by_payload] if isinstance(group_by_payload, list) else []

    order_by_payload = payload.get("order_by", [])
    order_by: list[SortSpec] = []
    if isinstance(order_by_payload, list):
        for item in order_by_payload:
            if not isinstance(item, dict):
                continue
            order_by.append(
                SortSpec(
                    column=str(item.get("column") or "").strip(),
                    asc=bool(item.get("asc", True)),
                )
            )

    limit_raw = payload.get("limit", 200)
    try:
        limit = int(limit_raw)
    except Exception:
        limit = 200
    if limit < 1:
        limit = 200

    output_payload = payload.get("output")
    output: dict[str, Any]
    if isinstance(output_payload, dict):
        fmt = str(output_payload.get("format") or "table").strip().lower()
        if fmt not in {"table", "grouped"}:
            fmt = "table"
        output = dict(output_payload)
        output["format"] = fmt
    else:
        output = {"format": "table"}

    return QueryPlan(
        target_sheets=target_sheets,
        select=select,
        filters=filters,
        group_by=group_by,
        order_by=order_by,
        limit=limit,
        output=output,
    )


def answer_excel_question(
    index: WorkbookIndex,
    question: str,
    llm_text: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    """Responde consultas sobre workbook usando ejecución local (pandas).

    Devuelve:
    - success: bool
    - message: str
    - dataframe: pd.DataFrame | None
    - plan: dict | None
    """

    plan: QueryPlan | None = heuristic_plan(index, question)

    used_llm = False
    if plan is None and llm_text is not None:
        used_llm = True
        prompt = build_llm_prompt(index.schema_summary(), question)
        plan_text = llm_text(prompt)
        plan = parse_plan(plan_text)

    if plan is None:
        return {
            "success": False,
            "message": "No pude inferir una consulta. Prueba indicando columnas o filtros (ej: jornada=vespertina, carrera=X).",
            "dataframe": None,
            "plan": None,
            "used_llm": False,
        }

    df = _execute_plan(index, plan, question)

    grouped_markdown: str | None = None
    fmt = str((plan.output or {}).get("format") or "table").strip().lower()
    if fmt == "grouped" and not df.empty:
        grouped_markdown = _grouped_summary_markdown(df, question=question, preferred_group_by=plan.group_by)

    msg = f"Encontré {len(df)} fila(s)" + (" (plan por LLM)." if used_llm else ".")
    if fmt == "grouped" and not df.empty and not grouped_markdown:
        msg += " No pude detectar una columna clara para agrupar; mostrando resultados en tabla."
    return {
        "success": True,
        "message": msg,
        "dataframe": df,
        "grouped_markdown": grouped_markdown,
        "plan": {
            "target_sheets": plan.target_sheets,
            "select": plan.select,
            "filters": [f.__dict__ for f in plan.filters],
            "group_by": plan.group_by,
            "order_by": [o.__dict__ for o in plan.order_by],
            "limit": plan.limit,
            "output": plan.output,
        },
        "used_llm": used_llm,
    }


def _pick_semantic_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = [str(c) for c in df.columns]
    for cand in candidates:
        m = _best_match(cand, cols)
        if m:
            return m
    return None


def _extract_group_hint_from_question(question: str) -> str | None:
    """Intenta extraer una pista tipo "por X"/"agrupa por X" desde la pregunta."""
    q = _norm_text(question)
    if not q:
        return None

    # patrones simples y seguros (sin NLP pesado)
    # ejemplos: "agrupa por carrera", "por proveedor", "resumen por cliente"
    m = re.search(r"(?:agrup(?:a|ar)|resumen|agrupado)\s+por\s+([^\n\r\t\,\.\;\:]{2,60})", q)
    if not m:
        m = re.search(r"\bpor\s+([^\n\r\t\,\.\;\:]{2,60})", q)
    if not m:
        return None

    hint = (m.group(1) or "").strip()
    # cortar en conectores frecuentes
    for cut in [" y ", " con ", " de ", " del ", " para ", " donde ", " que ", " en "]:
        if cut in hint:
            hint = hint.split(cut, 1)[0].strip()
    if len(hint) < 2:
        return None
    return hint


def _is_probably_identifier_column(name: str) -> bool:
    n = _norm_text(name)
    return any(
        k in n
        for k in [
            "id",
            "uuid",
            "codigo",
            "código",
            "rut",
            "dni",
            "cedula",
            "cédula",
            "correo",
            "email",
            "telefono",
            "teléfono",
            "celular",
            "nro",
            "numero",
            "número",
            "folio",
        ]
    )


def _pick_reasonable_group_column(df: pd.DataFrame, question: str, preferred_group_by: list[str] | None = None) -> str | None:
    """Elige una columna para agrupar de forma robusta.

    Prioridades:
    1) Si la pregunta sugiere "por X", usar X.
    2) Columnas con nombres semánticos típicos (carrera, cliente, proveedor, etc.).
    3) Heurística por cardinalidad (columna categórica con pocos valores únicos).
    """
    if df.empty or df.shape[1] == 0:
        return None

    cols = [str(c) for c in df.columns]

    # 0) preferencia explícita del plan
    if preferred_group_by:
        for pref in preferred_group_by:
            m0 = _best_match(str(pref), cols)
            if m0:
                return m0

    # 1) hint desde la pregunta
    hint = _extract_group_hint_from_question(question)
    if hint:
        m = _best_match(hint, cols)
        if m:
            return m

    # 2) nombres semánticos comunes (ampliado, no solo "carrera")
    semantic_candidates = [
        "carrera",
        "programa",
        "plan",
        "nombre carrera",
        "cliente",
        "nombre cliente",
        "proveedor",
        "vendedor",
        "responsable",
        "sucursal",
        "agencia",
        "region",
        "región",
        "comuna",
        "ciudad",
        "pais",
        "país",
        "departamento",
        "área",
        "area",
        "categoria",
        "categoría",
        "tipo",
        "estado",
        "canal",
        "mes",
        "anio",
        "año",
        "fecha",
    ]
    m2 = _pick_semantic_column(df, semantic_candidates)
    if m2:
        return m2

    # 3) heurística por cardinalidad: elegir columna categórica estable
    nrows = len(df)
    if nrows <= 0:
        return None

    best: tuple[float, str] | None = None
    for col in cols:
        if col.startswith("_"):
            continue
        if _is_probably_identifier_column(col):
            continue

        series = df[col]
        # preferir texto/categoría; para números, solo si son pocos valores
        nunique = int(series.nunique(dropna=True))
        if nunique < 2:
            continue
        # evitar columnas casi únicas (no agrupan)
        if nunique > min(50, max(10, int(nrows * 0.6))):
            continue

        # score: más filas por grupo (menos únicos) + nombre "humano" (no id)
        # en rango (2..50) => score alto con nunique bajo
        score = (1.0 / float(nunique))
        # pequeños boosts por nombres comunes
        name_n = _norm_text(col)
        if any(k in name_n for k in ["nombre", "tipo", "categoria", "categoría", "estado", "grupo"]):
            score += 0.05

        if best is None or score > best[0]:
            best = (score, col)

    return best[1] if best else None


def _grouped_summary_markdown(df: pd.DataFrame, question: str = "", preferred_group_by: list[str] | None = None) -> str | None:
    """Construye un resumen agrupado (best-effort) útil para respuestas rápidas.

    Si no hay una columna razonable para agrupar, retorna None.
    No llama a LLM.
    """
    if df.empty:
        return None

    group_col = _pick_reasonable_group_column(df, question, preferred_group_by=preferred_group_by)
    course_col = _pick_semantic_column(df, ["ramo", "asignatura", "curso", "modulo", "materia", "nombre ramo"])
    # Para horario, preferimos una columna directa; si no, intentaremos combinar.
    schedule_col = _pick_semantic_column(df, ["horario", "hora", "bloque", "dia", "inicio", "fin", "desde", "hasta"])

    if not group_col:
        return None

    # Construir una columna de detalle
    def _row_detail(row: pd.Series) -> str:
        parts: list[str] = []
        if course_col and pd.notna(row.get(course_col)):
            parts.append(str(row.get(course_col)))
        if schedule_col and pd.notna(row.get(schedule_col)):
            parts.append(str(row.get(schedule_col)))
        # Si no hay schedule_col pero existen dia/inicio/fin, concatenar.
        if (not schedule_col) and ("dia" in [str(c).lower() for c in df.columns]):
            # best effort
            day_c = _pick_semantic_column(df, ["dia"]) or ""
            start_c = _pick_semantic_column(df, ["inicio", "desde", "hora inicio"]) or ""
            end_c = _pick_semantic_column(df, ["fin", "hasta", "hora fin"]) or ""
            segs: list[str] = []
            if day_c and pd.notna(row.get(day_c)):
                segs.append(str(row.get(day_c)))
            if start_c and pd.notna(row.get(start_c)):
                segs.append(str(row.get(start_c)))
            if end_c and pd.notna(row.get(end_c)):
                segs.append(str(row.get(end_c)))
            if segs:
                parts.append(" ".join(segs))

        # Fallback: mostrar un par de columnas si no se encontró nada
        if not parts:
            for c in df.columns[:3]:
                v = row.get(c)
                if pd.notna(v):
                    parts.append(f"{c}={v}")
        return " — ".join(parts)[:240]

    max_careers = 30
    max_items_per_career = 30

    out: list[str] = []
    out.append(f"**Resumen por {group_col}**")

    grouped = df.groupby(group_col, dropna=False)
    careers = list(grouped.groups.keys())
    # Orden estable por texto
    careers_sorted = sorted(careers, key=lambda x: _norm_text(str(x)))

    truncated_careers = 0
    if len(careers_sorted) > max_careers:
        truncated_careers = len(careers_sorted) - max_careers
        careers_sorted = careers_sorted[:max_careers]

    for career in careers_sorted:
        sub = grouped.get_group(career)
        out.append(f"\n### {career}")

        # Items únicos (para no repetir filas idénticas)
        items: list[str] = []
        seen: set[str] = set()
        for _, row in sub.iterrows():
            d = _row_detail(row)
            dn = _norm_text(d)
            if not dn or dn in seen:
                continue
            seen.add(dn)
            items.append(d)
            if len(items) >= max_items_per_career:
                break

        for it in items:
            out.append(f"- {it}")

        if len(sub) > len(items):
            out.append(f"- … (mostrando {len(items)} de {len(sub)} filas)")

    if truncated_careers:
        out.append(f"\n_… y {truncated_careers} carrera(s) más (resumen truncado)._ ")

    return "\n".join(out)


def _execute_plan(index: WorkbookIndex, plan: QueryPlan, question: str) -> pd.DataFrame:
    # Elegir hojas
    if isinstance(plan.target_sheets, str):
        mode = plan.target_sheets.strip().lower()
        if mode in {"all"}:
            sheet_names = index.list_sheets()
        else:
            sheet_names = _pick_candidate_sheets(index, question)
    elif isinstance(plan.target_sheets, list) and plan.target_sheets:
        sheet_names = [s for s in plan.target_sheets if s in index.sheets]
        if not sheet_names:
            sheet_names = _pick_candidate_sheets(index, question)
    else:
        sheet_names = _pick_candidate_sheets(index, question)

    # Concatenar con columna de procedencia
    frames: list[pd.DataFrame] = []
    for s in sheet_names:
        df_sheet = index.sheets[s].copy()
        df_sheet["_sheet"] = s
        frames.append(df_sheet)

    if not frames:
        return pd.DataFrame()

    df_all = pd.concat(frames, ignore_index=True)

    # Resolver columnas referenciadas (plan puede venir con nombres aproximados)
    actual_columns = [str(c) for c in df_all.columns]

    def resolve_column(name: str) -> str | None:
        if name in df_all.columns:
            return name
        return _best_match(name, actual_columns)

    # Aplicar filtros
    mask = pd.Series([True] * len(df_all))
    for f in plan.filters:
        col = resolve_column(f.column)
        if not col:
            continue

        op = f.op
        if op not in {"eq", "contains", "in", "gt", "gte", "lt", "lte"}:
            continue

        series = df_all[col]

        if op in {"eq", "contains", "in"}:
            s_norm = series.astype(str).map(_norm_text)
            if op == "eq":
                v = _norm_text(str(f.value))
                mask &= s_norm == v
            elif op == "contains":
                v = _norm_text(str(f.value))
                if v:
                    mask &= s_norm.str.contains(re.escape(v), na=False)
            elif op == "in":
                if isinstance(f.value, list):
                    values = {_norm_text(str(x)) for x in f.value}
                else:
                    values = {_norm_text(str(f.value))}
                mask &= s_norm.isin(values)
        else:
            # Comparaciones numéricas/fechas best-effort
            s_num = pd.to_numeric(series, errors="coerce")
            try:
                vnum = float(f.value)
            except Exception:
                vnum = None
            if vnum is None:
                continue
            if op == "gt":
                mask &= s_num > vnum
            elif op == "gte":
                mask &= s_num >= vnum
            elif op == "lt":
                mask &= s_num < vnum
            elif op == "lte":
                mask &= s_num <= vnum

    df_out = df_all.loc[mask].copy()

    # Análisis/Agregaciones locales (para preguntas tipo: sumar columnas, valor más repetido, etc.)
    analysis = (plan.output or {}).get("analysis")
    if isinstance(analysis, dict):
        op = str(analysis.get("op") or "").strip().lower()
        if op in {"sum", "mean", "min", "max", "mode", "count", "duplicates", "nunique", "value_counts", "groupby_agg"}:
            # columnas preferidas (si vienen del plan) o inferidas desde la pregunta
            resolved_cols: list[str] = []
            cols_spec = analysis.get("columns")
            if isinstance(cols_spec, list) and cols_spec:
                for c in cols_spec:
                    rc = resolve_column(str(c))
                    if rc and rc not in resolved_cols and rc in df_out.columns:
                        resolved_cols.append(rc)
            if not resolved_cols:
                max_cols = 2 if op in {"sum", "mean", "min", "max"} else 1
                inferred = _infer_relevant_columns(df_out, question, max_cols=max_cols)
                resolved_cols = [c for c in inferred if c in df_out.columns]

            if op == "count":
                result = pd.DataFrame(
                    [
                        {
                            "metric": "rows",
                            "value": int(len(df_out)),
                        }
                    ]
                )
                return _make_arrow_safe(result)

            if op == "nunique":
                # Si no se especifica columna, mostrar conteo de únicos para varias columnas "razonables".
                cols = resolved_cols
                if not cols:
                    cols = [c for c in df_out.columns if not str(c).startswith("_")][:8]
                rows: list[dict[str, Any]] = []
                for c in cols:
                    try:
                        rows.append({"column": c, "metric": "nunique", "value": int(df_out[c].nunique(dropna=True))})
                    except Exception:
                        continue
                return _make_arrow_safe(pd.DataFrame(rows))

            if op == "value_counts":
                # Top valores más frecuentes (si no se indica columna, intentamos inferirla)
                col = resolved_cols[0] if resolved_cols else None
                if not col:
                    preferred = _pick_semantic_column(
                        df_out,
                        [
                            "codigo",
                            "código",
                            "code",
                            "id",
                            "referencia",
                            "ref",
                            "item",
                            "sku",
                            "estado",
                            "tipo",
                            "categoria",
                            "categoría",
                        ],
                    )
                    col = preferred
                if not col or col not in df_out.columns:
                    _log_unhandled_excel_request(question, index.schema_summary(), "value_counts:no_column")
                    return _make_arrow_safe(pd.DataFrame())

                series = df_out[col].dropna()
                vc = series.value_counts(dropna=True).head(50)
                result = pd.DataFrame({"column": [col] * int(len(vc)), "value": list(vc.index), "count": [int(x) for x in vc.values]})
                return _make_arrow_safe(result)

            if op == "groupby_agg":
                # Aggregación segura: group_by + métricas
                group_by_spec = analysis.get("group_by")
                group_cols: list[str] = []
                if isinstance(group_by_spec, list):
                    for g in group_by_spec:
                        rg = resolve_column(str(g))
                        if rg and rg in df_out.columns and rg not in group_cols:
                            group_cols.append(rg)
                elif isinstance(group_by_spec, str) and group_by_spec.strip().lower() == "auto":
                    # reusar heurística de columna de agrupación
                    gcol = _pick_reasonable_group_column(df_out, question)
                    if gcol:
                        group_cols = [gcol]

                if not group_cols:
                    _log_unhandled_excel_request(question, index.schema_summary(), "groupby_agg:no_group_by")
                    return _make_arrow_safe(pd.DataFrame())

                metrics_spec = analysis.get("metrics")
                # Construir métricas (si no vienen, inferir para sum/mean sobre numéricas)
                metrics: list[dict[str, str]] = []
                if isinstance(metrics_spec, list):
                    for m in metrics_spec:
                        if not isinstance(m, dict):
                            continue
                        coln = resolve_column(str(m.get("column") or ""))
                        agg = str(m.get("agg") or "").strip().lower()
                        if coln and coln in df_out.columns and agg in {"sum", "mean", "min", "max", "count", "nunique"}:
                            metrics.append({"column": coln, "agg": agg})

                if not metrics:
                    # Inferir: primeras numéricas para sum (si el usuario menciona suma/total)
                    qn = _norm_text(question)
                    default_agg = "sum" if any(k in qn for k in ["sum", "suma", "total", "sumar", "sumatoria"]) else "count"
                    numeric_cols = [c for c in df_out.columns if (not str(c).startswith("_")) and _is_numeric_enough(df_out[c])]
                    if numeric_cols and default_agg != "count":
                        for c in numeric_cols[:3]:
                            metrics.append({"column": str(c), "agg": default_agg})
                    else:
                        # fallback: contar filas por grupo
                        metrics.append({"column": group_cols[0], "agg": "count"})

                # Ejecutar
                agg_dict: dict[str, list[str]] = {}
                for m in metrics:
                    agg_dict.setdefault(m["column"], [])
                    if m["agg"] not in agg_dict[m["column"]]:
                        agg_dict[m["column"]].append(m["agg"])

                grouped = df_out.groupby(group_cols, dropna=False).agg(agg_dict)
                grouped.columns = [
                    f"{col}_{agg}" if isinstance(agg, str) else str(col)
                    for col, agg in grouped.columns.to_flat_index()
                ]
                grouped = grouped.reset_index()
                # ordenar por la primera métrica desc si existe
                metric_cols = [c for c in grouped.columns if c not in group_cols]
                if metric_cols:
                    grouped = grouped.sort_values(by=metric_cols[0], ascending=False, kind="mergesort")
                return _make_arrow_safe(grouped.head(200))

            if op == "duplicates":
                # Detectar duplicados por columna (ej: códigos/IDs repetidos).
                # Si no hay columna inferida, priorizar nombres típicos.
                if not resolved_cols:
                    preferred = _pick_semantic_column(
                        df_out,
                        [
                            "codigo",
                            "código",
                            "code",
                            "id",
                            "identificador",
                            "referencia",
                            "ref",
                            "item",
                            "sku",
                        ],
                    )
                    if preferred:
                        resolved_cols = [preferred]

                if not resolved_cols:
                    # último recurso: buscar la columna con mayor cantidad de repeticiones
                    best_col: str | None = None
                    best_dups = 0
                    for c in [c for c in df_out.columns if not str(c).startswith("_")]:
                        s = df_out[c].dropna()
                        if s.empty:
                            continue
                        dups = int(s.duplicated(keep=False).sum())
                        if dups > best_dups:
                            best_dups = dups
                            best_col = c
                    if best_col:
                        resolved_cols = [best_col]

                if not resolved_cols:
                    return _make_arrow_safe(pd.DataFrame())

                col = resolved_cols[0]
                series = df_out[col].dropna()
                if series.empty:
                    return _make_arrow_safe(pd.DataFrame())

                vc = series.value_counts(dropna=True)
                dups_vc = vc[vc > 1]
                top = dups_vc.head(50)
                result = pd.DataFrame(
                    {
                        "column": [col] * int(len(top)),
                        "value": list(top.index),
                        "count": [int(x) for x in top.values],
                    }
                )
                return _make_arrow_safe(result)

            if op in {"sum", "mean", "min", "max"}:
                # Si no se pudo inferir columnas, elegir primeras numéricas.
                numeric_cols = [c for c in df_out.columns if (not str(c).startswith("_")) and _is_numeric_enough(df_out[c])]
                if not resolved_cols:
                    resolved_cols = numeric_cols[:2]
                else:
                    # filtrar a numéricas si aplica
                    resolved_cols = [c for c in resolved_cols if c in numeric_cols] or numeric_cols[:2]

                rows: list[dict[str, Any]] = []
                for c in resolved_cols[:2]:
                    s = pd.to_numeric(df_out[c], errors="coerce")
                    if op == "sum":
                        v: Any = float(s.sum(skipna=True))
                        metric = "sum"
                    elif op == "mean":
                        v = float(s.mean(skipna=True)) if int(s.notna().sum()) else None
                        metric = "mean"
                    elif op == "min":
                        v = float(s.min(skipna=True)) if int(s.notna().sum()) else None
                        metric = "min"
                    else:
                        v = float(s.max(skipna=True)) if int(s.notna().sum()) else None
                        metric = "max"
                    rows.append({"column": c, "metric": metric, "value": v})

                # Para el caso de "sumar dos campos", entregar también la suma combinada.
                if op == "sum" and len(resolved_cols) >= 2:
                    c1, c2 = resolved_cols[0], resolved_cols[1]
                    s1 = pd.to_numeric(df_out[c1], errors="coerce")
                    s2 = pd.to_numeric(df_out[c2], errors="coerce")
                    rows.append({"column": f"{c1} + {c2}", "metric": "sum", "value": float((s1 + s2).sum(skipna=True))})

                return _make_arrow_safe(pd.DataFrame(rows))

            # mode: valor más repetido
            if op == "mode":
                def _mode_for_column(col: str) -> dict[str, Any] | None:
                    series = df_out[col].dropna()
                    if series.empty:
                        return None
                    vc = series.value_counts(dropna=True)
                    if vc.empty:
                        return None
                    top_value = vc.index[0]
                    top_count = int(vc.iloc[0])
                    total = int(series.shape[0])
                    share = (float(top_count) / float(total)) if total else 0.0
                    return {
                        "column": col,
                        "most_frequent_value": top_value,
                        "count": top_count,
                        "share": round(share, 4),
                    }

                # Si no hay columna, buscamos el máximo "top_count" en todas.
                if resolved_cols:
                    rec = _mode_for_column(resolved_cols[0])
                    return _make_arrow_safe(pd.DataFrame([rec]) if rec else pd.DataFrame())

                best_rec: dict[str, Any] | None = None
                for col in [c for c in df_out.columns if not str(c).startswith("_")]:
                    rec = _mode_for_column(col)
                    if not rec:
                        continue
                    if best_rec is None or int(rec["count"]) > int(best_rec["count"]):
                        best_rec = rec
                return _make_arrow_safe(pd.DataFrame([best_rec]) if best_rec else pd.DataFrame())

    # Seleccionar columnas
    if isinstance(plan.select, list) and plan.select:
        resolved: list[str] = []
        for name in plan.select:
            col = resolve_column(name)
            if col and col not in resolved:
                resolved.append(col)
        # siempre incluir _sheet si existe
        if "_sheet" in df_out.columns and "_sheet" not in resolved:
            resolved.insert(0, "_sheet")
        if resolved:
            df_out = df_out[resolved]

    # Ordenar
    for s in plan.order_by:
        col = resolve_column(s.column)
        if col and col in df_out.columns:
            df_out = df_out.sort_values(by=col, ascending=bool(s.asc), kind="mergesort")

    # Limitar
    if plan.limit and len(df_out) > plan.limit:
        df_out = df_out.head(plan.limit)

    return _make_arrow_safe(df_out.reset_index(drop=True))


def _pick_candidate_sheets(index: WorkbookIndex, question: str) -> list[str]:
    q = _norm_text(question)
    if not q:
        return index.list_sheets()[:1]

    tokens = {t for t in re.split(r"[^a-z0-9_]+", q) if len(t) >= 4}
    scored: list[tuple[int, str]] = []
    for sheet_name, prof in index.profiles.items():
        cols = [_norm_text(c.name) for c in prof.columns]
        score = 0
        for t in tokens:
            if t in _norm_text(sheet_name):
                score += 2
            if any(t in c for c in cols):
                score += 1
        scored.append((score, sheet_name))

    scored.sort(reverse=True)
    best_score = scored[0][0] if scored else 0
    if best_score <= 0:
        return index.list_sheets()[: min(3, len(index.list_sheets()))]

    # tomar las mejores 3
    return [s for _, s in scored[:3]]


def _read_excel_all_sheets(buf: BytesIO) -> dict[str, pd.DataFrame]:
    # Preferir pandas para tipos y rendimiento
    xls = pd.ExcelFile(buf)
    sheets: dict[str, pd.DataFrame] = {}
    for name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=name)
        df = _clean_headers(df)
        sheets[name] = df
    return sheets


def _read_csv_best_effort(buf: BytesIO) -> pd.DataFrame:
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    separators = [",", ";", "\t"]

    last_err: Exception | None = None
    for enc in encodings:
        for sep in separators:
            try:
                buf.seek(0)
                df = pd.read_csv(buf, encoding=enc, sep=sep, on_bad_lines="skip", engine="python")
                df = _clean_headers(df)
                if not df.empty:
                    return df
            except Exception as e:
                last_err = e
                continue

    if last_err:
        raise last_err
    return pd.DataFrame()


def _clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    cols: list[str] = []
    seen: dict[str, int] = {}
    for idx, c in enumerate(df.columns):
        name = str(c).strip() if c is not None else ""
        if not name:
            name = f"Columna_{idx + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        cols.append(name)
    df = df.copy()
    df.columns = cols
    return df


def _profile_sheet(sheet_name: str, df: pd.DataFrame) -> SheetProfile:
    cols: list[ColumnProfile] = []
    for c in df.columns[:60]:
        series = df[c]
        dtype = str(series.dtype)
        examples: list[str] = []
        try:
            # Top valores únicos no nulos, acotados
            unique_vals = series.dropna().astype(str).head(800).unique().tolist()
            examples = [str(v)[:40] for v in unique_vals[:4]]
        except Exception:
            examples = []
        cols.append(ColumnProfile(name=str(c), dtype=dtype, example_values=examples))

    return SheetProfile(
        name=sheet_name,
        nrows=int(len(df)),
        ncols=int(len(df.columns)),
        columns=cols,
    )
