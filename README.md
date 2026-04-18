# LexDocs — Gestor de Escritos Legales
**Banco Guayaquil - Consulegis**
Desarrollado por: Juan Fernando Camacho

---

## Usuarios

| Usuario           | Contraseña | Rol         |
|-------------------|------------|-------------|
| rafaela_b         | 123        | Solicitante |
| juan_fernando_c   | 456        | Solicitante |
| juan_pablo_w      | 789        | Revisor     |

---

## Ejecutar localmente

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar
streamlit run app.py
```

La app abre en http://localhost:8501

---

## Desplegar en Streamlit Community Cloud (URL pública gratuita)

### Paso 1 — Subir el proyecto a GitHub

Sube los siguientes archivos a un repositorio de GitHub (puede ser el mismo `Gestor-de-escritos`):

```
app.py
requirements.txt
.streamlit/config.toml
```

### Paso 2 — Crear cuenta en Streamlit Cloud

Ve a https://share.streamlit.io e inicia sesión con tu cuenta de GitHub.

### Paso 3 — Desplegar

1. Haz clic en **New app**
2. Selecciona el repositorio y la rama (`main`)
3. En **Main file path** escribe: `app.py`
4. Haz clic en **Deploy**

En 2-3 minutos tendrás una URL pública del tipo:
`https://tu-usuario-gestor-de-escritos.streamlit.app`

### Paso 4 — Base de datos persistente en la nube

> SQLite funciona en Streamlit Cloud pero **se resetea cada vez que la app se reinicia**.
> Para producción real, reemplaza SQLite con una base de datos externa gratuita:

**Opción recomendada: Supabase (PostgreSQL gratuito)**

1. Crea una cuenta en https://supabase.com
2. Crea un proyecto y copia la `DATABASE_URL`
3. En Streamlit Cloud, ve a **Settings → Secrets** y agrega:
   ```toml
   DATABASE_URL = "postgresql://user:password@host:5432/dbname"
   ```
4. Instala el driver: agrega `psycopg2-binary` a `requirements.txt`
5. Reemplaza `sqlite3.connect(DB_PATH)` por `psycopg2.connect(os.environ["DATABASE_URL"])`

---

## Estructura del proyecto

```
lexdocs-streamlit/
├── app.py                  # Aplicación principal
├── requirements.txt        # Dependencias
├── .streamlit/
│   └── config.toml         # Tema y configuración
└── lexdocs.db              # Base de datos SQLite (se crea automáticamente)
```
