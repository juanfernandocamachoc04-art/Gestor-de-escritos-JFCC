"""
LexDocs — Gestión de Escritos Legales
Banco Guayaquil - Consulegis
Desarrollado por: Juan Fernando Camacho
"""

import streamlit as st
import sqlite3
import hashlib
import base64
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

DB_PATH = "lexdocs.db"
DIAS_EXPIRACION = 7  # días tras presentación para borrar el escrito

USERS = {
    "rafaela_b": {
        "password": hashlib.sha256("123".encode()).hexdigest(),
        "nombre":   "Rafaela B.",
        "rol":      "Solicitante",
    },
    "juan_fernando_c": {
        "password": hashlib.sha256("456".encode()).hexdigest(),
        "nombre":   "Juan Fernando C.",
        "rol":      "Solicitante",
    },
    "juan_pablo_w": {
        "password": hashlib.sha256("789".encode()).hexdigest(),
        "nombre":   "Juan Pablo W.",
        "rol":      "Revisor",
    },
}

# ─────────────────────────────────────────────
# BASE DE DATOS
# ─────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        # Tabla escritos
        conn.execute("""
            CREATE TABLE IF NOT EXISTS escritos (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre              TEXT    NOT NULL,
                nombre_archivo      TEXT    NOT NULL,
                mime_type           TEXT    NOT NULL,
                file_data           BLOB    NOT NULL,
                creador             TEXT    NOT NULL,
                creador_nombre      TEXT    NOT NULL,
                estado              TEXT    NOT NULL DEFAULT 'pendiente',
                fecha_creacion      TEXT    NOT NULL,
                fecha_presentado    TEXT,
                fecha_presentado_dt TEXT
            )
        """)
        # Tabla modelos (nunca se borran)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS modelos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre          TEXT    NOT NULL,
                descripcion     TEXT,
                nombre_archivo  TEXT    NOT NULL,
                mime_type       TEXT    NOT NULL,
                file_data       BLOB    NOT NULL,
                subido_por      TEXT    NOT NULL,
                subido_por_nombre TEXT  NOT NULL,
                fecha_subida    TEXT    NOT NULL
            )
        """)
        conn.commit()


# ── ESCRITOS ─────────────────────────────────

def purgar_escritos_expirados():
    """Borra escritos presentados hace más de DIAS_EXPIRACION días."""
    limite = (datetime.now() - timedelta(days=DIAS_EXPIRACION)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM escritos
            WHERE estado = 'presentado'
              AND fecha_presentado_dt IS NOT NULL
              AND fecha_presentado_dt <= ?
        """, (limite,))
        conn.commit()


def insertar_escrito(nombre, nombre_archivo, mime_type, file_data, creador, creador_nombre):
    fecha = datetime.now().strftime("%d %b %Y")
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO escritos
                (nombre, nombre_archivo, mime_type, file_data,
                 creador, creador_nombre, estado, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, 'pendiente', ?)
        """, (nombre, nombre_archivo, mime_type, file_data,
              creador, creador_nombre, fecha))
        conn.commit()


def marcar_presentado(id_escrito):
    fecha_legible = datetime.now().strftime("%d %b %Y")
    fecha_iso     = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        conn.execute("""
            UPDATE escritos
            SET estado = 'presentado',
                fecha_presentado    = ?,
                fecha_presentado_dt = ?
            WHERE id = ?
        """, (fecha_legible, fecha_iso, id_escrito))
        conn.commit()


def get_escritos_usuario(username):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, nombre, nombre_archivo, mime_type, file_data,
                   creador, creador_nombre, estado,
                   fecha_creacion, fecha_presentado, fecha_presentado_dt
            FROM escritos
            WHERE creador = ?
            ORDER BY id DESC
        """, (username,)).fetchall()
    return [dict(r) for r in rows]


