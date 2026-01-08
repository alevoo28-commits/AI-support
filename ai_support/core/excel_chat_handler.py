"""
Handler de comandos naturales sobre DataFrames (ChatGPT para Excel).

Soporta:
- Suma, promedio, máximo, mínimo de rangos o celdas
- Obtener valor de celda
- Buscar valor (VLOOKUP-like)
- Filtrar filas por condición
- Ordenar por columna
- Contar valores, contar únicos
- Operaciones aritméticas entre celdas
"""

import re
from typing import Any

import pandas as pd


def col_letters_to_index(letters: str) -> int:
    """Convierte letras de columna Excel (A, B, AA, etc.) a índice 0-based."""
    letters = letters.upper()
    acc = 0
    for ch in letters:
        if not ("A" <= ch <= "Z"):
            raise ValueError(f"Columna inválida: {letters}")
        acc = acc * 26 + (ord(ch) - ord("A") + 1)
    return acc - 1


def parse_cell_ref(ref: str) -> tuple[int, int]:
    """Parsea A2 → (col_idx, row_idx) 0-based.
    
    Asume fila 1 = cabecera, entonces A2 → iloc[0, 0]
    """
    m = re.match(r"^([A-Za-z]{1,3})(\d{1,6})$", ref.strip())
    if not m:
        raise ValueError(f"Referencia inválida: {ref}")
    col_letters = m.group(1)
    row_num = int(m.group(2))
    col_idx = col_letters_to_index(col_letters)
    row_idx = row_num - 2  # fila 2 → iloc[0]
    if row_idx < 0:
        raise ValueError(f"Fila {row_num} no mapeable (cabecera en fila 1)")
    return col_idx, row_idx


def parse_range(range_str: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """Parsea A2:B10 → ((col1, row1), (col2, row2)) 0-based."""
    parts = range_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"Rango inválido: {range_str}")
    start_cell = parse_cell_ref(parts[0].strip())
    end_cell = parse_cell_ref(parts[1].strip())
    return start_cell, end_cell


def get_cell_value(df: pd.DataFrame, ref: str) -> Any:
    """Obtiene el valor de una celda (ej: A2)."""
    col_idx, row_idx = parse_cell_ref(ref)
    return df.iloc[row_idx, col_idx]


def get_range_values(df: pd.DataFrame, range_str: str) -> list[Any]:
    """Obtiene valores de un rango (ej: A2:A10) en forma de lista."""
    (col1, row1), (col2, row2) = parse_range(range_str)
    values = []
    for r in range(min(row1, row2), max(row1, row2) + 1):
        for c in range(min(col1, col2), max(col1, col2) + 1):
            values.append(df.iloc[r, c])
    return values


def sum_range(df: pd.DataFrame, range_str: str) -> float:
    """Suma valores de un rango."""
    vals = get_range_values(df, range_str)
    nums = [float(v) for v in vals if pd.notna(v)]
    return sum(nums)


def avg_range(df: pd.DataFrame, range_str: str) -> float:
    """Promedio de un rango."""
    vals = get_range_values(df, range_str)
    nums = [float(v) for v in vals if pd.notna(v)]
    return sum(nums) / len(nums) if nums else 0.0


def max_range(df: pd.DataFrame, range_str: str) -> float:
    """Máximo de un rango."""
    vals = get_range_values(df, range_str)
    nums = [float(v) for v in vals if pd.notna(v)]
    return max(nums) if nums else 0.0


def min_range(df: pd.DataFrame, range_str: str) -> float:
    """Mínimo de un rango."""
    vals = get_range_values(df, range_str)
    nums = [float(v) for v in vals if pd.notna(v)]
    return min(nums) if nums else 0.0


def count_range(df: pd.DataFrame, range_str: str) -> int:
    """Cuenta valores no vacíos en un rango."""
    vals = get_range_values(df, range_str)
    return sum(1 for v in vals if pd.notna(v))


