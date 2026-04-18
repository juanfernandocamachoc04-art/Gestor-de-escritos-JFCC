"""
LexDocs — Gestión de Escritos Legales
Banco Guayaquil - Consulegis
Desarrollado por: Juan Fernando Camacho
"""

import streamlit as st
import sqlite3
import hashlib
import os
import base64
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

DB_PATH = "lexdocs.db"

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS escritos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre          TEXT    NOT NULL,
                nombre_archivo  TEXT    NOT NULL,
                mime_type       TEXT    NOT NULL,
                file_data       BLOB    NOT NULL,
                creador         TEXT    NOT NULL,
                creador_nombre  TEXT    NOT NULL,
                estado          TEXT    NOT NULL DEFAULT 'pendiente',
                fecha_creacion  TEXT    NOT NULL,
                fecha_presentado TEXT
            )
        """)
        conn.commit()


def insertar_escrito(nombre, nombre_archivo, mime_type, file_data, creador, creador_nombre):
    fecha = datetime.now().strftime("%d %b %Y")
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO escritos
                (nombre, nombre_archivo, mime_type, file_data, creador, creador_nombre, estado, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, 'pendiente', ?)
        """, (nombre, nombre_archivo, mime_type, file_data, creador, creador_nombre, fecha))
        conn.commit()


def marcar_presentado(id_escrito):
    fecha = datetime.now().strftime("%d %b %Y")
    with get_conn() as conn:
        conn.execute("""
            UPDATE escritos
            SET estado = 'presentado', fecha_presentado = ?
            WHERE id = ?
        """, (fecha, id_escrito))
        conn.commit()


def get_escritos_usuario(username):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, nombre, nombre_archivo, mime_type, file_data,
                   creador, creador_nombre, estado, fecha_creacion, fecha_presentado
            FROM escritos
            WHERE creador = ?
            ORDER BY id DESC
        """, (username,)).fetchall()
    return [dict(r) for r in rows]


def get_todos_escritos():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, nombre, nombre_archivo, mime_type, file_data,
                   creador, creador_nombre, estado, fecha_creacion, fecha_presentado
            FROM escritos
            ORDER BY id DESC
        """).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# AUTENTICACIÓN
# ─────────────────────────────────────────────

def verificar_credenciales(username, password):
    if username not in USERS:
        return False
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return USERS[username]["password"] == hashed


