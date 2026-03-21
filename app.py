import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN DE ENTORNO Y DOMINIOS ---
ENV = "DESA" 

# DICCIONARIO DE DOMINIOS PERMITIDOS
# Aquí defines la estructura de carpetas válidas de tu ADLS
ESTRUCTURA_DOMINIOS = {
    "usr": ["cobr", "dyan", "pric"],
    "int": ["finanzas", "rrhh", "operaciones"], # Reemplaza con tus dominios reales
    "ext": ["proveedores", "clientes", "marketing"] # Reemplaza con tus dominios reales
}

def save_to_adls(df, tipo_origen, dominio, user_email):
    from databricks.sdk import WorkspaceClient
    import io

    # En Databricks Apps, la autenticación es automática
    w = WorkspaceClient()

    # Agregar metadatos
    df['ingested_by'] = user_email
    df['ingestion_timestamp'] = datetime.now().isoformat()

    # Convertir DataFrame a CSV en memoria
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode('utf-8')

    # Generar nombre único para el archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dataentry_{timestamp}.csv"

    # Escribir al Volume de Unity Catalog (que mapea a tu ADLS)
    volume_path = f"/Volumes/tu_catalogo/tu_schema/bronze/peps/dataentry/{tipo_origen}/{dominio}/{filename}"

    w.files.upload(volume_path, io.BytesIO(csv_bytes), overwrite=True)
    
# --- 2. INTERFAZ DE USUARIO (Streamlit) ---
st.set_page_config(page_title="Data Entry Portal", layout="wide")

# Obtener identidad desde Headers de Databricks
user_email = st.context.headers.get("X-Forwarded-Email", "desarrollador_local@empresa.com")

st.title("📥 Portal de Ingesta Dinámica (Directo a Bronze)")
st.markdown(f"**Usuario:** `{user_email}` | **Entorno:** `{ENV}`")
st.divider()

# Sección de Carga
uploaded_file = st.file_uploader("Arrastra tu archivo CSV aquí", type="csv")

if uploaded_file:
    # Leer el archivo cargado
    df = pd.read_csv(uploaded_file)
    
    st.subheader("👀 Previsualización de datos")
    st.dataframe(df.head(10), use_container_width=True)
    
    # --- 3. VALIDACIÓN Y CONFIGURACIÓN DINÁMICA ---
    st.sidebar.header("⚙️ Ruta de Destino")
    
    # Selector de Tipo de Origen (Las "carpetas padre")
    tipos_origen_disponibles = list(ESTRUCTURA_DOMINIOS.keys())
    tipo_origen_seleccionado = st.sidebar.selectbox(
        "📂 1. Selecciona el Tipo de Origen:", 
        options=tipos_origen_disponibles
    )
    
    # Selector de Dominio (Las "carpetas hijo", cambia según el Origen seleccionado)
    dominios_disponibles = ESTRUCTURA_DOMINIOS[tipo_origen_seleccionado]
    dominio_seleccionado = st.sidebar.selectbox(
        "📁 2. Selecciona el Dominio:", 
        options=dominios_disponibles
    )
    
    # Mostrar la ruta final generada para que el usuario verifique
    ruta_visual = f"/peps/dataentry/{tipo_origen_seleccionado}/{dominio_seleccionado}/"
    st.sidebar.info(f"📍 Destino Final:\n`{ruta_visual}`")
    
    st.sidebar.divider()
    
    # Botón de Ingesta
    if st.sidebar.button("🚀 Confirmar e Ingestar"):
        with st.spinner(f"Escribiendo en ADLS ({ruta_visual})..."):
            try:
                save_to_adls(df, tipo_origen_seleccionado, dominio_seleccionado, user_email)
                st.success(f"¡Éxito! Archivo guardado físicamente en la ruta: `{ruta_visual}`")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Error interno al guardar los datos: {e}")
