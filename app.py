import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN DE ENTORNO ---
# Cambia a "PROD" cuando tengas el External Location de ADLS listo
ENV = "DEV_FREE" 

def save_to_databricks(df, table_name, user_email):
    """
    Función modular para persistir datos usando Databricks Connect.
    No requiere Java local.
    """
    # Usamos EXCLUSIVAMENTE la conexión serverless de Databricks
    from databricks.connect import DatabricksSession
    spark = DatabricksSession.builder.getOrCreate()
    
    # Agregar metadatos de auditoría
    df['ingested_by'] = user_email
    df['ingestion_timestamp'] = datetime.now()
    
    # Convertir Pandas a Spark DataFrame y mandar al cluster
    sdf = spark.createDataFrame(df)
    
    if ENV == "DEV_FREE":
        sdf.write.mode("append").saveAsTable(f"default.{table_name}")
    else:
        # Lógica para ADLS Gen2 (Futuro)
        pass
# --- 2. INTERFAZ DE USUARIO (Streamlit) ---
st.set_page_config(page_title="Data Entry Portal", layout="wide")

# Obtener identidad desde Headers de Databricks
# En local/codespaces usará el valor por defecto
user_email = st.context.headers.get("X-Forwarded-Email", "desarrollador_local@empresa.com")

st.title("📥 Portal de Ingesta Dinámica")
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
    st.sidebar.header("⚙️ Opciones de Ingesta")
    
    # Mostrar el esquema detectado dinámicamente
    columnas_detectadas = list(df.columns)
    st.sidebar.success(f"✅ Esquema detectado: {len(columnas_detectadas)} columnas")
    with st.sidebar.expander("Ver columnas detectadas"):
        st.write(columnas_detectadas)
    
    # Input para que el usuario nombre su tabla destino
    # Limpiamos espacios y pasamos a minúsculas por buenas prácticas de BD
    table_name = st.sidebar.text_input(
        "📝 Nombre de la tabla destino:", 
        value="nueva_ingesta"
    ).strip().replace(" ", "_").lower()
    
    st.sidebar.divider()
    
    # Botón de Ingesta
    if st.sidebar.button("🚀 Confirmar e Ingestar"):
        if table_name == "":
            st.sidebar.error("Por favor, ingresa un nombre válido para la tabla.")
        else:
            with st.spinner(f"Escribiendo en Databricks (default.{table_name})..."):
                try:
                    # Ejecutar la función de guardado
                    save_to_databricks(df, table_name, user_email)
                    st.success(f"¡Éxito! Datos guardados en la tabla: `default.{table_name}`")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error interno al guardar los datos: {e}")
