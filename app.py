import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURACIÓN ---
ENV = "DESA"

ESTRUCTURA_DOMINIOS = {
    "usr": ["cobr", "dyan", "pric"],
    "int": ["finanzas", "rrhh", "operaciones"],
    "ext": ["proveedores", "clientes", "marketing"]
}

def save_to_adls(df, tipo_origen, dominio, user_email, filename):
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()

    # Agregar metadatos de auditoría
    df['ingested_by'] = user_email
    df['ingestion_timestamp'] = datetime.now().isoformat()

    # Convertir a CSV en memoria
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode('utf-8')

    # Subir con el nombre exacto del usuario al Volume (que apunta a tu ADLS)
    volume_path = f"/Volumes/tu_catalogo/tu_schema/bronze_volume/{tipo_origen}/{dominio}/{filename}"

    w.files.upload(volume_path, io.BytesIO(csv_bytes), overwrite=True)


# --- 2. INTERFAZ DE USUARIO ---
st.set_page_config(page_title="Data Entry Portal", layout="wide")

user_email = st.context.headers.get("X-Forwarded-Email", "desarrollador_local@empresa.com")
st.title("📥 Portal de Ingesta Dinámica (Directo a Bronze)")
st.markdown(f"**Usuario:** `{user_email}` | **Entorno:** `{ENV}`")
st.divider()

uploaded_file = st.file_uploader("Arrastra tu archivo CSV aquí", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    st.subheader("👀 Previsualización de datos")
    st.dataframe(df.head(10), use_container_width=True)

    st.sidebar.header("⚙️ Ruta de Destino")

    tipos_origen_disponibles = list(ESTRUCTURA_DOMINIOS.keys())
    tipo_origen_seleccionado = st.sidebar.selectbox(
        "📂 1. Selecciona el Tipo de Origen:",
        options=tipos_origen_disponibles
    )

    dominios_disponibles = ESTRUCTURA_DOMINIOS[tipo_origen_seleccionado]
    dominio_seleccionado = st.sidebar.selectbox(
        "📁 2. Selecciona el Dominio:",
        options=dominios_disponibles
    )

    ruta_visual = f"/peps/dataentry/{tipo_origen_seleccionado}/{dominio_seleccionado}/"
    st.sidebar.info(f"📍 Destino Final:\n`{ruta_visual}{uploaded_file.name}`")

    st.sidebar.divider()

    if st.sidebar.button("🚀 Confirmar e Ingestar"):
        with st.spinner(f"Escribiendo {uploaded_file.name} en ADLS ({ruta_visual})..."):
            try:
                save_to_adls(df, tipo_origen_seleccionado, dominio_seleccionado, user_email, uploaded_file.name)
                st.success(f"¡Éxito! Archivo `{uploaded_file.name}` guardado en: `{ruta_visual}`")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Error interno al guardar los datos: {e}")