def count_unique(df: pd.DataFrame, range_str: str) -> int:
    """Cuenta valores únicos en un rango."""
    vals = get_range_values(df, range_str)
    unique = {v for v in vals if pd.notna(v)}
    return len(unique)


def vlookup(df: pd.DataFrame, lookup_value: Any, col_name_search: str, col_name_return: str) -> Any:
    """Busca lookup_value en col_name_search y retorna el valor de col_name_return."""
    mask = df[col_name_search] == lookup_value
    matches = df.loc[mask, col_name_return]
    if matches.empty:
        return None
    return matches.iloc[0]


def filter_rows(df: pd.DataFrame, col_name: str, condition: str, value: Any) -> pd.DataFrame:
    """Filtra filas según condición.
    
    condition: '=', '>', '<', '>=', '<=', '!='
    """
    if condition == "=":
        return df.loc[df[col_name] == value]
    elif condition == ">":
        return df.loc[df[col_name] > value]
    elif condition == "<":
        return df.loc[df[col_name] < value]
    elif condition == ">=":
        return df.loc[df[col_name] >= value]
    elif condition == "<=":
        return df.loc[df[col_name] <= value]
    elif condition == "!=":
        return df.loc[df[col_name] != value]
    else:
        raise ValueError(f"Condición inválida: {condition}")


def sort_by_column(df: pd.DataFrame, col_name: str, ascending: bool = True) -> pd.DataFrame:
    """Ordena DataFrame por columna."""
    return df.sort_values(by=col_name, ascending=ascending)