def get_todos_escritos():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, nombre, nombre_archivo, mime_type, file_data,
                   creador, creador_nombre, estado,
                   fecha_creacion, fecha_presentado, fecha_presentado_dt
            FROM escritos
            ORDER BY id DESC
        """).fetchall()
    return [dict(r) for r in rows]


# ── MODELOS ──────────────────────────────────

def insertar_modelo(nombre, descripcion, nombre_archivo, mime_type, file_data, subido_por, subido_por_nombre):
    fecha = datetime.now().strftime("%d %b %Y")
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO modelos
                (nombre, descripcion, nombre_archivo, mime_type, file_data,
                 subido_por, subido_por_nombre, fecha_subida)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nombre, descripcion, nombre_archivo, mime_type,
              file_data, subido_por, subido_por_nombre, fecha))
        conn.commit()


def get_modelos():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, nombre, descripcion, nombre_archivo, mime_type, file_data,
                   subido_por, subido_por_nombre, fecha_subida
            FROM modelos
            ORDER BY id DESC
        """).fetchall()
    return [dict(r) for r in rows]


def eliminar_modelo(id_modelo):
    """Solo el Revisor puede eliminar modelos."""
    with get_conn() as conn:
        conn.execute("DELETE FROM modelos WHERE id = ?", (id_modelo,))
        conn.commit()


# ─────────────────────────────────────────────
# AUTENTICACIÓN
# ─────────────────────────────────────────────

def verificar_credenciales(username, password):
    if username not in USERS:
        return False
    return USERS[username]["password"] == hashlib.sha256(password.encode()).hexdigest()


