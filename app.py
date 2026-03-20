import streamlit as st
import pandas as pd
from datetime import datetime
from pyspark.sql import SparkSession

# --- 1. CONFIGURACIÓN DE ENTORNO ---
# Cambia a "PROD" cuando tengas el External Location de ADLS listo
ENV = "DEV_FREE" 

def save_to_databricks(df, table_name, user_email):
    """
    Función modular para persistir datos. 
    Fácil de switchear entre Metastore local y ADLS Gen2.
    """
    try:
        # Intentamos obtener la sesión activa de Spark (Para Databricks Serverless)
        from databricks.connect import DatabricksSession
        spark = DatabricksSession.builder.getOrCreate()
    except ImportError:
        # Fallback para entornos que ya tienen spark definido (Local/Free Edition)
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
    
    # Agregar metadatos de auditoría (DAC)
    df['ingested_by'] = user_email
    df['ingestion_timestamp'] = datetime.now()
    
    # Convertir Pandas a Spark DataFrame
    sdf = spark.createDataFrame(df)
    
    if ENV == "DEV_FREE":
        # Escritura en el Metastore de Databricks Community
        # Se guarda en el schema 'default' por defecto
        sdf.write.mode("append").saveAsTable(f"default.{table_name}")
    else:
        # Lógica para ADLS Gen2 (Futuro)
        # path = f"abfss://<container>@<storage>.dfs.core.windows.net/raw/{table_name}"
        # sdf.write.mode("append").format("delta").save(path)
        pass

# --- 2. INTERFAZ DE USUARIO (Streamlit) ---
st.set_page_config(page_title="Data Entry Portal", layout="wide")

# Obtener identidad desde Headers de Databricks
# En local/codespaces usará el valor por defecto
user_email = st.context.headers.get("X-Forwarded-Email", "desarrollador_local@empresa.com")

st.title("📥 Portal de Ingesta Manual")
st.markdown(f"**Usuario:** `{user_email}` | **Entorno:** `{ENV}`")
st.divider()

# Sección de Carga
uploaded_file = st.file_uploader("Arrastra tu archivo CSV aquí", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    st.subheader("👀 Previsualización de datos")
    st.dataframe(df.head(10), use_container_width=True)
    
    # --- 3. VALIDACIÓN TÉCNICA ---
    st.sidebar.header("Validaciones de Ingeniería")
    
    # Definir esquema esperado
    expected_columns = ["fecha", "cliente_id", "monto", "producto"]
    actual_columns = list(df.columns)
    
    is_schema_valid = all(col in actual_columns for col in expected_columns)
    
    if is_schema_valid:
        st.sidebar.success("✅ Esquema coincidente")
        
        try:
            # Validar que la columna fecha sea válida
            df['fecha'] = pd.to_datetime(df['fecha'])
            st.sidebar.success("✅ Formato de fecha correcto")
            
            # Botón de Ingesta
            if st.button("🚀 Confirmar e Ingestar en Databricks"):
                with st.spinner("Escribiendo en el Metastore..."):
                    save_to_databricks(df, "ingesta_manual_pacificosalud", user_email)
                    st.success("¡Éxito! Datos guardados en la tabla: `default.ingesta_manual_pacificosalud`")
                    st.balloons()
                    
        except Exception as e:
            # Aquí estaba el error de sintaxis original
            st.sidebar.error(f"❌ Error en fechas: {e}")
            st.error("Revisa el formato de la columna 'fecha' (ej. YYYY-MM-DD)")
    else:
        # Faltaba cerrar esta condición en tu copia
        st.sidebar.error("❌ Esquema inválido")
        st.error(f"Faltan columnas obligatorias. Se espera: {expected_columns}")
