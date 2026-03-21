import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN DE ENTORNO ---
ENV = "PROD" 

def save_to_adls(df, folder_name, user_email):
    """
    Función para guardar archivos directamente en el ADLS Bronze.
    Cero tablas, cero Unity Catalog. Solo archivos crudos.
    """
    from databricks.connect import DatabricksSession
    spark = DatabricksSession.builder.getOrCreate()
    
    # Agregar metadatos de auditoría
    df['ingested_by'] = user_email
    df['ingestion_timestamp'] = datetime.now()
    
    # Convertir Pandas a Spark DataFrame
    sdf = spark.createDataFrame(df)
    
    # --- LÓGICA DE ALMACENAMIENTO FÍSICO (Directo a Bronze) ---
    # Usamos la External Location para ir directo al contenedor
    # Guardará los archivos dentro de la carpeta que el usuario escriba
    adls_path = f"abfss://bronze@adlslhcl.dfs.core.windows.net/dataentry_usr/{folder_name}/"
    
    # Escribimos físicamente en el storage en formato CSV
    # .save() tira el archivo al disco sin registrar NADA en el catálogo
    sdf.write \
       .format("csv") \
       .option("header", "true") \
       .mode("append") \
       .save(adls_path)

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
    st.sidebar.header("⚙️ Opciones de Ingesta")
    
    columnas_detectadas = list(df.columns)
    st.sidebar.success(f"✅ Esquema detectado: {len(columnas_detectadas)} columnas")
    with st.sidebar.expander("Ver columnas detectadas"):
        st.write(columnas_detectadas)
    
    # Input para que el usuario nombre la carpeta destino
    folder_name = st.sidebar.text_input(
        "📁 Nombre de la carpeta destino:", 
        value="nueva_ingesta"
    ).strip().replace(" ", "_").lower()
    
    st.sidebar.divider()
    
    # Botón de Ingesta
    if st.sidebar.button("🚀 Confirmar e Ingestar"):
        if folder_name == "":
            st.sidebar.error("Por favor, ingresa un nombre válido para la carpeta.")
        else:
            with st.spinner(f"Escribiendo directamente en ADLS (bronze/.../{folder_name})..."):
                try:
                    save_to_adls(df, folder_name, user_email)
                    st.success(f"¡Éxito! Archivo guardado físicamente en la carpeta: `{folder_name}`")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error interno al guardar los datos: {e}")