def login_form():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="margin-top:60px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:24px;">
                    <div style="width:32px;height:32px;background:#5a67f2;border-radius:7px;
                                display:flex;align-items:center;justify-content:center;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                             stroke="white" stroke-width="2" stroke-linecap="round">
                            <line x1="12" y1="2" x2="12" y2="22"/>
                            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                        </svg>
                    </div>
                    <span style="font-family:Georgia,serif;font-size:22px;font-weight:600;color:#dde1ef;">
                        Lex<span style="color:#7a80a0;font-weight:400;">Docs</span>
                    </span>
                </div>
                <div style="font-size:18px;font-weight:600;color:#dde1ef;margin-bottom:4px;">
                    Iniciar sesión
                </div>
                <div style="font-size:12px;color:#7a80a0;margin-bottom:2px;">
                    Gestión de escritos legales - Banco Guayaquil-Consulegis
                </div>
                <div style="font-size:11px;color:#4a5070;margin-bottom:24px;">
                    Desarrollado por: Juan Fernando Camacho
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username  = st.text_input("Usuario", placeholder="ej. rafaela_b")
            password  = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Ingresar al sistema", use_container_width=True)
            if submitted:
                if verificar_credenciales(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username  = username
                    st.session_state.nombre    = USERS[username]["nombre"]
                    st.session_state.rol       = USERS[username]["rol"]
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")


# ─────────────────────────────────────────────
# UTILIDADES UI
# ─────────────────────────────────────────────

def file_preview_html(file_data: bytes, mime_type: str, filename: str) -> str:
    b64      = base64.b64encode(file_data).decode()
    data_url = f"data:{mime_type};base64,{b64}"
    if mime_type == "application/pdf":
        return f'<iframe src="{data_url}" width="100%" height="520px" style="border:none;border-radius:6px;"></iframe>'
    elif mime_type.startswith("image/"):
        return f'<img src="{data_url}" style="max-width:100%;border-radius:6px;" alt="{filename}">'
    else:
        ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "archivo"
        return f"""
            <div style="padding:40px;text-align:center;background:#1f2230;
                        border-radius:8px;color:#7a80a0;font-size:13px;">
                Vista previa no disponible para archivos <strong>{ext}</strong>.<br>
                Usa el botón Descargar para abrirlo en tu equipo.
            </div>"""


def download_link(file_data: bytes, filename: str, mime_type: str, label: str = "Descargar"):
    b64 = base64.b64encode(file_data).decode()
    st.markdown(f"""
        <a href="data:{mime_type};base64,{b64}" download="{filename}" style="
            display:inline-flex;align-items:center;gap:6px;
            padding:5px 12px;background:#5a67f2;color:white;
            border-radius:6px;font-size:12px;font-weight:600;text-decoration:none;">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                 stroke="white" stroke-width="2.5" stroke-linecap="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            {label}
        </a>""", unsafe_allow_html=True)


def dias_restantes(fecha_presentado_dt: str) -> int:
    try:
        f = datetime.strptime(fecha_presentado_dt, "%Y-%m-%d")
        expira = f + timedelta(days=DIAS_EXPIRACION)
        return max(0, (expira - datetime.now()).days)
    except Exception:
        return DIAS_EXPIRACION


def estado_badge(estado: str, fecha_presentado_dt: str = None) -> str:
    if estado == "pendiente":
        return """<span style="background:rgba(232,160,32,.08);color:#e8a020;
            border:1px solid rgba(232,160,32,.25);border-radius:10px;
            padding:2px 10px;font-size:11px;font-weight:600;">Pendiente</span>"""
    dias = dias_restantes(fecha_presentado_dt) if fecha_presentado_dt else DIAS_EXPIRACION
    color_exp = "#ef4444" if dias <= 2 else "#e8a020" if dias <= 4 else "#0ea271"
    return f"""<span style="background:rgba(14,162,113,.08);color:#0ea271;
        border:1px solid rgba(14,162,113,.22);border-radius:10px;
        padding:2px 10px;font-size:11px;font-weight:600;">Presentado</span>
        &nbsp;<span style="font-size:10px;color:{color_exp};font-weight:500;">
        expira en {dias}d</span>"""


# ─────────────────────────────────────────────
# PESTAÑA: ESCRITOS
# ─────────────────────────────────────────────

def render_escrito(e: dict, show_author: bool, show_mark: bool):
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"""
                <div style="font-weight:600;font-size:13px;color:#dde1ef;">{e['nombre']}</div>
                <div style="font-size:11px;color:#4a5070;margin-top:2px;">{e['nombre_archivo']}</div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(
                estado_badge(e["estado"], e.get("fecha_presentado_dt")),
                unsafe_allow_html=True
            )

        meta = [f"Subido: {e['fecha_creacion']}"]
        if show_author:
            meta.append(f"Por: {e['creador_nombre']}")
        if e["fecha_presentado"]:
            meta.append(f"Presentado: {e['fecha_presentado']}")
        st.markdown(
            f"<div style='font-size:11px;color:#7a80a0;margin-bottom:8px;'>{'  ·  '.join(meta)}</div>",
            unsafe_allow_html=True
        )

        btn_cols = st.columns([1, 1, 1, 2]) if show_mark else st.columns([1, 1, 3])

        with btn_cols[0]:
            if st.button("Ver", key=f"ver_e_{e['id']}", use_container_width=True):
                key = f"prev_e_{e['id']}"
                st.session_state[key] = not st.session_state.get(key, False)
        with btn_cols[1]:
            download_link(bytes(e["file_data"]), e["nombre_archivo"], e["mime_type"])

        if show_mark:
            with btn_cols[2]:
                if st.button("Marcar presentado", key=f"mark_{e['id']}",
                             type="primary", use_container_width=True):
                    marcar_presentado(e["id"])
                    st.rerun()

        if st.session_state.get(f"prev_e_{e['id']}", False):
            st.markdown(
                file_preview_html(bytes(e["file_data"]), e["mime_type"], e["nombre_archivo"]),
                unsafe_allow_html=True
            )


def tab_escritos():
    rol       = st.session_state.rol
    is_revisor = rol == "Revisor"

    if not is_revisor:
        # ── Formulario subida ──
        st.markdown("### Subir nuevo escrito")
        with st.form("form_escrito", clear_on_submit=True):
            nombre   = st.text_input("Nombre del escrito", placeholder="Ej: Demanda ejecutiva – Caso 2024-087")
            uploaded = st.file_uploader("Archivo", help="PDF, imágenes, Word. Máximo 10 MB.")
            submitted = st.form_submit_button("Subir escrito", use_container_width=False)
            if submitted:
                if not nombre.strip():
                    st.error("Ingresa el nombre del escrito.")
                elif uploaded is None:
                    st.error("Selecciona un archivo.")
                elif uploaded.size > 10 * 1024 * 1024:
                    st.error("El archivo supera los 10 MB.")
                else:
                    insertar_escrito(
                        nombre         = nombre.strip(),
                        nombre_archivo = uploaded.name,
                        mime_type      = uploaded.type or "application/octet-stream",
                        file_data      = uploaded.read(),
                        creador        = st.session_state.username,
                        creador_nombre = st.session_state.nombre,
                    )
                    st.success(f"Escrito **{nombre}** registrado correctamente.")
                    st.rerun()

        escritos    = get_escritos_usuario(st.session_state.username)
        pendientes  = [e for e in escritos if e["estado"] == "pendiente"]
        presentados = [e for e in escritos if e["estado"] == "presentado"]

        col1, col2 = st.columns(2)
        with col1:
            _section_header("Pendientes", len(pendientes), "yellow")
            if pendientes:
                for e in pendientes:
                    render_escrito(e, show_author=False, show_mark=False)
            else:
                _empty_state("Sin escritos pendientes")
        with col2:
            _section_header("Presentados", len(presentados), "green")
            if presentados:
                for e in presentados:
                    render_escrito(e, show_author=False, show_mark=False)
            else:
                _empty_state("Sin escritos presentados")

    else:
        # ── Vista Revisor ──
        todos       = get_todos_escritos()
        pendientes  = [e for e in todos if e["estado"] == "pendiente"]
        presentados = [e for e in todos if e["estado"] == "presentado"]

        ca, cb, cc = st.columns([3, 1, 1])
        with ca:
            st.markdown("""
                <div style="font-size:14px;font-weight:600;color:#dde1ef;">Panel del Revisor</div>
                <div style="font-size:12px;color:#7a80a0;">
                    Revisa los escritos de todos los solicitantes.
                </div>
            """, unsafe_allow_html=True)
        with cb:
            st.markdown(f"""<div style="text-align:center;padding:6px 0;">
                <div style="font-size:24px;font-weight:700;color:#e8a020;">{len(pendientes)}</div>
                <div style="font-size:10px;color:#7a80a0;text-transform:uppercase;">Pendientes</div>
            </div>""", unsafe_allow_html=True)
        with cc:
            st.markdown(f"""<div style="text-align:center;padding:6px 0;">
                <div style="font-size:24px;font-weight:700;color:#0ea271;">{len(presentados)}</div>
                <div style="font-size:10px;color:#7a80a0;text-transform:uppercase;">Presentados</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            _section_header("Pendientes", len(pendientes), "yellow")
            if pendientes:
                for e in pendientes:
                    render_escrito(e, show_author=True, show_mark=True)
            else:
                _empty_state("Sin escritos pendientes")
        with col2:
            _section_header("Presentados", len(presentados), "green")
            if presentados:
                for e in presentados:
                    render_escrito(e, show_author=True, show_mark=False)
            else:
                _empty_state("Sin escritos presentados")


# ─────────────────────────────────────────────
# PESTAÑA: MODELOS
# ─────────────────────────────────────────────

def tab_modelos():
    is_revisor = st.session_state.rol == "Revisor"

    st.markdown("### Subir nuevo modelo")
    with st.form("form_modelo", clear_on_submit=True):
        nombre      = st.text_input("Nombre del modelo", placeholder="Ej: Modelo de demanda ejecutiva")
        descripcion = st.text_area("Descripción (opcional)",
                                   placeholder="Breve descripción del uso de esta plantilla",
                                   height=80)
        uploaded    = st.file_uploader("Archivo (Word, PDF, etc.)", help="Máximo 10 MB.")
        submitted   = st.form_submit_button("Subir modelo", use_container_width=False)

        if submitted:
            if not nombre.strip():
                st.error("Ingresa el nombre del modelo.")
            elif uploaded is None:
                st.error("Selecciona un archivo.")
            elif uploaded.size > 10 * 1024 * 1024:
                st.error("El archivo supera los 10 MB.")
            else:
                insertar_modelo(
                    nombre            = nombre.strip(),
                    descripcion       = descripcion.strip(),
                    nombre_archivo    = uploaded.name,
                    mime_type         = uploaded.type or "application/octet-stream",
                    file_data         = uploaded.read(),
                    subido_por        = st.session_state.username,
                    subido_por_nombre = st.session_state.nombre,
                )
                st.success(f"Modelo **{nombre}** registrado correctamente.")
                st.rerun()

    st.divider()

    modelos = get_modelos()

    st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
            <div style="width:7px;height:7px;border-radius:50%;
                        background:#5a67f2;box-shadow:0 0 5px rgba(90,103,242,.6);"></div>
            <span style="font-size:13px;font-weight:600;">Plantillas disponibles</span>
            <span style="background:rgba(90,103,242,.1);color:#7b87f5;
                         border:1px solid rgba(90,103,242,.25);
                         border-radius:9px;padding:1px 8px;font-size:10px;font-weight:700;">
                {len(modelos)}
            </span>
        </div>
    """, unsafe_allow_html=True)

    if not modelos:
        _empty_state("No hay modelos cargados aún. Sube el primero.")
        return

    for m in modelos:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"""
                    <div style="font-weight:600;font-size:13px;color:#dde1ef;">{m['nombre']}</div>
                    <div style="font-size:11px;color:#4a5070;margin-top:2px;">{m['nombre_archivo']}</div>
                    {f'<div style="font-size:12px;color:#7a80a0;margin-top:4px;">{m["descripcion"]}</div>'
                      if m.get('descripcion') else ''}
                """, unsafe_allow_html=True)
            with c2:
                st.markdown("""
                    <span style="background:rgba(90,103,242,.1);color:#7b87f5;
                        border:1px solid rgba(90,103,242,.25);border-radius:10px;
                        padding:2px 10px;font-size:11px;font-weight:600;">Plantilla</span>
                """, unsafe_allow_html=True)

            st.markdown(
                f"<div style='font-size:11px;color:#7a80a0;margin-bottom:8px;'>"
                f"Subido por: {m['subido_por_nombre']}  ·  {m['fecha_subida']}</div>",
                unsafe_allow_html=True
            )

            btn_cols = st.columns([1, 1, 3]) if not is_revisor else st.columns([1, 1, 1, 2])

            with btn_cols[0]:
                if st.button("Ver", key=f"ver_m_{m['id']}", use_container_width=True):
                    key = f"prev_m_{m['id']}"
                    st.session_state[key] = not st.session_state.get(key, False)
            with btn_cols[1]:
                download_link(bytes(m["file_data"]), m["nombre_archivo"], m["mime_type"])

            # Solo el Revisor puede eliminar modelos
            if is_revisor:
                with btn_cols[2]:
                    if st.button("Eliminar", key=f"del_m_{m['id']}",
                                 use_container_width=True):
                        st.session_state[f"confirm_del_{m['id']}"] = True

                if st.session_state.get(f"confirm_del_{m['id']}", False):
                    st.warning(f"¿Eliminar el modelo **{m['nombre']}** permanentemente?")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("Sí, eliminar", key=f"yes_del_{m['id']}",
                                     type="primary", use_container_width=True):
                            eliminar_modelo(m["id"])
                            st.session_state.pop(f"confirm_del_{m['id']}", None)
                            st.rerun()
                    with cc2:
                        if st.button("Cancelar", key=f"no_del_{m['id']}",
                                     use_container_width=True):
                            st.session_state.pop(f"confirm_del_{m['id']}", None)
                            st.rerun()

            if st.session_state.get(f"prev_m_{m['id']}", False):
                st.markdown(
                    file_preview_html(bytes(m["file_data"]), m["mime_type"], m["nombre_archivo"]),
                    unsafe_allow_html=True
                )


# ─────────────────────────────────────────────
# HELPERS UI
# ─────────────────────────────────────────────

def _section_header(label: str, count: int, color: str):
    colors = {
        "yellow": ("#e8a020", "rgba(232,160,32,.08)", "rgba(232,160,32,.25)", "rgba(232,160,32,.6)"),
        "green":  ("#0ea271", "rgba(14,162,113,.08)",  "rgba(14,162,113,.22)",  "rgba(14,162,113,.6)"),
    }
    c, bg, border, glow = colors[color]
    st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <div style="width:7px;height:7px;border-radius:50%;
                        background:{c};box-shadow:0 0 5px {glow};"></div>
            <span style="font-size:13px;font-weight:600;">Escritos {label}</span>
            <span style="background:{bg};color:{c};border:1px solid {border};
                         border-radius:9px;padding:1px 8px;font-size:10px;font-weight:700;">
                {count}
            </span>
        </div>
    """, unsafe_allow_html=True)


