import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN DE ENTORNO Y DOMINIOS ---
ENV = "DESA"

ESTRUCTURA_DOMINIOS = {
    "usr": ["cobr", "dyan", "pric"],
    "int": ["finanzas", "rrhh", "operaciones"],
    "ext": ["proveedores", "clientes", "marketing"]
}

def save_to_adls(df, tipo_origen, dominio, user_email, filename):
    from databricks.connect import DatabricksSession

    spark = DatabricksSession.builder.serverless().getOrCreate()

    # Agregar metadatos de auditoría
    df['ingested_by'] = user_email
    df['ingestion_timestamp'] = datetime.now().isoformat()

    sdf = spark.createDataFrame(df)

    # Paso 1: Escribir como un solo archivo en carpeta temporal
    base_path = f"abfss://bronze@adlslhcl.dfs.core.windows.net/peps/dataentry/{tipo_origen}/{dominio}"
    temp_path = f"{base_path}/_temp_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    sdf.coalesce(1) \
       .write \
       .format("csv") \
       .option("header", "true") \
       .mode("overwrite") \
       .save(temp_path)

    # Paso 2: Renombrar el part-00000 al nombre original del usuario
    hadoop = spark._jsc.hadoopConfiguration()
    uri = spark._jvm.java.net.URI(base_path)
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(uri, hadoop)

    # Buscar el archivo part-00000 en la carpeta temporal
    temp_hadoop_path = spark._jvm.org.apache.hadoop.fs.Path(temp_path)
    files = fs.listStatus(temp_hadoop_path)

    for f in files:
        name = f.getPath().getName()
        if name.startswith("part-"):
            old_path = f.getPath()
            new_path = spark._jvm.org.apache.hadoop.fs.Path(f"{base_path}/{filename}")
            fs.rename(old_path, new_path)

    # Paso 3: Eliminar la carpeta temporal
    fs.delete(temp_hadoop_path, True)


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