def handle_excel_command(df: pd.DataFrame, user_input: str) -> dict[str, Any]:
    """Interpreta comando natural y ejecuta operación sobre DataFrame.
    
    Retorna dict con:
    - success: bool
    - result: valor o DataFrame resultante
    - message: str explicativo
    - error: str (si falla)
    """
    user_input = user_input.strip()
    lower = user_input.lower()

    try:
        # 0. Buscar duplicados
        if any(w in lower for w in ["duplicado", "duplicados", "repetido", "repetidos"]):
            # Buscar filas completamente duplicadas
            duplicates = df[df.duplicated(keep=False)]
            
            if not duplicates.empty:
                # Agrupar por valores duplicados para mostrar mejor
                duplicate_groups = []
                for _, row in duplicates.iterrows():
                    duplicate_groups.append(row.to_dict())
                
                msg = f"Se encontraron {len(duplicates)} filas duplicadas (de {len(df)} total).\n\n"
                msg += "**Filas duplicadas:**\n"
                
                return {
                    "success": True,
                    "result": duplicates,
                    "message": msg,
                    "error": None,
                }
            else:
                return {
                    "success": True,
                    "result": "No hay duplicados",
                    "message": "✓ No se encontraron filas duplicadas en el archivo.",
                    "error": None,
                }
        
        # 1. Suma de rango o celdas
        if any(w in lower for w in ["suma", "sumar", "+"]):
            # Buscar rangos tipo A2:A10
            range_match = re.search(r"\b([A-Za-z]{1,3}\d{1,6}):([A-Za-z]{1,3}\d{1,6})\b", user_input)
            if range_match:
                range_str = range_match.group(0)
                total = sum_range(df, range_str)
                return {
                    "success": True,
                    "result": total,
                    "message": f"Suma de {range_str}: {total}",
                    "error": None,
                }
            # Buscar celdas individuales
            cells = re.findall(r"\b([A-Za-z]{1,3}\d{1,6})\b", user_input)
            if cells:
                values = []
                for cell in cells:
                    val = get_cell_value(df, cell)
                    try:
                        values.append(float(val))
                    except Exception:
                        pass
                if values:
                    total = sum(values)
                    return {
                        "success": True,
                        "result": total,
                        "message": f"Suma de {', '.join(cells)}: {total} (valores: {values})",
                        "error": None,
                    }

        # 2. Promedio
        if any(w in lower for w in ["promedio", "promediar", "media", "average", "avg"]):
            range_match = re.search(r"\b([A-Za-z]{1,3}\d{1,6}):([A-Za-z]{1,3}\d{1,6})\b", user_input)
            if range_match:
                range_str = range_match.group(0)
                avg = avg_range(df, range_str)
                return {
                    "success": True,
                    "result": avg,
                    "message": f"Promedio de {range_str}: {avg}",
                    "error": None,
                }

        # 3. Máximo
        if any(w in lower for w in ["maximo", "máximo", "max"]):
            range_match = re.search(r"\b([A-Za-z]{1,3}\d{1,6}):([A-Za-z]{1,3}\d{1,6})\b", user_input)
            if range_match:
                range_str = range_match.group(0)
                mx = max_range(df, range_str)
                return {
                    "success": True,
                    "result": mx,
                    "message": f"Máximo de {range_str}: {mx}",
                    "error": None,
                }

        # 4. Mínimo
        if any(w in lower for w in ["minimo", "mínimo", "min"]):
            range_match = re.search(r"\b([A-Za-z]{1,3}\d{1,6}):([A-Za-z]{1,3}\d{1,6})\b", user_input)
            if range_match:
                range_str = range_match.group(0)
                mn = min_range(df, range_str)
                return {
                    "success": True,
                    "result": mn,
                    "message": f"Mínimo de {range_str}: {mn}",
                    "error": None,
                }

        # 5. Contar
        if any(w in lower for w in ["contar", "count"]):
            if "unico" in lower or "único" in lower or "unique" in lower:
                range_match = re.search(r"\b([A-Za-z]{1,3}\d{1,6}):([A-Za-z]{1,3}\d{1,6})\b", user_input)
                if range_match:
                    range_str = range_match.group(0)
                    cnt = count_unique(df, range_str)
                    return {
                        "success": True,
                        "result": cnt,
                        "message": f"Valores únicos en {range_str}: {cnt}",
                        "error": None,
                    }
            else:
                range_match = re.search(r"\b([A-Za-z]{1,3}\d{1,6}):([A-Za-z]{1,3}\d{1,6})\b", user_input)
                if range_match:
                    range_str = range_match.group(0)
                    cnt = count_range(df, range_str)
                    return {
                        "success": True,
                        "result": cnt,
                        "message": f"Contar valores en {range_str}: {cnt}",
                        "error": None,
                    }

        # 6. Obtener valor de celda
        if any(w in lower for w in ["valor de", "celda", "obtener"]):
            cells = re.findall(r"\b([A-Za-z]{1,3}\d{1,6})\b", user_input)
            if cells:
                cell = cells[0]
                val = get_cell_value(df, cell)
                return {
                    "success": True,
                    "result": val,
                    "message": f"Valor de {cell}: {val}",
                    "error": None,
                }

        # 7. Buscar (VLOOKUP-like)
        if any(w in lower for w in ["buscar", "vlookup", "busca"]):
            # Formato esperado: "buscar X en columna Y retornar columna Z"
            # Simplificado: usuario deberá especificar nombres de columnas
            cols = list(df.columns)
            # Intentar extraer nombres de columnas mencionadas
            mentioned = [c for c in cols if c.lower() in lower]
            if len(mentioned) >= 2:
                col_search = mentioned[0]
                col_return = mentioned[1]
                # Buscar el valor (asumimos que está entre comillas o es un número)
                quote_match = re.search(r"['\"]([^'\"]+)['\"]", user_input)
                num_match = re.search(r"\b(\d+\.?\d*)\b", user_input)
                lookup_val = None
                if quote_match:
                    lookup_val = quote_match.group(1)
                elif num_match:
                    lookup_val = float(num_match.group(1))
                
                if lookup_val is not None:
                    result = vlookup(df, lookup_val, col_search, col_return)
                    return {
                        "success": True,
                        "result": result,
                        "message": f"Buscar '{lookup_val}' en '{col_search}' → '{col_return}': {result}",
                        "error": None,
                    }

        # 8. Filtrar
        if any(w in lower for w in ["filtrar", "filter", "donde"]):
            cols = list(df.columns)
            mentioned = [c for c in cols if c.lower() in lower]
            if mentioned:
                col = mentioned[0]
                # Detectar condición
                cond = None
                if ">=" in user_input:
                    cond = ">="
                elif "<=" in user_input:
                    cond = "<="
                elif "!=" in user_input or "≠" in user_input:
                    cond = "!="
                elif ">" in user_input:
                    cond = ">"
                elif "<" in user_input:
                    cond = "<"
                elif "=" in user_input or "igual" in lower:
                    cond = "="
                
                if cond:
                    # Extraer valor
                    quote_match = re.search(r"['\"]([^'\"]+)['\"]", user_input)
                    num_match = re.search(r"\b(\d+\.?\d*)\b", user_input)
                    val = None
                    if quote_match:
                        val = quote_match.group(1)
                    elif num_match:
                        val = float(num_match.group(1))
                    
                    if val is not None:
                        result_df = filter_rows(df, col, cond, val)
                        return {
                            "success": True,
                            "result": result_df,
                            "message": f"Filtrar '{col}' {cond} {val}: {len(result_df)} filas",
                            "error": None,
                        }

        # 9. Ordenar
        if any(w in lower for w in ["ordenar", "sort"]):
            cols = list(df.columns)
            mentioned = [c for c in cols if c.lower() in lower]
            if mentioned:
                col = mentioned[0]
                asc = "desc" not in lower and "descendente" not in lower
                result_df = sort_by_column(df, col, ascending=asc)
                direction = "ascendente" if asc else "descendente"
                return {
                    "success": True,
                    "result": result_df,
                    "message": f"Ordenar por '{col}' ({direction})",
                    "error": None,
                }

        # 10. Multiplicar, dividir, restar (celdas)
        if "*" in user_input or "multiplicar" in lower:
            cells = re.findall(r"\b([A-Za-z]{1,3}\d{1,6})\b", user_input)
            if len(cells) >= 2:
                values = []
                for cell in cells:
                    val = get_cell_value(df, cell)
                    try:
                        values.append(float(val))
                    except Exception:
                        pass
                if len(values) >= 2:
                    result = values[0]
                    for v in values[1:]:
                        result *= v
                    return {
                        "success": True,
                        "result": result,
                        "message": f"Multiplicar {', '.join(cells)}: {result}",
                        "error": None,
                    }

        if "/" in user_input or "dividir" in lower:
            cells = re.findall(r"\b([A-Za-z]{1,3}\d{1,6})\b", user_input)
            if len(cells) >= 2:
                values = []
                for cell in cells:
                    val = get_cell_value(df, cell)
                    try:
                        values.append(float(val))
                    except Exception:
                        pass
                if len(values) >= 2:
                    result = values[0]
                    for v in values[1:]:
                        result /= v if v != 0 else 1
                    return {
                        "success": True,
                        "result": result,
                        "message": f"Dividir {', '.join(cells)}: {result}",
                        "error": None,
                    }

        if "-" in user_input or "restar" in lower:
            cells = re.findall(r"\b([A-Za-z]{1,3}\d{1,6})\b", user_input)
            if len(cells) >= 2:
                values = []
                for cell in cells:
                    val = get_cell_value(df, cell)
                    try:
                        values.append(float(val))
                    except Exception:
                        pass
                if len(values) >= 2:
                    result = values[0]
                    for v in values[1:]:
                        result -= v
                    return {
                        "success": True,
                        "result": result,
                        "message": f"Restar {', '.join(cells)}: {result}",
                        "error": None,
                    }

        return {
            "success": False,
            "result": None,
            "message": "No se pudo interpretar el comando. Operaciones soportadas: suma, promedio, max, min, contar, buscar, filtrar, ordenar, multiplicar, dividir, restar.",
            "error": "Comando no reconocido",
        }

    except Exception as e:
        return {
            "success": False,
            "result": None,
            "message": f"Error al procesar comando: {e}",
            "error": str(e),
        }
