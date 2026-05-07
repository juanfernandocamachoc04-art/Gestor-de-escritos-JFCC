"""
LexDocs — Gestión de Escritos Legales
Banco Guayaquil - Consulegis
Desarrollado por: Juan Fernando Camacho
"""

import streamlit as st
import hashlib
import base64
import os
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

DIAS_EXPIRACION = 7

# Estados válidos y sus propiedades visuales
ESTADOS = {
    "pendiente":  {"label": "Pendiente",  "color": "#e8a020", "bg": "rgba(232,160,32,.08)", "border": "rgba(232,160,32,.25)"},
    "observado":  {"label": "Observado",  "color": "#ef4444", "bg": "rgba(239,68,68,.08)",  "border": "rgba(239,68,68,.25)"},
    "presentado": {"label": "Presentado", "color": "#0ea271", "bg": "rgba(14,162,113,.08)", "border": "rgba(14,162,113,.22)"},
}

# Usuarios con permisos puede_filtrar para JFC y Revisor
USERS = {
    "rafaela_b": {
        "password":      hashlib.sha256("123".encode()).hexdigest(),
        "nombre":        "Rafaela B.",
        "rol":           "Solicitante",
        "puede_eliminar": False,
        "puede_filtrar":  False,
    },
    "juan_fernando_c": {
        "password":      hashlib.sha256("456".encode()).hexdigest(),
        "nombre":        "Juan Fernando C.",
        "rol":           "Solicitante",
        "puede_eliminar": True,
        "puede_filtrar":  True,
    },
    "juan_pablo_w": {
        "password":      hashlib.sha256("789".encode()).hexdigest(),
        "nombre":        "Juan Pablo W.",
        "rol":           "Revisor",
        "puede_eliminar": False,
        "puede_filtrar":  True,
    },
}

# ─────────────────────────────────────────────
# CONEXIÓN — PostgreSQL (Supabase) o SQLite
# ─────────────────────────────────────────────

def _get_db_url():
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return os.environ.get("DATABASE_URL", "")