def login_form():
    st.markdown("""
        <div style="max-width:420px; margin:80px auto 0;">
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="
                background:#13151d;
                border:1px solid #272b3d;
                border-radius:14px;
                padding:40px 32px;
                box-shadow:0 20px 60px rgba(0,0,0,.5);
            ">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:24px;">
                    <div style="
                        width:32px;height:32px;
                        background:#5a67f2;
                        border-radius:7px;
                        display:flex;align-items:center;justify-content:center;
                    ">
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
                <div style="font-size:12px;color:#7a80a0;margin-bottom:4px;">
                    Gestión de escritos legales - Banco Guayaquil-Consulegis
                </div>
                <div style="font-size:11px;color:#4a5070;margin-bottom:24px;">
                    Desarrollado por: Juan Fernando Camacho
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Usuario", placeholder="ej. rafaela_b")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Ingresar al sistema", use_container_width=True)

            if submitted:
                if verificar_credenciales(username, password):
                    st.session_state.logged_in    = True
                    st.session_state.username     = username
                    st.session_state.nombre       = USERS[username]["nombre"]
                    st.session_state.rol          = USERS[username]["rol"]
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")


# ─────────────────────────────────────────────
# UTILIDADES UI
# ─────────────────────────────────────────────

def file_preview_html(file_data: bytes, mime_type: str, filename: str) -> str:
    """Genera HTML para previsualizar o descargar un archivo."""
    b64 = base64.b64encode(file_data).decode()
    data_url = f"data:{mime_type};base64,{b64}"

    if mime_type == "application/pdf":
        return f"""
            <iframe src="{data_url}" width="100%" height="500px"
                    style="border:none;border-radius:6px;"></iframe>
        """
    elif mime_type.startswith("image/"):
        return f"""
            <img src="{data_url}" style="max-width:100%;border-radius:6px;" alt="{filename}">
        """
    else:
        ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "archivo"
        return f"""
            <div style="
                padding:40px;text-align:center;
                background:#1f2230;border-radius:8px;
                color:#7a80a0;font-size:14px;
            ">
                <div style="font-size:36px;margin-bottom:12px;opacity:.4;">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
                         stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                </div>
                Vista previa no disponible para archivos <strong>{ext}</strong>.<br>
                Usa el botón Descargar para abrirlo en tu equipo.
            </div>
        """


def download_button(file_data: bytes, filename: str, mime_type: str, label: str = "Descargar"):
    b64 = base64.b64encode(file_data).decode()
    href = f'data:{mime_type};base64,{b64}'
    st.markdown(f"""
        <a href="{href}" download="{filename}" style="
            display:inline-flex;align-items:center;gap:6px;
            padding:6px 14px;
            background:#5a67f2;color:white;
            border-radius:6px;font-size:13px;font-weight:600;
            text-decoration:none;
        ">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                 stroke="white" stroke-width="2.5" stroke-linecap="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            {label}
        </a>
    """, unsafe_allow_html=True)


def estado_badge(estado: str) -> str:
    if estado == "pendiente":
        return """<span style="
            background:rgba(232,160,32,.08);color:#e8a020;
            border:1px solid rgba(232,160,32,.25);
            border-radius:10px;padding:2px 10px;font-size:11px;font-weight:600;
        ">Pendiente</span>"""
    return """<span style="
        background:rgba(14,162,113,.08);color:#0ea271;
        border:1px solid rgba(14,162,113,.22);
        border-radius:10px;padding:2px 10px;font-size:11px;font-weight:600;
    ">Presentado</span>"""


# ─────────────────────────────────────────────
# VISTAS
# ─────────────────────────────────────────────

def vista_solicitante():
    st.markdown("### Subir nuevo escrito")

    with st.form("upload_form", clear_on_submit=True):
        nombre   = st.text_input("Nombre del escrito", placeholder="Ej: Demanda ejecutiva – Caso 2024-087")
        uploaded = st.file_uploader("Archivo", type=None, help="PDF, imágenes, Word. Máximo 10 MB.")
        submitted = st.form_submit_button("Subir escrito", use_container_width=False)

        if submitted:
            if not nombre.strip():
                st.error("Ingresa el nombre del escrito.")
            elif uploaded is None:
                st.error("Selecciona un archivo.")
            elif uploaded.size > 10 * 1024 * 1024:
                st.error("El archivo supera los 10 MB permitidos.")
            else:
                file_data = uploaded.read()
                insertar_escrito(
                    nombre         = nombre.strip(),
                    nombre_archivo = uploaded.name,
                    mime_type      = uploaded.type or "application/octet-stream",
                    file_data      = file_data,
                    creador        = st.session_state.username,
                    creador_nombre = st.session_state.nombre,
                )
                st.success(f"Escrito **{nombre}** registrado correctamente.")
                st.rerun()

    escritos = get_escritos_usuario(st.session_state.username)
    pendientes  = [e for e in escritos if e["estado"] == "pendiente"]
    presentados = [e for e in escritos if e["estado"] == "presentado"]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <div style="width:7px;height:7px;border-radius:50%;
                            background:#e8a020;box-shadow:0 0 5px rgba(232,160,32,.6);"></div>
                <span style="font-size:13px;font-weight:600;">Escritos Pendientes</span>
                <span style="background:rgba(232,160,32,.08);color:#e8a020;
                             border:1px solid rgba(232,160,32,.22);
                             border-radius:9px;padding:1px 8px;font-size:10px;font-weight:700;">
                    {len(pendientes)}
                </span>
            </div>
        """, unsafe_allow_html=True)
        render_tabla(pendientes, show_author=False, show_mark=False)

    with col2:
        st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <div style="width:7px;height:7px;border-radius:50%;
                            background:#0ea271;box-shadow:0 0 5px rgba(14,162,113,.6);"></div>
                <span style="font-size:13px;font-weight:600;">Escritos Presentados</span>
                <span style="background:rgba(14,162,113,.08);color:#0ea271;
                             border:1px solid rgba(14,162,113,.22);
                             border-radius:9px;padding:1px 8px;font-size:10px;font-weight:700;">
                    {len(presentados)}
                </span>
            </div>
        """, unsafe_allow_html=True)
        render_tabla(presentados, show_author=False, show_mark=False)