def _empty_state(msg: str):
    st.markdown(f"""
        <div style="text-align:center;padding:28px 16px;color:#4a5070;
                    font-size:12.5px;border:1px solid #272b3d;border-radius:8px;">
            {msg}
        </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("""
            <div style="display:flex;align-items:center;gap:9px;margin-bottom:20px;padding:4px 0;">
                <div style="width:28px;height:28px;background:#5a67f2;border-radius:6px;
                            display:flex;align-items:center;justify-content:center;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                         stroke="white" stroke-width="2" stroke-linecap="round">
                        <line x1="12" y1="2" x2="12" y2="22"/>
                        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                    </svg>
                </div>
                <span style="font-family:Georgia,serif;font-size:18px;font-weight:600;color:#dde1ef;">
                    Lex<span style="color:#7a80a0;font-weight:400;">Docs</span>
                </span>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        rol   = st.session_state.rol
        color = "#0ea271" if rol == "Revisor" else "#7b87f5"
        bg    = "rgba(14,162,113,.12)" if rol == "Revisor" else "rgba(90,103,242,.12)"

        st.markdown(f"""
            <div style="background:{bg};border:1px solid {color}30;
                        border-radius:9px;padding:12px 14px;margin-bottom:16px;">
                <div style="font-size:13px;font-weight:600;color:#dde1ef;">
                    {st.session_state.nombre}
                </div>
                <div style="display:inline-block;margin-top:5px;background:{bg};
                            border:1px solid {color}40;border-radius:4px;padding:1px 8px;
                            font-size:10px;font-weight:700;color:{color};
                            text-transform:uppercase;letter-spacing:.5px;">
                    {rol}
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.markdown("""
            <div style="font-size:11px;color:#4a5070;line-height:1.8;margin-bottom:8px;">
                Banco Guayaquil - Consulegis<br>
                Desarrollado por:<br>
                <span style="color:#7a80a0;">Juan Fernando Camacho</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div style="font-size:10.5px;color:#4a5070;margin-top:8px;
                        padding:8px;background:#191c27;border-radius:6px;
                        border:1px solid #272b3d;">
                Los escritos presentados se eliminan automáticamente<br>
                después de <strong style="color:#7a80a0;">{DIAS_EXPIRACION} días</strong>.<br>
                Los modelos nunca se eliminan automáticamente.
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        if st.button("Cerrar sesión", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ─────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────

def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

        .stApp { background: #0c0e14; }
        header[data-testid="stHeader"] { background: #13151d; border-bottom: 1px solid #272b3d; }
        [data-testid="stSidebar"] { background: #13151d !important; border-right: 1px solid #272b3d !important; }

        /* Tabs */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            background: #13151d !important;
            border-bottom: 1px solid #272b3d !important;
            gap: 4px;
        }
        [data-testid="stTabs"] [data-baseweb="tab"] {
            background: transparent !important;
            color: #7a80a0 !important;
            border-radius: 6px 6px 0 0 !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 8px 20px !important;
        }
        [data-testid="stTabs"] [aria-selected="true"] {
            background: #191c27 !important;
            color: #dde1ef !important;
            border-bottom: 2px solid #5a67f2 !important;
        }
        [data-testid="stTabPanel"] { background: transparent !important; padding-top: 20px !important; }

        /* Inputs */
        [data-testid="stTextInput"] input { background: #191c27 !important; border: 1px solid #272b3d !important; border-radius: 7px !important; color: #dde1ef !important; font-size: 13px !important; }
        [data-testid="stTextInput"] input:focus { border-color: #5a67f2 !important; }
        [data-testid="stTextArea"] textarea { background: #191c27 !important; border: 1px solid #272b3d !important; border-radius: 7px !important; color: #dde1ef !important; font-size: 13px !important; }
        [data-testid="stFileUploader"] { background: #191c27 !important; border: 1px dashed #313654 !important; border-radius: 8px !important; }

        /* Buttons */
        .stButton > button { background: #191c27 !important; border: 1px solid #272b3d !important; color: #7a80a0 !important; border-radius: 6px !important; font-size: 12px !important; font-weight: 500 !important; transition: all .18s !important; }
        .stButton > button:hover { border-color: #3d4266 !important; color: #dde1ef !important; background: #1f2230 !important; }
        .stButton > button[kind="primary"] { background: rgba(14,162,113,.08) !important; border: 1px solid rgba(14,162,113,.25) !important; color: #0ea271 !important; font-weight: 600 !important; }
        .stButton > button[kind="primary"]:hover { background: rgba(14,162,113,.15) !important; }
        .stFormSubmitButton > button { background: #5a67f2 !important; color: white !important; border: none !important; font-weight: 600 !important; font-size: 13px !important; border-radius: 7px !important; }
        .stFormSubmitButton > button:hover { background: #7b87f5 !important; }

        /* Containers */
        [data-testid="stVerticalBlockBorderWrapper"] { background: #13151d !important; border: 1px solid #272b3d !important; border-radius: 10px !important; }

        p, label, div { color: #dde1ef; }
        h1, h2, h3 { color: #dde1ef !important; font-weight: 600 !important; }
        hr { border-color: #272b3d !important; }
        [data-testid="stAlert"] { border-radius: 8px !important; font-size: 13px !important; }
        #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
        [data-testid="stForm"] { background: #13151d !important; border: 1px solid #272b3d !important; border-radius: 10px !important; padding: 16px !important; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title            = "LexDocs — Gestor de Escritos",
        page_icon             = "⚖",
        layout                = "wide",
        initial_sidebar_state = "expanded",
    )

    inject_css()
    init_db()
    purgar_escritos_expirados()  # limpieza automática en cada carga

    if not st.session_state.get("logged_in"):
        login_form()
        return

    render_sidebar()

    rol = st.session_state.rol
    st.markdown(f"## {'Panel de Revisión' if rol == 'Revisor' else 'Panel del Solicitante'}")

    tab_e, tab_m = st.tabs(["Escritos", "Modelos / Plantillas"])

    with tab_e:
        tab_escritos()

    with tab_m:
        tab_modelos()


if __name__ == "__main__":
    main()