def get_conn():
    url = _get_db_url()
    if url:
        try:
            import psycopg2
            conn = psycopg2.connect(url, connect_timeout=10)
            conn.autocommit = False
            return conn, "pg"
        except Exception as e:
            st.warning(f"No se pudo conectar a la base de datos remota ({e}).")
    import sqlite3
    conn = sqlite3.connect("lexdocs.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def execute(sql, params=(), fetch=None):
    conn, engine = get_conn()
    if engine == "pg":
        sql = sql.replace("?", "%s")
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        result = None
        if fetch == "one":
            row = cur.fetchone()
            if engine == "pg" and row:
                cols = [d[0] for d in cur.description]
                result = dict(zip(cols, row))
            elif row:
                result = dict(row)
        elif fetch == "all":
            rows = cur.fetchall()
            if engine == "pg":
                cols = [d[0] for d in cur.description]
                result = [dict(zip(cols, r)) for r in rows]
            else:
                result = [dict(r) for r in rows]
        conn.commit()
        return result
    finally:
        conn.close()


# ─────────────────────────────────────────────
# BASE DE DATOS — INIT Y MIGRACIÓN
# ─────────────────────────────────────────────

def init_db():
    conn, engine = get_conn()
    try:
        cur = conn.cursor()
        if engine == "pg":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS escritos (
                    id                  SERIAL PRIMARY KEY,
                    nombre              TEXT    NOT NULL,
                    nombre_archivo      TEXT    NOT NULL,
                    mime_type           TEXT    NOT NULL DEFAULT 'application/octet-stream',
                    file_data           BYTEA   NOT NULL,
                    creador             TEXT    NOT NULL,
                    creador_nombre      TEXT    NOT NULL DEFAULT '',
                    estado              TEXT    NOT NULL DEFAULT 'pendiente',
                    fecha_creacion      TEXT    NOT NULL,
                    fecha_presentado    TEXT,
                    fecha_presentado_dt TEXT,
                    observacion         TEXT,
                    version             INTEGER NOT NULL DEFAULT 1,
                    num_expediente      TEXT    NOT NULL DEFAULT '',
                    tipo_escrito        TEXT    NOT NULL DEFAULT '',
                    carpeta_anio         TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS modelos (
                    id                SERIAL PRIMARY KEY,
                    nombre            TEXT    NOT NULL,
                    descripcion       TEXT,
                    nombre_archivo    TEXT    NOT NULL,
                    mime_type         TEXT    NOT NULL DEFAULT 'application/octet-stream',
                    file_data         BYTEA   NOT NULL,
                    subido_por        TEXT    NOT NULL,
                    subido_por_nombre TEXT    NOT NULL DEFAULT '',
                    fecha_subida      TEXT    NOT NULL
                )
            """)
            # Migración PostgreSQL — cada ALTER en su propia transacción
            migraciones = [
                ("observacion",    "ALTER TABLE escritos ADD COLUMN IF NOT EXISTS observacion TEXT"),
                ("version",        "ALTER TABLE escritos ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1"),
                ("num_expediente", "ALTER TABLE escritos ADD COLUMN IF NOT EXISTS num_expediente TEXT NOT NULL DEFAULT ''"),
                ("tipo_escrito",   "ALTER TABLE escritos ADD COLUMN IF NOT EXISTS tipo_escrito TEXT NOT NULL DEFAULT ''"),
                ("carpeta_anio",   "ALTER TABLE escritos ADD COLUMN IF NOT EXISTS carpeta_anio TEXT"),
            ]
            for _, ddl in migraciones:
                try:
                    cur.execute(ddl)
                    conn.commit()
                except Exception:
                    conn.rollback()
            # Renombrar carpeta_año → carpeta_anio si existe con la ñ
            try:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'escritos' AND column_name = 'carpeta_año'
                """)
                if cur.fetchone():
                    cur.execute('ALTER TABLE escritos RENAME COLUMN "carpeta_año" TO carpeta_anio')
                    conn.commit()
            except Exception:
                conn.rollback()
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS escritos (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre              TEXT    NOT NULL,
                    nombre_archivo      TEXT    NOT NULL,
                    mime_type           TEXT    NOT NULL DEFAULT 'application/octet-stream',
                    file_data           BLOB    NOT NULL,
                    creador             TEXT    NOT NULL,
                    creador_nombre      TEXT    NOT NULL DEFAULT '',
                    estado              TEXT    NOT NULL DEFAULT 'pendiente',
                    fecha_creacion      TEXT    NOT NULL,
                    fecha_presentado    TEXT,
                    fecha_presentado_dt TEXT,
                    observacion         TEXT,
                    version             INTEGER NOT NULL DEFAULT 1,
                    num_expediente      TEXT    NOT NULL DEFAULT '',
                    tipo_escrito        TEXT    NOT NULL DEFAULT '',
                    carpeta_anio         TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS modelos (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre            TEXT    NOT NULL,
                    descripcion       TEXT,
                    nombre_archivo    TEXT    NOT NULL,
                    mime_type         TEXT    NOT NULL DEFAULT 'application/octet-stream',
                    file_data         BLOB    NOT NULL,
                    subido_por        TEXT    NOT NULL,
                    subido_por_nombre TEXT    NOT NULL DEFAULT '',
                    fecha_subida      TEXT    NOT NULL
                )
            """)
            cols = {r[1] for r in cur.execute("PRAGMA table_info(escritos)")}
            for col, ddl in [
                ("fecha_presentado_dt", "ALTER TABLE escritos ADD COLUMN fecha_presentado_dt TEXT"),
                ("mime_type",           "ALTER TABLE escritos ADD COLUMN mime_type TEXT NOT NULL DEFAULT 'application/octet-stream'"),
                ("creador_nombre",      "ALTER TABLE escritos ADD COLUMN creador_nombre TEXT NOT NULL DEFAULT ''"),
                ("observacion",         "ALTER TABLE escritos ADD COLUMN observacion TEXT"),
                ("version",             "ALTER TABLE escritos ADD COLUMN version INTEGER NOT NULL DEFAULT 1"),
                ("num_expediente",      "ALTER TABLE escritos ADD COLUMN num_expediente TEXT NOT NULL DEFAULT ''"),
                ("tipo_escrito",        "ALTER TABLE escritos ADD COLUMN tipo_escrito TEXT NOT NULL DEFAULT ''"),
                ("carpeta_anio",        "ALTER TABLE escritos ADD COLUMN carpeta_anio TEXT"),
            ]:
                if col not in cols:
                    cur.execute(ddl)
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# OPERACIONES — ESCRITOS
# ─────────────────────────────────────────────

def purgar_escritos_expirados():
    limite = (datetime.now() - timedelta(days=DIAS_EXPIRACION)).strftime("%Y-%m-%d")
    execute("""
        DELETE FROM escritos
        WHERE estado = 'presentado'
          AND fecha_presentado_dt IS NOT NULL
          AND fecha_presentado_dt <= ?
    """, (limite,))


def insertar_escrito(nombre, num_expediente, tipo_escrito, nombre_archivo, mime_type, file_data, creador, creador_nombre, version=1):
    fecha = datetime.now().strftime("%d %b %Y")
    conn, engine = get_conn()
    try:
        cur = conn.cursor()
        if engine == "pg":
            from psycopg2 import Binary
            cur.execute("""
                INSERT INTO escritos
                    (nombre, num_expediente, tipo_escrito, nombre_archivo, mime_type, file_data,
                     creador, creador_nombre, estado, fecha_creacion, version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendiente', %s, %s)
            """, (nombre, num_expediente, tipo_escrito, nombre_archivo, mime_type, Binary(file_data),
                  creador, creador_nombre, fecha, version))
        else:
            cur.execute("""
                INSERT INTO escritos
                    (nombre, num_expediente, tipo_escrito, nombre_archivo, mime_type, file_data,
                     creador, creador_nombre, estado, fecha_creacion, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?)
            """, (nombre, num_expediente, tipo_escrito, nombre_archivo, mime_type, file_data,
                  creador, creador_nombre, fecha, version))
        conn.commit()
    finally:
        conn.close()


def marcar_presentado(id_escrito):
    fecha_legible = datetime.now().strftime("%d %b %Y")
    fecha_iso     = datetime.now().strftime("%Y-%m-%d")
    execute("""
        UPDATE escritos
        SET estado = 'presentado',
            fecha_presentado    = ?,
            fecha_presentado_dt = ?,
            observacion         = NULL
        WHERE id = ?
    """, (fecha_legible, fecha_iso, id_escrito))


def marcar_observado(id_escrito, observacion: str):
    execute("""
        UPDATE escritos
        SET estado = 'observado', observacion = ?
        WHERE id = ?
    """, (observacion, id_escrito))


def eliminar_escrito(id_escrito):
    execute("DELETE FROM escritos WHERE id = ?", (id_escrito,))


def get_escritos_usuario(username):
    rows = execute("""
        SELECT id, nombre, num_expediente, tipo_escrito, nombre_archivo, mime_type, file_data,
               creador, creador_nombre, estado,
               fecha_creacion, fecha_presentado, fecha_presentado_dt,
               observacion, version
        FROM escritos
        WHERE creador = ?
        ORDER BY id DESC
    """, (username,), fetch="all") or []
    # Intentar obtener carpeta_anio por separado para no romper si no existe
    for r in rows:
        r.setdefault("carpeta_anio", None)
    try:
        extras = execute("""
            SELECT id, carpeta_anio FROM escritos WHERE creador = ?
        """, (username,), fetch="all") or []
        extra_map = {e["id"]: e["carpeta_anio"] for e in extras}
        for r in rows:
            r["carpeta_anio"] = extra_map.get(r["id"])
    except Exception:
        pass
    return rows


def get_todos_escritos():
    rows = execute("""
        SELECT id, nombre, num_expediente, tipo_escrito, nombre_archivo, mime_type, file_data,
               creador, creador_nombre, estado,
               fecha_creacion, fecha_presentado, fecha_presentado_dt,
               observacion, version
        FROM escritos
        ORDER BY id DESC
    """, fetch="all") or []
    for r in rows:
        r.setdefault("carpeta_anio", None)
    try:
        extras = execute("SELECT id, carpeta_anio FROM escritos", fetch="all") or []
        extra_map = {e["id"]: e["carpeta_anio"] for e in extras}
        for r in rows:
            r["carpeta_anio"] = extra_map.get(r["id"])
    except Exception:
        pass
    return rows


# ─────────────────────────────────────────────
# OPERACIONES — MODELOS
# ─────────────────────────────────────────────

def insertar_modelo(nombre, descripcion, nombre_archivo, mime_type, file_data, subido_por, subido_por_nombre):
    fecha = datetime.now().strftime("%d %b %Y")
    conn, engine = get_conn()
    try:
        cur = conn.cursor()
        if engine == "pg":
            from psycopg2 import Binary
            cur.execute("""
                INSERT INTO modelos
                    (nombre, descripcion, nombre_archivo, mime_type, file_data,
                     subido_por, subido_por_nombre, fecha_subida)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, descripcion, nombre_archivo, mime_type, Binary(file_data),
                  subido_por, subido_por_nombre, fecha))
        else:
            cur.execute("""
                INSERT INTO modelos
                    (nombre, descripcion, nombre_archivo, mime_type, file_data,
                     subido_por, subido_por_nombre, fecha_subida)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (nombre, descripcion, nombre_archivo, mime_type, file_data,
                  subido_por, subido_por_nombre, fecha))
        conn.commit()
    finally:
        conn.close()


def get_modelos():
    return execute("""
        SELECT id, nombre, descripcion, nombre_archivo, mime_type, file_data,
               subido_por, subido_por_nombre, fecha_subida
        FROM modelos
        ORDER BY id DESC
    """, fetch="all") or []


def eliminar_modelo(id_modelo):
    execute("DELETE FROM modelos WHERE id = ?", (id_modelo,))


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def to_bytes(val) -> bytes:
    if isinstance(val, (memoryview, bytearray)):
        return bytes(val)
    return val


def verificar_credenciales(username, password):
    if username not in USERS:
        return False
    return USERS[username]["password"] == hashlib.sha256(password.encode()).hexdigest()


def dias_restantes(fecha_presentado_dt: str) -> int:
    try:
        f = datetime.strptime(fecha_presentado_dt, "%Y-%m-%d")
        return max(0, (f + timedelta(days=DIAS_EXPIRACION) - datetime.now()).days)
    except Exception:
        return DIAS_EXPIRACION


def estado_badge(estado: str, fecha_presentado_dt=None, version=1) -> str:
    cfg = ESTADOS.get(estado, ESTADOS["pendiente"])
    extra = ""
    if estado == "presentado" and fecha_presentado_dt:
        dias = dias_restantes(fecha_presentado_dt)
        ec = "#ef4444" if dias <= 2 else "#e8a020" if dias <= 4 else "#0ea271"
        extra = f'&nbsp;<span style="font-size:10px;color:{ec};font-weight:500;">expira en {dias}d</span>'
    if version > 1:
        extra += f'&nbsp;<span style="font-size:10px;color:#7a80a0;">v{version}</span>'
    return (f'<span style="background:{cfg["bg"]};color:{cfg["color"]};'
            f'border:1px solid {cfg["border"]};border-radius:10px;'
            f'padding:2px 10px;font-size:11px;font-weight:600;">{cfg["label"]}</span>{extra}')


def render_preview(file_data: bytes, mime_type: str, filename: str):
    import streamlit.components.v1 as components
    if mime_type == "application/pdf":
        b64 = base64.b64encode(file_data).decode()
        components.html(
            f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600" '
            f'style="border:1px solid #272b3d;border-radius:8px;"></iframe>',
            height=620, scrolling=False)
    elif mime_type.startswith("image/"):
        st.image(file_data, use_container_width=True)
    else:
        ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "archivo"
        st.info(f"Vista previa no disponible para archivos **{ext}**. Usa Descargar para abrirlo.")


def download_link(file_data: bytes, filename: str, mime_type: str, label: str = "Descargar"):
    b64 = base64.b64encode(file_data).decode()
    st.markdown(f"""
        <a href="data:{mime_type};base64,{b64}" download="{filename}" style="
            display:inline-flex;align-items:center;gap:6px;padding:5px 12px;
            background:#5a67f2;color:white;border-radius:6px;
            font-size:12px;font-weight:600;text-decoration:none;">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                 stroke="white" stroke-width="2.5" stroke-linecap="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>{label}</a>""", unsafe_allow_html=True)


def _section_header(label, count, color):
    cfg = {
        "yellow": ("#e8a020","rgba(232,160,32,.08)","rgba(232,160,32,.25)","rgba(232,160,32,.6)"),
        "green":  ("#0ea271","rgba(14,162,113,.08)", "rgba(14,162,113,.22)", "rgba(14,162,113,.6)"),
        "red":    ("#ef4444","rgba(239,68,68,.08)",  "rgba(239,68,68,.25)",  "rgba(239,68,68,.6)"),
    }[color]
    st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <div style="width:7px;height:7px;border-radius:50%;
                        background:{cfg[0]};box-shadow:0 0 5px {cfg[3]};"></div>
            <span style="font-size:13px;font-weight:600;">Escritos {label}</span>
            <span style="background:{cfg[1]};color:{cfg[0]};border:1px solid {cfg[2]};
                         border-radius:9px;padding:1px 8px;font-size:10px;font-weight:700;">{count}</span>
        </div>""", unsafe_allow_html=True)


def _empty_state(msg):
    st.markdown(f"""<div style="text-align:center;padding:28px 16px;color:#4a5070;
                    font-size:12.5px;border:1px solid #272b3d;border-radius:8px;">{msg}</div>""",
                unsafe_allow_html=True)


def render_por_año(escritos: list, show_author: bool, show_mark: bool,
                   show_delete: bool, estado: str, key_suffix: str,
                   puede_asignar: bool = False):
    """Agrupa escritos por año y renderiza cada grupo en un expander colapsable.
    Escritos sin carpeta se muestran sueltos al final sin ningún expander.
    """
    if not escritos:
        _empty_state(f"Sin escritos {estado}")
        return

    color_map = {
        "pendiente":  "#e8a020",
        "observado":  "#ef4444",
        "presentado": "#0ea271",
    }
    color = color_map.get(estado, "#7a80a0")

    # Agrupar — separar los que tienen carpeta de los que no
    grupos: dict = {}
    sin_carpeta: list = []
    for e in escritos:
        c = _get_carpeta(e)
        if c:
            grupos.setdefault(c, []).append(e)
        else:
            sin_carpeta.append(e)

    # Ordenar años descendente
    años_ordenados = sorted(grupos.keys(), reverse=True)

    for año in años_ordenados:
        grupo = grupos[año]
        label = f"Carpeta {año}  —  {len(grupo)} escrito{'s' if len(grupo) != 1 else ''}"
        expandido = (año == años_ordenados[0])
        with st.expander(label, expanded=expandido):
            st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;
                            padding:8px 12px;background:rgba(255,255,255,.03);
                            border-radius:7px;border-left:3px solid {color};">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                         stroke="{color}" stroke-width="2" stroke-linecap="round">
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                    </svg>
                    <span style="font-size:12px;font-weight:600;color:{color};">{año}</span>
                    <span style="font-size:11px;color:#7a80a0;">{len(grupo)} escrito{'s' if len(grupo) != 1 else ''}</span>
                </div>
            """, unsafe_allow_html=True)
            for e in grupo:
                render_escrito(e, show_author, show_mark,
                               show_delete=show_delete,
                               puede_asignar=puede_asignar)

    # Escritos sin carpeta — sueltos, sin expander
    if sin_carpeta:
        if años_ordenados:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        for e in sin_carpeta:
            render_escrito(e, show_author, show_mark,
                           show_delete=show_delete,
                           puede_asignar=puede_asignar)


# ─────────────────────────────────────────────
# FILTROS / ORDENAMIENTO
# ─────────────────────────────────────────────

def render_filtros(escritos: list, key_prefix: str) -> list:
    """Muestra controles de filtro y retorna la lista ordenada/filtrada."""
    # Buscador siempre visible (fuera del expander)
    busqueda = st.text_input(
        "Buscar",
        placeholder="Número de expediente, tipo de escrito…",
        key=f"{key_prefix}_busqueda",
        label_visibility="collapsed",
    )

    with st.expander("Filtros y ordenamiento", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            orden = st.selectbox("Ordenar por", [
                "Más reciente primero",
                "Más antiguo primero",
                "Por solicitante (A-Z)",
                "Por expediente (A-Z)",
                "Días restantes (presentados)",
            ], key=f"{key_prefix}_orden")
        with c2:
            autores_disp = sorted({e["creador_nombre"] for e in escritos})
            autor_fil = st.multiselect("Solicitante", autores_disp,
                                       default=autores_disp,
                                       key=f"{key_prefix}_autor")
        with c3:
            import re
            def _get_año(exp):
                for p in re.split(r"[-/.]", (exp or "").strip()):
                    if len(p) == 4 and p.isdigit() and 1990 <= int(p) <= 2099:
                        return p
                return None
            años_disp = sorted(
                {a for e in escritos if (a := _get_año(e.get("num_expediente") or ""))},
                reverse=True
            )
            año_fil = st.multiselect("Año", años_disp,
                                     default=años_disp,
                                     key=f"{key_prefix}_año")

    # Filtrar
    q = busqueda.strip().lower()
    result = [e for e in escritos
              if e["creador_nombre"] in autor_fil
              and (_get_año(e.get("num_expediente") or "") in año_fil if año_fil else True)
              and (not q or
                   q in (e.get("num_expediente") or "").lower() or
                   q in (e.get("tipo_escrito") or "").lower() or
                   q in (e.get("nombre") or "").lower())]

    # Ordenar
    if orden == "Más reciente primero":
        result = sorted(result, key=lambda x: x["id"], reverse=True)
    elif orden == "Más antiguo primero":
        result = sorted(result, key=lambda x: x["id"])
    elif orden == "Por solicitante (A-Z)":
        result = sorted(result, key=lambda x: x["creador_nombre"])
    elif orden == "Por nombre (A-Z)":
        result = sorted(result, key=lambda x: x["nombre"].lower())
    elif orden == "Por expediente (A-Z)":
        result = sorted(result, key=lambda x: (x.get("num_expediente") or "").lower())
    elif orden == "Días restantes (presentados)":
        result = sorted(result, key=lambda x: dias_restantes(x.get("fecha_presentado_dt") or "9999-12-31"))

    return result


# ─────────────────────────────────────────────
# RENDER ESCRITO
# ─────────────────────────────────────────────

def render_escrito(e: dict, show_author: bool, show_mark: bool, show_delete: bool = False):
    fd  = to_bytes(e["file_data"])
    eid = e["id"]
    ver = e.get("version") or 1
    obs = e.get("observacion")

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            exp  = e.get("num_expediente") or e.get("nombre") or ""
            tipo = e.get("tipo_escrito") or ""
            st.markdown(f"""
                <div style="font-weight:700;font-size:13px;color:#7b87f5;">{exp}</div>
                {f'<div style="font-size:12px;color:#dde1ef;margin-top:2px;">{tipo}</div>' if tipo else ""}
                <div style="font-size:11px;color:#4a5070;margin-top:3px;">{e['nombre_archivo']}</div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(estado_badge(e["estado"], e.get("fecha_presentado_dt"), ver),
                        unsafe_allow_html=True)

        # Observación visible para el solicitante
        if obs and e["estado"] == "observado":
            st.markdown(f"""
                <div style="margin:8px 0;padding:10px 14px;
                            background:rgba(239,68,68,.07);
                            border:1px solid rgba(239,68,68,.25);
                            border-radius:7px;font-size:12px;color:#fca5a5;">
                    <strong>Observación del Revisor:</strong> {obs}
                </div>
            """, unsafe_allow_html=True)

        meta = [f"Subido: {e['fecha_creacion']}"]
        if show_author:
            meta.append(f"Por: {e['creador_nombre']}")
        if e.get("fecha_presentado"):
            meta.append(f"Presentado: {e['fecha_presentado']}")
        st.markdown(
            f"<div style='font-size:11px;color:#7a80a0;margin-bottom:8px;'>{'  ·  '.join(meta)}</div>",
            unsafe_allow_html=True)

        # ── Botones principales ──
        n_extra = sum([show_mark, show_delete])
        # show_mark implica también el botón "Observar" para el Revisor
        if show_mark:
            n_extra += 1  # botón extra "Observar"

        if n_extra >= 3:
            bcols = st.columns([1, 1, 1, 1, 1, 1])
        elif n_extra == 2:
            bcols = st.columns([1, 1, 1, 1, 2])
        elif n_extra == 1:
            bcols = st.columns([1, 1, 1, 2])
        else:
            bcols = st.columns([1, 1, 3])

        with bcols[0]:
            if st.button("Ver", key=f"ver_e_{eid}", use_container_width=True):
                k = f"prev_e_{eid}"
                st.session_state[k] = not st.session_state.get(k, False)
        with bcols[1]:
            download_link(fd, e["nombre_archivo"], e["mime_type"])

        col_idx = 2
        if show_mark:
            with bcols[col_idx]:
                if st.button("Presentado", key=f"mark_{eid}",
                             type="primary", use_container_width=True):
                    marcar_presentado(eid)
                    st.rerun()
            col_idx += 1
            with bcols[col_idx]:
                if st.button("Observar", key=f"obs_{eid}", use_container_width=True):
                    st.session_state[f"form_obs_{eid}"] = not st.session_state.get(f"form_obs_{eid}", False)
            col_idx += 1

        if show_delete:
            with bcols[col_idx]:
                if st.button("Eliminar", key=f"del_e_{eid}", use_container_width=True):
                    st.session_state[f"confirm_del_e_{eid}"] = True

        # ── Formulario de observación (Revisor) ──
        if st.session_state.get(f"form_obs_{eid}", False):
            with st.form(key=f"form_obs_submit_{eid}"):
                obs_text = st.text_area("Escribe la observación para el solicitante",
                                        placeholder="Ej: Falta la firma en la página 3...",
                                        height=90)
                s1, s2 = st.columns(2)
                with s1:
                    if st.form_submit_button("Enviar observación", use_container_width=True):
                        if obs_text.strip():
                            marcar_observado(eid, obs_text.strip())
                            st.session_state.pop(f"form_obs_{eid}", None)
                            st.rerun()
                        else:
                            st.error("Escribe una observación antes de enviar.")
                with s2:
                    if st.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state.pop(f"form_obs_{eid}", None)
                        st.rerun()

        # ── Confirmación de borrado ──
        if show_delete and st.session_state.get(f"confirm_del_e_{eid}", False):
            st.warning(f"¿Eliminar **{e['nombre']}** permanentemente? Esta acción no se puede deshacer.")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Sí, eliminar", key=f"yes_del_e_{eid}",
                             type="primary", use_container_width=True):
                    eliminar_escrito(eid)
                    st.session_state.pop(f"confirm_del_e_{eid}", None)
                    st.rerun()
            with cc2:
                if st.button("Cancelar", key=f"no_del_e_{eid}", use_container_width=True):
                    st.session_state.pop(f"confirm_del_e_{eid}", None)
                    st.rerun()

        # ── Formulario corrección (Solicitante, estado observado) ──
        if e["estado"] == "observado" and not show_mark:
            with st.form(key=f"form_corr_{eid}", clear_on_submit=True):
                st.markdown("<div style='font-size:12px;font-weight:600;color:#dde1ef;margin-bottom:6px;'>Subir versión corregida</div>",
                            unsafe_allow_html=True)
                nuevo_archivo = st.file_uploader("Archivo corregido", key=f"fu_corr_{eid}",
                                                  help="Reemplaza el archivo actual. Máximo 10 MB.")
                if st.form_submit_button("Enviar corrección", use_container_width=False):
                    if nuevo_archivo is None:
                        st.error("Selecciona el archivo corregido.")
                    elif nuevo_archivo.size > 10 * 1024 * 1024:
                        st.error("El archivo supera los 10 MB.")
                    else:
                        insertar_escrito(
                            nombre         = e["nombre"],
                            num_expediente = e.get("num_expediente") or "",
                            tipo_escrito   = e.get("tipo_escrito") or "",
                            nombre_archivo = nuevo_archivo.name,
                            mime_type      = nuevo_archivo.type or "application/octet-stream",
                            file_data      = nuevo_archivo.read(),
                            creador        = e["creador"],
                            creador_nombre = e["creador_nombre"],
                            version        = ver + 1,
                        )
                        eliminar_escrito(eid)
                        st.rerun()

        # ── Vista previa ──
        if st.session_state.get(f"prev_e_{eid}", False):
            render_preview(fd, e["mime_type"], e["nombre_archivo"])