def vista_revisor():
    todos       = get_todos_escritos()
    pendientes  = [e for e in todos if e["estado"] == "pendiente"]
    presentados = [e for e in todos if e["estado"] == "presentado"]

    col_a, col_b, col_c = st.columns([3, 1, 1])
    with col_a:
        st.markdown("""
            <div>
                <div style="font-size:15px;font-weight:600;margin-bottom:3px;">Panel del Revisor</div>
                <div style="font-size:12px;color:#7a80a0;">
                    Revisa los escritos de todos los solicitantes y marca los que han sido presentados.
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
            <div style="text-align:center;padding:8px 0;">
                <div style="font-size:26px;font-weight:700;color:#e8a020;">{len(pendientes)}</div>
                <div style="font-size:10px;color:#7a80a0;text-transform:uppercase;letter-spacing:.4px;">Pendientes</div>
            </div>
        """, unsafe_allow_html=True)
    with col_c:
        st.markdown(f"""
            <div style="text-align:center;padding:8px 0;">
                <div style="font-size:26px;font-weight:700;color:#0ea271;">{len(presentados)}</div>
                <div style="font-size:10px;color:#7a80a0;text-transform:uppercase;letter-spacing:.4px;">Presentados</div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <div style="width:7px;height:7px;border-radius:50%;
                            background:#e8a020;box-shadow:0 0 5px rgba(232,160,32,.6);"></div>
                <span style="font-size:13px;font-weight:600;">Escritos Pendientes</span>
                <span style="background:rgba(232,160,32,.08);color:#e8a020;
                             border:1px solid rgba(232,160,32,.22);
                             border-radius:9px;padding:1px 8px;font-size:10px;font-weight:700;">
                    {len(pendientes)}
                </span>
            </div>
        """, unsafe_allow_html=True)
        render_tabla(pendientes, show_author=True, show_mark=True)

    with col2:
        st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <div style="width:7px;height:7px;border-radius:50%;
                            background:#0ea271;box-shadow:0 0 5px rgba(14,162,113,.6);"></div>
                <span style="font-size:13px;font-weight:600;">Escritos Presentados</span>
                <span style="background:rgba(14,162,113,.08);color:#0ea271;
                             border:1px solid rgba(14,162,113,.22);
                             border-radius:9px;padding:1px 8px;font-size:10px;font-weight:700;">
                    {len(presentados)}
                </span>
            </div>
        """, unsafe_allow_html=True)
        render_tabla(presentados, show_author=True, show_mark=False)


def render_tabla(escritos: list, show_author: bool, show_mark: bool):
    if not escritos:
        st.markdown("""
            <div style="
                text-align:center;padding:32px 16px;
                color:#4a5070;font-size:13px;
                border:1px solid #272b3d;border-radius:8px;
            ">
                Sin escritos registrados
            </div>
        """, unsafe_allow_html=True)
        return

    for e in escritos:
        with st.container(border=True):
            # Fila superior: nombre + estado
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"""
                    <div style="font-weight:600;font-size:13px;color:#dde1ef;">{e['nombre']}</div>
                    <div style="font-size:11px;color:#4a5070;margin-top:2px;">{e['nombre_archivo']}</div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(estado_badge(e["estado"]), unsafe_allow_html=True)

            # Metadatos
            meta_parts = [f"Subido: {e['fecha_creacion']}"]
            if show_author:
                meta_parts.append(f"Por: {e['creador_nombre']}")
            if e["fecha_presentado"]:
                meta_parts.append(f"Presentado: {e['fecha_presentado']}")

            st.markdown(
                f"<div style='font-size:11px;color:#7a80a0;margin-bottom:8px;'>"
                + "  ·  ".join(meta_parts)
                + "</div>",
                unsafe_allow_html=True
            )

            # Botones
            btn_cols = st.columns([1, 1, 1, 2]) if show_mark else st.columns([1, 1, 3])

            # Vista previa
            with btn_cols[0]:
                if st.button("Ver", key=f"ver_{e['id']}", use_container_width=True):
                    st.session_state[f"preview_{e['id']}"] = not st.session_state.get(f"preview_{e['id']}", False)

            # Descarga
            with btn_cols[1]:
                download_button(
                    file_data = bytes(e["file_data"]),
                    filename  = e["nombre_archivo"],
                    mime_type = e["mime_type"],
                    label     = "Descargar",
                )

            # Marcar presentado (solo Revisor, solo pendientes)
            if show_mark:
                with btn_cols[2]:
                    if st.button(
                        "Marcar presentado",
                        key=f"mark_{e['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        marcar_presentado(e["id"])
                        st.rerun()

            # Vista previa expandible
            if st.session_state.get(f"preview_{e['id']}", False):
                html_preview = file_preview_html(
                    bytes(e["file_data"]), e["mime_type"], e["nombre_archivo"]
                )
                st.markdown(html_preview, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────

def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

        .stApp { background: #0c0e14; }

        /* Header */
        header[data-testid="stHeader"] { background: #13151d; border-bottom: 1px solid #272b3d; }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: #13151d !important;
            border-right: 1px solid #272b3d !important;
        }

        /* Inputs */
        [data-testid="stTextInput"] input,
        [data-testid="stTextInput"] input:focus {
            background: #191c27 !important;
            border: 1px solid #272b3d !important;
            border-radius: 7px !important;
            color: #dde1ef !important;
            font-size: 13.5px !important;
        }

        [data-testid="stTextInput"] input:focus { border-color: #5a67f2 !important; }

        /* File uploader */
        [data-testid="stFileUploader"] {
            background: #191c27 !important;
            border: 1px dashed #313654 !important;
            border-radius: 8px !important;
        }

        /* Buttons */
        .stButton > button {
            background: #191c27 !important;
            border: 1px solid #272b3d !important;
            color: #7a80a0 !important;
            border-radius: 6px !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            padding: 4px 10px !important;
            transition: all .18s !important;
        }

        .stButton > button:hover {
            border-color: #3d4266 !important;
            color: #dde1ef !important;
            background: #1f2230 !important;
        }

        .stButton > button[kind="primary"] {
            background: rgba(14,162,113,.08) !important;
            border: 1px solid rgba(14,162,113,.25) !important;
            color: #0ea271 !important;
            font-weight: 600 !important;
        }

        .stButton > button[kind="primary"]:hover {
            background: rgba(14,162,113,.15) !important;
            border-color: rgba(14,162,113,.45) !important;
        }

        /* Form submit button */
        .stFormSubmitButton > button {
            background: #5a67f2 !important;
            color: white !important;
            border: none !important;
            font-weight: 600 !important;
            font-size: 13.5px !important;
            border-radius: 7px !important;
            padding: 10px 20px !important;
        }

        .stFormSubmitButton > button:hover { background: #7b87f5 !important; }

        /* Containers */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
            background: #13151d !important;
            border: 1px solid #272b3d !important;
            border-radius: 10px !important;
        }

        /* Text */
        p, label, span, div { color: #dde1ef; }
        h1, h2, h3 { color: #dde1ef !important; font-weight: 600 !important; }

        /* Divider */
        hr { border-color: #272b3d !important; }

        /* Alerts */
        [data-testid="stAlert"] { border-radius: 8px !important; font-size: 13px !important; }

        /* Hide Streamlit branding */
        #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

        /* Form container */
        [data-testid="stForm"] {
            background: #13151d !important;
            border: 1px solid #272b3d !important;
            border-radius: 10px !important;
            padding: 16px !important;
        }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        # Marca
        st.markdown("""
            <div style="display:flex;align-items:center;gap:9px;margin-bottom:20px;padding:4px 0;">
                <div style="
                    width:28px;height:28px;background:#5a67f2;
                    border-radius:6px;display:flex;align-items:center;justify-content:center;
                ">
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

        # Info usuario
        rol   = st.session_state.rol
        color = "#0ea271" if rol == "Revisor" else "#7b87f5"
        bg    = "rgba(14,162,113,.12)" if rol == "Revisor" else "rgba(90,103,242,.12)"

        st.markdown(f"""
            <div style="
                background:{bg};
                border:1px solid {color}30;
                border-radius:9px;
                padding:12px 14px;
                margin-bottom:16px;
            ">
                <div style="font-size:13px;font-weight:600;color:#dde1ef;">
                    {st.session_state.nombre}
                </div>
                <div style="
                    display:inline-block;margin-top:5px;
                    background:{bg};border:1px solid {color}40;
                    border-radius:4px;padding:1px 8px;
                    font-size:10px;font-weight:700;color:{color};
                    text-transform:uppercase;letter-spacing:.5px;
                ">
                    {rol}
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Info app
        st.markdown("""
            <div style="font-size:11px;color:#4a5070;line-height:1.7;margin-bottom:8px;">
                Banco Guayaquil - Consulegis<br>
                Desarrollado por:<br>
                <span style="color:#7a80a0;">Juan Fernando Camacho</span>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Logout
        if st.button("Cerrar sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title = "LexDocs — Gestor de Escritos",
        page_icon  = "⚖",
        layout     = "wide",
        initial_sidebar_state = "expanded",
    )

    inject_css()
    init_db()

    if not st.session_state.get("logged_in"):
        login_form()
        return

    render_sidebar()

    # Título de sección
    rol = st.session_state.rol
    if rol == "Revisor":
        st.markdown("## Panel de Revisión")
        vista_revisor()
    else:
        st.markdown("## Panel del Solicitante")
        vista_solicitante()


if __name__ == "__main__":
    main()
