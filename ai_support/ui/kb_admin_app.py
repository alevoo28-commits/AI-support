import json
import os
import re
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from ai_support.core.knowledge_base import get_kb_manager


load_dotenv(override=True)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _departments_path() -> Path:
    return Path(__file__).resolve().parents[2] / "knowledge_base" / "departments.json"


def _load_departments() -> dict:
    path = _departments_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_departments(data: dict) -> None:
    path = _departments_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _dept_children_map(data: dict) -> dict[str, list[str]]:
    children: dict[str, list[str]] = {}
    for dept_id, meta in data.items():
        parent_id = str(meta.get("parent_id") or "").strip()
        if not parent_id:
            continue
        children.setdefault(parent_id, []).append(dept_id)
    for parent in children:
        children[parent].sort()
    return children


def _dept_depth(data: dict, dept_id: str) -> int:
    depth = 0
    current = dept_id
    seen: set[str] = set()
    while True:
        if current in seen:
            break
        seen.add(current)
        parent = str((data.get(current) or {}).get("parent_id") or "").strip()
        if not parent or parent not in data:
            break
        depth += 1
        current = parent
    return depth


def _dept_path(data: dict, dept_id: str) -> str:
    parts: list[str] = []
    current = dept_id
    seen: set[str] = set()
    while True:
        if current in seen:
            break
        seen.add(current)
        meta = data.get(current) or {}
        name = str(meta.get("name") or current).strip() or current
        parts.append(name)
        parent = str(meta.get("parent_id") or "").strip()
        if not parent or parent not in data:
            break
        current = parent
    parts.reverse()
    return " > ".join(parts)


def _list_departments_view() -> list[dict]:
    data = _load_departments()
    rows: list[dict] = []
    for dept_id, meta in data.items():
        rows.append(
            {
                "id": dept_id,
                "name": str(meta.get("name") or "").strip(),
                "parent_id": str(meta.get("parent_id") or "").strip() or None,
                "mapped_area_id": str(meta.get("mapped_area_id") or "").strip() or None,
                "depth": _dept_depth(data, dept_id),
                "full_path": _dept_path(data, dept_id),
                "created_at": float(meta.get("created_at") or 0.0),
            }
        )
    return sorted(rows, key=lambda r: (r.get("full_path") or "", r.get("name") or ""))


def _create_department(name: str, parent_id: str | None, mapped_area_id: str | None) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("El nombre del departamento no puede estar vacio.")

    data = _load_departments()

    if parent_id and parent_id not in data:
        raise ValueError("El departamento padre seleccionado no existe.")

    for existing in data.values():
        existing_name = str(existing.get("name") or "").strip().lower()
        existing_parent = str(existing.get("parent_id") or "").strip() or None
        if existing_name == name.lower() and existing_parent == (parent_id or None):
            raise ValueError("Ya existe un departamento con ese nombre bajo el mismo padre.")

    base = _normalize(name)[:48] or "departamento"
    dept_id = f"{base}_{str(int(time.time()))[-5:]}"

    data[dept_id] = {
        "id": dept_id,
        "name": name,
        "parent_id": parent_id,
        "mapped_area_id": mapped_area_id,
        "created_at": time.time(),
    }
    _save_departments(data)
    return data[dept_id]


def _delete_department(dept_id: str) -> bool:
    data = _load_departments()
    if dept_id not in data:
        return False

    children = _dept_children_map(data)
    if children.get(dept_id):
        raise ValueError("No puedes eliminar un departamento que tiene subdepartamentos.")

    data.pop(dept_id, None)
    _save_departments(data)
    return True


def _set_department_parent(dept_id: str, parent_id: str | None) -> dict:
    data = _load_departments()
    if dept_id not in data:
        raise ValueError("El departamento seleccionado no existe.")

    parent_clean = (parent_id or "").strip() or None
    if parent_clean == dept_id:
        raise ValueError("Un departamento no puede ser padre de sí mismo.")
    if parent_clean and parent_clean not in data:
        raise ValueError("El departamento padre seleccionado no existe.")

    # Evitar ciclos: el nuevo padre no puede estar dentro de sus descendientes.
    children = _dept_children_map(data)
    descendants: set[str] = set()
    queue = [dept_id]
    while queue:
        current = queue.pop(0)
        for child in children.get(current, []):
            if child in descendants:
                continue
            descendants.add(child)
            queue.append(child)
    if parent_clean and parent_clean in descendants:
        raise ValueError("Movimiento inválido: el padre seleccionado es descendiente del departamento.")

    data[dept_id]["parent_id"] = parent_clean
    _save_departments(data)
    return data[dept_id]