# ─────────────────────────────────────────────
# PESTAÑA: ESCRITOS
# ─────────────────────────────────────────────

def tab_escritos():
    is_revisor    = st.session_state.rol == "Revisor"
    puede_filtrar = USERS.get(st.session_state.username, {}).get("puede_filtrar", False)

    if not is_revisor:
        # ── Subir escrito ──
        st.markdown("### Subir nuevo escrito")
        with st.form("form_escrito", clear_on_submit=True):
            c_exp, c_tipo  = st.columns(2)
            with c_exp:
                num_expediente = st.text_input("Número de expediente / causa *",
                                               placeholder="Ej: 09332-2024-00262")
            with c_tipo:
                tipo_escrito   = st.text_input("Tipo de escrito",
                                               placeholder="Ej: Solicitud de desglose, Citación…")
            uploaded = st.file_uploader("Archivo", help="PDF, imágenes, Word. Máximo 10 MB.")
            submitted = st.form_submit_button("Subir escrito")
            if submitted:
                if not num_expediente.strip():
                    st.error("El número de expediente es obligatorio.")
                elif uploaded is None:
                    st.error("Selecciona un archivo.")
                elif uploaded.size > 10 * 1024 * 1024:
                    st.error("El archivo supera los 10 MB.")
                else:
                    insertar_escrito(
                        nombre         = num_expediente.strip(),
                        num_expediente = num_expediente.strip(),
                        tipo_escrito   = tipo_escrito.strip(),
                        nombre_archivo = uploaded.name,
                        mime_type      = uploaded.type or "application/octet-stream",
                        file_data      = uploaded.read(),
                        creador        = st.session_state.username,
                        creador_nombre = st.session_state.nombre,
                    )
                    st.success(f"Escrito **{num_expediente}** registrado correctamente.")
                    st.rerun()

        escritos       = get_escritos_usuario(st.session_state.username)
        puede_eliminar = USERS.get(st.session_state.username, {}).get("puede_eliminar", False)

        if puede_filtrar and escritos:
            escritos = render_filtros(escritos, key_prefix="sol")

        pendientes  = [e for e in escritos if e["estado"] == "pendiente"]
        observados  = [e for e in escritos if e["estado"] == "observado"]
        presentados = [e for e in escritos if e["estado"] == "presentado"]

        # Alerta si hay escritos observados
        if observados:
            st.warning(f"Tienes **{len(observados)} escrito(s) con observaciones** del Revisor. Revísalos y sube la versión corregida.")

        tab_pend, tab_obs, tab_pres = st.tabs([
            f"Pendientes ({len(pendientes)})",
            f"Observados ({len(observados)})",
            f"Presentados ({len(presentados)})",
        ])
        with tab_pend:
            _ = [render_escrito(e, False, False, show_delete=puede_eliminar) for e in pendientes]
            if not pendientes: _empty_state("Sin escritos pendientes")
        with tab_obs:
            _ = [render_escrito(e, False, False, show_delete=puede_eliminar) for e in observados]
            if not observados: _empty_state("Sin escritos observados")
        with tab_pres:
            _ = [render_escrito(e, False, False, show_delete=puede_eliminar) for e in presentados]
            if not presentados: _empty_state("Sin escritos presentados")

    else:
        # ── Vista Revisor ──
        todos = get_todos_escritos()

        if puede_filtrar and todos:
            todos = render_filtros(todos, key_prefix="rev")

        pendientes  = [e for e in todos if e["estado"] == "pendiente"]
        observados  = [e for e in todos if e["estado"] == "observado"]
        presentados = [e for e in todos if e["estado"] == "presentado"]

        ca, cb, cc, cd = st.columns([3, 1, 1, 1])
        with ca:
            st.markdown("""
                <div style="font-size:14px;font-weight:600;color:#dde1ef;">Panel del Revisor</div>
                <div style="font-size:12px;color:#7a80a0;">Gestiona los escritos de todos los solicitantes.</div>
            """, unsafe_allow_html=True)
        with cb:
            st.markdown(f"""<div style="text-align:center;padding:6px 0;">
                <div style="font-size:22px;font-weight:700;color:#e8a020;">{len(pendientes)}</div>
                <div style="font-size:10px;color:#7a80a0;text-transform:uppercase;">Pendientes</div>
            </div>""", unsafe_allow_html=True)
        with cc:
            st.markdown(f"""<div style="text-align:center;padding:6px 0;">
                <div style="font-size:22px;font-weight:700;color:#ef4444;">{len(observados)}</div>
                <div style="font-size:10px;color:#7a80a0;text-transform:uppercase;">Observados</div>
            </div>""", unsafe_allow_html=True)
        with cd:
            st.markdown(f"""<div style="text-align:center;padding:6px 0;">
                <div style="font-size:22px;font-weight:700;color:#0ea271;">{len(presentados)}</div>
                <div style="font-size:10px;color:#7a80a0;text-transform:uppercase;">Presentados</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        tab_pend, tab_obs, tab_pres = st.tabs([
            f"Pendientes ({len(pendientes)})",
            f"Observados ({len(observados)})",
            f"Presentados ({len(presentados)})",
        ])
        with tab_pend:
            _ = [render_escrito(e, True, True) for e in pendientes]
            if not pendientes: _empty_state("Sin escritos pendientes")
        with tab_obs:
            _ = [render_escrito(e, True, False) for e in observados]
            if not observados: _empty_state("Sin escritos observados")
        with tab_pres:
            _ = [render_escrito(e, True, False) for e in presentados]
            if not presentados: _empty_state("Sin escritos presentados")


# ─────────────────────────────────────────────
# PESTAÑA: MODELOS
# ─────────────────────────────────────────────

def tab_modelos():
    is_revisor = st.session_state.rol == "Revisor"

    st.markdown("### Subir nuevo modelo")
    with st.form("form_modelo", clear_on_submit=True):
        nombre      = st.text_input("Nombre del modelo",
                                    placeholder="Ej: Modelo de demanda ejecutiva")
        descripcion = st.text_area("Descripción (opcional)",
                                   placeholder="Breve descripción del uso de esta plantilla",
                                   height=80)
        uploaded    = st.file_uploader("Archivo (Word, PDF, etc.)", help="Máximo 10 MB.")
        submitted   = st.form_submit_button("Subir modelo")
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
                {len(modelos)}</span>
        </div>
    """, unsafe_allow_html=True)

    if not modelos:
        _empty_state("No hay modelos cargados aún.")
        return

    for m in modelos:
        fd = to_bytes(m["file_data"])
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"""
                    <div style="font-weight:600;font-size:13px;color:#dde1ef;">{m['nombre']}</div>
                    <div style="font-size:11px;color:#4a5070;margin-top:2px;">{m['nombre_archivo']}</div>
                    {f'<div style="font-size:12px;color:#7a80a0;margin-top:4px;">{m["descripcion"]}</div>'
                      if m.get("descripcion") else ""}
                """, unsafe_allow_html=True)
            with c2:
                st.markdown("""<span style="background:rgba(90,103,242,.1);color:#7b87f5;
                    border:1px solid rgba(90,103,242,.25);border-radius:10px;
                    padding:2px 10px;font-size:11px;font-weight:600;">Plantilla</span>""",
                    unsafe_allow_html=True)

            st.markdown(
                f"<div style='font-size:11px;color:#7a80a0;margin-bottom:8px;'>"
                f"Subido por: {m['subido_por_nombre']}  ·  {m['fecha_subida']}</div>",
                unsafe_allow_html=True)

            bcols = st.columns([1, 1, 1, 2]) if is_revisor else st.columns([1, 1, 3])
            with bcols[0]:
                if st.button("Ver", key=f"ver_m_{m['id']}", use_container_width=True):
                    k = f"prev_m_{m['id']}"
                    st.session_state[k] = not st.session_state.get(k, False)
            with bcols[1]:
                download_link(fd, m["nombre_archivo"], m["mime_type"])

            if is_revisor:
                with bcols[2]:
                    if st.button("Eliminar", key=f"del_m_{m['id']}", use_container_width=True):
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
                        if st.button("Cancelar", key=f"no_del_{m['id']}", use_container_width=True):
                            st.session_state.pop(f"confirm_del_{m['id']}", None)
                            st.rerun()

            if st.session_state.get(f"prev_m_{m['id']}", False):
                render_preview(fd, m["mime_type"], m["nombre_archivo"])


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

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
                    Lex<span style="color:#7a80a0;font-weight:400;">Docs</span></span>
            </div>
        """, unsafe_allow_html=True)
        st.divider()

        rol   = st.session_state.rol
        color = "#0ea271" if rol == "Revisor" else "#7b87f5"
        bg    = "rgba(14,162,113,.12)" if rol == "Revisor" else "rgba(90,103,242,.12)"
        st.markdown(f"""
            <div style="background:{bg};border:1px solid {color}30;
                        border-radius:9px;padding:12px 14px;margin-bottom:16px;">
                <div style="font-size:13px;font-weight:600;color:#dde1ef;">{st.session_state.nombre}</div>
                <div style="display:inline-block;margin-top:5px;background:{bg};
                            border:1px solid {color}40;border-radius:4px;padding:1px 8px;
                            font-size:10px;font-weight:700;color:{color};
                            text-transform:uppercase;letter-spacing:.5px;">{rol}</div>
            </div>""", unsafe_allow_html=True)
        st.divider()

        st.markdown("""
            <div style="font-size:11px;color:#4a5070;line-height:1.8;margin-bottom:8px;">
                Banco Guayaquil - Consulegis<br>
                Desarrollado por:<br>
                <span style="color:#7a80a0;">Juan Fernando Camacho</span>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""
            <div style="font-size:10.5px;color:#4a5070;margin-top:8px;padding:8px;
                        background:#191c27;border-radius:6px;border:1px solid #272b3d;">
                Escritos presentados: eliminados tras
                <strong style="color:#7a80a0;">{DIAS_EXPIRACION} días</strong>.<br>
                Modelos: nunca se eliminan automáticamente.
            </div>""", unsafe_allow_html=True)
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

        /* ── BASE ── */
        html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
        .stApp { background: #0c0e14; }
        header[data-testid="stHeader"] { background: #13151d; border-bottom: 1px solid #272b3d; }
        [data-testid="stSidebar"] { background: #13151d !important; border-right: 1px solid #272b3d !important; }

        /* ── MAIN CONTENT: max-width + padding responsivo ── */
        .main .block-container {
            max-width: 100% !important;
            padding: 1.5rem 1.5rem 2rem !important;
        }

        /* ── TABS ── */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            background: #13151d !important;
            border-bottom: 1px solid #272b3d !important;
            gap: 4px;
            flex-wrap: wrap;
        }
        [data-testid="stTabs"] [data-baseweb="tab"] {
            background: transparent !important;
            color: #7a80a0 !important;
            border-radius: 6px 6px 0 0 !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 8px 16px !important;
            white-space: nowrap;
        }
        [data-testid="stTabs"] [aria-selected="true"] {
            background: #191c27 !important;
            color: #dde1ef !important;
            border-bottom: 2px solid #5a67f2 !important;
        }
        [data-testid="stTabPanel"] { background: transparent !important; padding-top: 16px !important; }

        /* ── INPUTS ── */
        [data-testid="stTextInput"] input {
            background: #191c27 !important; border: 1px solid #272b3d !important;
            border-radius: 7px !important; color: #dde1ef !important; font-size: 13px !important;
        }
        [data-testid="stTextInput"] input:focus { border-color: #5a67f2 !important; }
        [data-testid="stTextArea"] textarea {
            background: #191c27 !important; border: 1px solid #272b3d !important;
            border-radius: 7px !important; color: #dde1ef !important; font-size: 13px !important;
        }
        [data-testid="stFileUploader"] {
            background: #191c27 !important; border: 1px dashed #313654 !important;
            border-radius: 8px !important;
        }

        /* ── BUTTONS ── */
        .stButton > button {
            background: #191c27 !important; border: 1px solid #272b3d !important;
            color: #7a80a0 !important; border-radius: 6px !important;
            font-size: 12px !important; font-weight: 500 !important;
            transition: all .18s !important;
            width: 100% !important;
            white-space: nowrap !important;
            padding: 6px 10px !important;
        }
        .stButton > button:hover {
            border-color: #3d4266 !important; color: #dde1ef !important;
            background: #1f2230 !important;
        }
        .stButton > button[kind="primary"] {
            background: rgba(14,162,113,.08) !important;
            border: 1px solid rgba(14,162,113,.25) !important;
            color: #0ea271 !important; font-weight: 600 !important;
        }
        .stButton > button[kind="primary"]:hover { background: rgba(14,162,113,.15) !important; }
        .stFormSubmitButton > button {
            background: #5a67f2 !important; color: white !important;
            border: none !important; font-weight: 600 !important;
            font-size: 13px !important; border-radius: 7px !important;
        }
        .stFormSubmitButton > button:hover { background: #7b87f5 !important; }

        /* ── CONTAINERS / CARDS ── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: #13151d !important; border: 1px solid #272b3d !important;
            border-radius: 10px !important;
        }
        [data-testid="stForm"] {
            background: #13151d !important; border: 1px solid #272b3d !important;
            border-radius: 10px !important; padding: 16px !important;
        }
        [data-testid="stExpander"] {
            background: #13151d !important; border: 1px solid #272b3d !important;
            border-radius: 8px !important;
        }

        /* ── TYPOGRAPHY ── */
        p, label, div { color: #dde1ef; }
        h1, h2, h3 { color: #dde1ef !important; font-weight: 600 !important; }
        hr { border-color: #272b3d !important; }
        [data-testid="stAlert"] { border-radius: 8px !important; font-size: 13px !important; }
        #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

        /* ── COLUMNAS: colapsar en pantallas angostas ── */
        /* < 900px: columnas de secciones se apilan */
        @media (max-width: 900px) {
            /* Todas las columnas de nivel superior se vuelven full-width */
            [data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
                gap: 0 !important;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                width: 100% !important;
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }
            /* Padding del main más ajustado */
            .main .block-container {
                padding: 1rem 0.75rem 2rem !important;
            }
            /* Sidebar oculto por defecto en móvil (Streamlit lo maneja) */
            [data-testid="stSidebar"] {
                min-width: 0 !important;
            }
            /* Tabs más compactos */
            [data-testid="stTabs"] [data-baseweb="tab"] {
                padding: 7px 12px !important;
                font-size: 12px !important;
            }
        }

        /* < 640px: ajustes adicionales para teléfonos */
        @media (max-width: 640px) {
            .main .block-container {
                padding: 0.75rem 0.5rem 2rem !important;
            }
            /* Títulos más pequeños */
            h2 { font-size: 1.2rem !important; }
            h3 { font-size: 1rem !important; }
            /* Botones de acción en cada escrito: apilar */
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] .stButton > button {
                font-size: 11px !important;
                padding: 5px 8px !important;
            }
            /* Badges más pequeños */
            span[style*="border-radius:10px"] {
                font-size: 10px !important;
                padding: 2px 7px !important;
            }
        }

        /* ── SCROLL horizontal para tablas/badges en mobile ── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            overflow-x: hidden !important;
        }

        /* ── Selectbox / multiselect ── */
        [data-testid="stSelectbox"] > div,
        [data-testid="stMultiSelect"] > div {
            background: #191c27 !important;
            border-color: #272b3d !important;
            border-radius: 7px !important;
            color: #dde1ef !important;
        }
        [data-baseweb="select"] { background: #191c27 !important; }
        [data-baseweb="menu"] { background: #1e2130 !important; border: 1px solid #272b3d !important; }
        [data-baseweb="option"] { background: #1e2130 !important; color: #dde1ef !important; }
        [data-baseweb="option"]:hover { background: #252838 !important; }

        /* ── Touch targets más grandes en móvil ── */
        @media (max-width: 900px) {
            .stButton > button {
                min-height: 40px !important;
                font-size: 13px !important;
            }
            [data-testid="stTextInput"] input,
            [data-testid="stTextArea"] textarea {
                font-size: 16px !important; /* evita zoom en iOS */
                min-height: 44px !important;
            }
        }
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
        initial_sidebar_state = "auto",
    )
    inject_css()
    init_db()
    purgar_escritos_expirados()

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