def _render_auth_gate() -> bool:
    admin_password = (os.getenv("AI_SUPPORT_ADMIN_PASSWORD") or "").strip()
    if not admin_password:
        st.info("AI_SUPPORT_ADMIN_PASSWORD no esta definido. Acceso local habilitado para mantencion.")
        return True

    if st.session_state.get("kb_admin_ok"):
        return True

    st.warning("Zona de administracion. Ingresa la clave de administrador.")
    with st.form("kb_admin_login"):
        pwd = st.text_input("Clave administrador", type="password")
        ok = st.form_submit_button("Ingresar", use_container_width=True)
        if ok:
            if pwd == admin_password:
                st.session_state["kb_admin_ok"] = True
                st.rerun()
            else:
                st.error("Clave incorrecta.")
    return False


def main() -> None:
    st.set_page_config(page_title="Mantenedor KB Admin", page_icon="🛠️", layout="wide")
    st.title("🛠️ Mantenedor de Areas y Departamentos")
    st.caption("Administra jerarquias de areas (KB) y departamentos con subareas.")

    if not _render_auth_gate():
        st.stop()

    kb = get_kb_manager()
    areas = kb.list_areas()

    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        st.subheader("📚 Areas de Base de Conocimiento")

        with st.expander("➕ Crear area", expanded=False):
            with st.form("create_area_form"):
                area_name = st.text_input("Nombre area", placeholder="Ej: Infraestructura")
                area_desc = st.text_area("Descripcion", height=80)
                parent_options = ["(sin padre)"]
                parent_map: dict[str, str | None] = {"(sin padre)": None}
                for a in areas:
                    label = str(a.get("full_path") or a.get("name") or a.get("id") or "").strip()
                    if not label:
                        continue
                    parent_options.append(label)
                    parent_map[label] = str(a.get("id") or "").strip() or None
                parent_label = st.selectbox("Area padre", options=parent_options)
                submitted = st.form_submit_button("Crear area", use_container_width=True)
                if submitted:
                    try:
                        created = kb.create_area(
                            area_name.strip(),
                            area_desc.strip(),
                            parent_id=parent_map.get(parent_label),
                        )
                        st.success(f"Area creada: {created.get('name')}")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        if areas:
            st.write("Arbol de areas:")
            for a in areas:
                indent = "  " * int(a.get("depth") or 0)
                st.write(f"{indent}- {a.get('name')} ({a.get('doc_count', 0)} docs)")

            with st.expander("🔀 Mover area", expanded=False):
                area_labels = [str(a.get("full_path") or a.get("name") or a.get("id")) for a in areas]
                area_label_to_id = {
                    str(a.get("full_path") or a.get("name") or a.get("id")): str(a.get("id")) for a in areas
                }
                selected_move_area_label = st.selectbox("Area a mover", options=area_labels, key="move_area_sel")
                move_parent_options = ["(sin padre)"] + area_labels
                selected_move_parent_label = st.selectbox("Nuevo padre", options=move_parent_options, key="move_area_parent_sel")
                if st.button("Aplicar movimiento de area", use_container_width=True):
                    try:
                        area_id = area_label_to_id.get(selected_move_area_label)
                        parent_id = None if selected_move_parent_label == "(sin padre)" else area_label_to_id.get(selected_move_parent_label)
                        if area_id:
                            kb.update_area_parent(area_id, parent_id)
                            st.success("Area movida correctamente.")
                            st.rerun()
                    except Exception as e:
                        st.error(str(e))

            delete_area_options = {str(a.get("full_path") or a.get("name") or a.get("id")): str(a.get("id")) for a in areas}
            selected_area_label = st.selectbox("Eliminar area", options=list(delete_area_options.keys()), key="del_area_sel")
            if st.button("🗑️ Eliminar area seleccionada", type="secondary", use_container_width=True):
                area_id = delete_area_options.get(selected_area_label)
                if area_id:
                    ok = kb.delete_area(area_id)
                    if ok:
                        st.success("Area eliminada.")
                        st.rerun()
                    else:
                        st.error("No se pudo eliminar el area.")
        else:
            st.info("No hay areas creadas.")

    with col_right:
        st.subheader("🏢 Departamentos y Subdepartamentos")
        departments = _list_departments_view()

        with st.expander("➕ Crear departamento", expanded=False):
            with st.form("create_dept_form"):
                dept_name = st.text_input("Nombre departamento", placeholder="Ej: CEC")

                dept_parent_options = ["(sin padre)"]
                dept_parent_map: dict[str, str | None] = {"(sin padre)": None}
                for d in departments:
                    label = str(d.get("full_path") or d.get("name") or d.get("id") or "").strip()
                    if not label:
                        continue
                    dept_parent_options.append(label)
                    dept_parent_map[label] = str(d.get("id") or "").strip() or None
                dept_parent_label = st.selectbox("Departamento padre", options=dept_parent_options)

                area_options = ["(sin area asociada)"]
                area_map: dict[str, str | None] = {"(sin area asociada)": None}
                for a in areas:
                    label = str(a.get("full_path") or a.get("name") or a.get("id") or "").strip()
                    if not label:
                        continue
                    area_options.append(label)
                    area_map[label] = str(a.get("id") or "").strip() or None
                mapped_area_label = st.selectbox("Area KB asociada (opcional)", options=area_options)

                submitted_dept = st.form_submit_button("Crear departamento", use_container_width=True)
                if submitted_dept:
                    try:
                        created = _create_department(
                            dept_name.strip(),
                            dept_parent_map.get(dept_parent_label),
                            area_map.get(mapped_area_label),
                        )
                        st.success(f"Departamento creado: {created.get('name')}")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        if departments:
            st.write("Arbol de departamentos:")
            for d in departments:
                indent = "  " * int(d.get("depth") or 0)
                mapped = f" -> area:{d.get('mapped_area_id')}" if d.get("mapped_area_id") else ""
                st.write(f"{indent}- {d.get('name')}{mapped}")

            with st.expander("🔀 Mover departamento", expanded=False):
                dept_labels = [str(d.get("full_path") or d.get("name") or d.get("id")) for d in departments]
                dept_label_to_id = {
                    str(d.get("full_path") or d.get("name") or d.get("id")): str(d.get("id")) for d in departments
                }
                selected_move_dept_label = st.selectbox("Departamento a mover", options=dept_labels, key="move_dept_sel")
                move_dept_parent_options = ["(sin padre)"] + dept_labels
                selected_move_dept_parent_label = st.selectbox(
                    "Nuevo padre de departamento",
                    options=move_dept_parent_options,
                    key="move_dept_parent_sel",
                )
                if st.button("Aplicar movimiento de departamento", use_container_width=True):
                    try:
                        dept_id = dept_label_to_id.get(selected_move_dept_label)
                        parent_id = None if selected_move_dept_parent_label == "(sin padre)" else dept_label_to_id.get(selected_move_dept_parent_label)
                        if dept_id:
                            _set_department_parent(dept_id, parent_id)
                            st.success("Departamento movido correctamente.")
                            st.rerun()
                    except Exception as e:
                        st.error(str(e))

            delete_dept_options = {str(d.get("full_path") or d.get("name") or d.get("id")): str(d.get("id")) for d in departments}
            selected_dept_label = st.selectbox("Eliminar departamento", options=list(delete_dept_options.keys()), key="del_dept_sel")
            if st.button("🗑️ Eliminar departamento seleccionado", type="secondary", use_container_width=True):
                dept_id = delete_dept_options.get(selected_dept_label)
                if dept_id:
                    try:
                        _delete_department(dept_id)
                        st.success("Departamento eliminado.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        else:
            st.info("No hay departamentos creados.")


if __name__ == "__main__":
    main()
