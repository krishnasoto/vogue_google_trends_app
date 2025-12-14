# =========================================================
# VOGUE vs GOOGLE TRENDS - STREAMLIT APP
# =========================================================

# =========================
# IMPORTACIONES
# =========================
import ast
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pytrends.request import TrendReq

# =========================
# CONFIGURACIÓN GLOBAL
# =========================
st.set_page_config(layout="wide", page_title="Vogue vs Google Trends")

BASE_DIR = Path(__file__).parent
CSV_FILE = BASE_DIR / "data/vogue_celebrities_data.csv"
SENTIMENT_FILE = BASE_DIR / "data/vogue_celebrities_sentiment.json"

MOCK_TRENDS = False  # True para demo/desarrollo
MIN_TRENDS_DAYS = 7  # mínimo de días para solicitar Google Trends

# =========================
# DISEÑO Y PALETA DE COLORES
# =========================

# --- Paleta Principal (VOGUE-Inspired) ---
PALETTE = {
    "black": "#0E0E0E",
    "dark_gray": "#4A4A4A",
    "light_gray": "#E6E6E6",
    "cream": "#F5EFE6",
    "rose": "#C78885", # Color principal para gráficos
}

# --- Colores de Sentimiento ---
SENTIMENT_COLORS = {
    "positive": "#97C3E3", # Verde suave
    "neutral": "#F2E1C4", # Beige/Crema
    "negative": "#C78885", # Rojo ladrillo
    "unknown": "##4A4A4A", 
}

# =========================
# FUNCIONES DE UTILIDAD
# =========================
# =========================
# UTILIDADES
# =========================
BANNED_ARTISTS = {"estilo de vida"}

TAG_RULES = {
    "MET GALA": "Met Gala",
    "METGALA": "Met Gala",
    "PAREJA": "Parejas",
    "PAREJAS": "Parejas",
}

def clean_artist_name(name: str) -> str:
    cleaned = name.strip().strip("'").strip('"').strip()
    return cleaned.title() if cleaned else ""

def parse_artists(value) -> list:
    if pd.isna(value):
        return []
    if isinstance(value, list):
        return [clean_artist_name(a) for a in value if clean_artist_name(a).lower() not in BANNED_ARTISTS and clean_artist_name(a)]
    if isinstance(value, str):
        clean_str = value.replace('[','').replace(']','').strip()
        try:
            parsed = ast.literal_eval(clean_str)
            if isinstance(parsed, list):
                return parse_artists(parsed)
        except:
            pass
        return [clean_artist_name(a) for a in clean_str.split(",") if clean_artist_name(a).lower() not in BANNED_ARTISTS and clean_artist_name(a)]
    return []

def clean_tags(tag) -> str:
    tag = str(tag).upper().strip()
    for key, value in TAG_RULES.items():
        if key in tag:
            return value
    return tag.capitalize()

def sentiment_to_color(sentiment) -> str:
    return SENTIMENT_COLORS.get(sentiment, SENTIMENT_COLORS["unknown"])

def unique_artists(series: pd.Series) -> int:
    return len({a for sub in series for a in sub})

def total_mentions(series: pd.Series) -> int:
    return sum(len(sub) for sub in series)

def apply_editorial_layout(fig: go.Figure, title=None) -> go.Figure:
    fig.update_layout(
        font=dict(family="Didot, serif", color=PALETTE["dark_gray"]),
        margin=dict(t=60, l=40, r=40, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
        hoverlabel=dict(font=dict(family="Arial, sans-serif"))
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig

# =========================
# CARGA DE DATOS
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_FILE)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["artistas_en_articulo"] = df["artistas_en_articulo"].apply(parse_artists)
    df["tag"] = df["tag"].apply(clean_tags)
    
    with open(SENTIMENT_FILE, encoding="utf-8") as f:
        sentiment = pd.DataFrame(json.load(f)).rename(columns={"score":"confidence"})
    
    df = df.reset_index(drop=True)
    sentiment = sentiment.reset_index(drop=True)
    df = pd.concat([df, sentiment[["sentiment","confidence"]]], axis=1)
    df["sentiment"].fillna("unknown", inplace=True)
    df["confidence"].fillna(0.0, inplace=True)
    return df

# =========================
# GOOGLE TRENDS
# =========================
@st.cache_data(ttl=3600)
def get_trends(keywords: list, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if not keywords or (end - start).days < MIN_TRENDS_DAYS:
        return pd.DataFrame()
    if MOCK_TRENDS:
        dates = pd.date_range(start, end, freq="D")
        return pd.DataFrame({kw: np.random.randint(20,100,len(dates)) for kw in keywords}, index=dates)
    try:
        pytrends = TrendReq(hl="es-ES", tz=360)
        timeframe = f"{start:%Y-%m-%d} {end:%Y-%m-%d}"
        pytrends.build_payload(keywords[:5], timeframe=timeframe, geo="ES")
        return pytrends.interest_over_time().drop(columns="isPartial", errors="ignore")
    except Exception as e:
        st.error(f"Error Google Trends: {e}")
        return pd.DataFrame()

# =========================
# INICIO DE APP
# =========================
df = load_data()
df = df[df["fecha"] >= "2025-01-01"].dropna(subset=["fecha"])

if df.empty:
    st.warning("No hay datos disponibles.")
    st.stop()

# =========================
# SESIÓN
# =========================
if "section" not in st.session_state:
    st.session_state.section = "General"

# =========================
# CABECERA Y PORTADA (VOGUE STYLE)
# =========================

# --- Estilos CSS Personalizados (Inyección de HTML/CSS) ---
st.markdown("""
<style>
.vogue-logo {
    font-family: 'Didot', 'Times New Roman', serif;
    font-size: 70px;
    font-weight: 500;
    text-align: center;
    line-height: 0.8;
    margin-bottom: 5px;
}
.vogue-country {
    font-size: 30px;
    font-weight: 400;
    text-align: center;
    letter-spacing: 5px; 
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# 1. Imitación del Logo VOGUE SPAIN
st.markdown("<div class='vogue-logo'>VOGUE</div>", unsafe_allow_html=True)
st.markdown("<div class='vogue-country'>SPAIN</div>", unsafe_allow_html=True)

# 2. Separador
st.markdown("<hr style='border: 1px solid #000; margin: 30px 0;'>", unsafe_allow_html=True)


# --- Título y Contexto ---
col_gif, col_text = st.columns([3, 4])

with col_gif:
    # Imagen/GIF de portada
    st.image("https://media.vogue.es/photos/6152f4886d4025329835a96e/master/w_1600,c_limit/COVER%20HORIZONTAL.gif")

with col_text:
    # Título principal
    st.markdown("<h1 style='text-align: center; font-size: 50px; letter-spacing: 5px; color: #555555; margin-top: 0px;'>El Eco de Vogue en las Búsquedas Públicas</h2>", unsafe_allow_html=True)

    # Texto de introducción/contexto
    st.markdown(
            """
            <div style='text-align: center; font-family: serif; font-size: 20px; letter-spacing: 2px; line-height: 1.5;'>
                Midiendo el Impacto Editorial de Vogue frente a Google Trends de las Celebridades.
            </div>
            """, 
            unsafe_allow_html=True
        )

# Separador de cierre de cabecera
st.markdown("<hr style='border: 1px solid #ccc; margin: 30px 0;'>", unsafe_allow_html=True)

# =========================
# FILTRO DE FECHAS
# =========================
start_date, end_date = st.slider(
    "Rango de fechas",
    df["fecha"].min().date(),
    df["fecha"].max().date(),
    (df["fecha"].min().date(), df["fecha"].max().date())
)
df_filtered = df[(df["fecha"].dt.date >= start_date) & (df["fecha"].dt.date <= end_date)]

# =========================
# NAVEGACIÓN (BOTONES)
# =========================
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Análisis General", type="primary" if st.session_state.section == "General" else "secondary", width='stretch'):
        st.session_state.section = "General"
with col2:
    if st.button("Análisis por Celebridad", type="primary" if st.session_state.section == "Por Artista" else "secondary",width='stretch'):
        st.session_state.section = "Por Artista"

st.markdown("---") # Separador para el contenido principal

# =========================
# BARRA LATERAL (ÍNDICE)
# =========================
st.sidebar.markdown("## 🧭 Índice")

if st.session_state.section == "General":
    for item in [
        "1. Categorías Vogue",
        "2. Distribución por Artículos",
        "3. Celebridades",
        "4. Google Trends",
        "5. Sentimiento por Celebridad",
    ]:
        st.sidebar.markdown(f"— {item}")
else:
    for item in [
        "1. Tendencia y Apariciones",
        "2. Distribución de Sentimiento",
        "3. Influencia Editorial",
        "4. Artículos y Sentimiento",
    ]:
        st.sidebar.markdown(f"— {item}")


# =========================
# SECCIÓN: ANÁLISIS GENERAL
# =========================
if st.session_state.section == "General":
    st.header("Análisis General de la Cobertura Editorial")

    # 1. Gráfico de Barras de Categorías
    st.subheader("1. Categorías Vogue")
    st.markdown("Comparativa de categorías (tags) basada en el número de celebridades únicas que aparecen en sus artículos.")
    
    # Agrupar por 'tag' y contar artistas únicos
    category_artist_counts = (
        df_filtered.groupby("tag")["artistas_en_articulo"]
        .apply(unique_artists)
        .reset_index(name="Celebridades")
        .sort_values("Celebridades", ascending=True)
    )

    fig = px.bar(
            category_artist_counts,
            x="Celebridades",
            y="tag",
            orientation="h",
            title="Categorías de Vogue según el Volumen de Celebridades Mencionadas",
            labels={"tag": "", "Celebridades": "No. de Celebridades Únicas"},
            hover_data={'Celebridades': True, 'tag': False},
            color_discrete_sequence=[PALETTE["rose"]] # Color principal
        )
    st.plotly_chart(apply_editorial_layout(fig), width='stretch') # Ajustar al ancho de la columna

    # 2. Gráfico de Dispersión (Scatter) de Distribución por Artículos
    st.subheader("2. Distribución por Artículos")
    st.markdown("Relación entre el número de artículos, las celebridades únicas y el total de menciones por categoría.")
    
    grouped = df_filtered.groupby("tag")
    scatter_df = pd.DataFrame({
        "Artículos": grouped.size(),
        "Celebridades": grouped["artistas_en_articulo"].apply(unique_artists),
        "Menciones": grouped["artistas_en_articulo"].apply(total_mentions), # Usado para el tamaño de la burbuja
    }).reset_index()

    fig_scatter = px.scatter(
            scatter_df,
            x="Celebridades",
            y="Artículos",
            size="Menciones", # Tamaño de la burbuja por menciones totales
            color="tag",
            color_discrete_sequence=px.colors.qualitative.Dark24, # Paleta de colores variada
            title="Categorías de Vogue: Artículos vs Celebridades Mencionadas",
            labels={"tag": "Categoría", "Celebridades": "No. de Celebridades Únicas",  "Menciones": "No. de Menciones Totales", "Artículos": "No. de Artículos"},
            hover_data={"tag": True, "Celebridades": True, "Menciones": True, "Artículos": True},
        )
    st.plotly_chart(apply_editorial_layout(fig_scatter), width='stretch') # Ajustar al ancho de la columna

    # 3. Treemap de Celebridades
    st.subheader("3. Celebridades Top")
    st.markdown("Mapa jerárquico que muestra las 50 celebridades más mencionadas en los artículos.")
    
    # Contar todas las menciones de artistas
    all_artists = [a for sub in df_filtered["artistas_en_articulo"] for a in sub]
    treemap_df = (
        pd.DataFrame(Counter(all_artists).items(), columns=["Artista", "Count"])
        .sort_values("Count", ascending=False)
        .head(50) # Top 50
    )

    fig_treemap = px.treemap(
        treemap_df,
        path=[px.Constant("Celebridades"), "Artista"], # Jerarquía: Raíz -> Artista
        values="Count",
        color="Count",
        color_continuous_scale=[PALETTE["cream"], PALETTE["rose"]], # Gradiente de color
        hover_data=[], # Simplificar el hover para solo mostrar label y value
        title="Top 50 Celebridades Mencionadas en Vogue"
    )

    # Personalizar el texto de hover
    custom_hovertemplate = (
        "<b>%{label}</b><br>" 
        "No. Artículos en los que aparece: <b>%{value}</b><br>" 
        "<extra></extra>" # Eliminar información extra de Plotly
    )
    
    fig_treemap.update_traces(hovertemplate=custom_hovertemplate)
    fig_treemap.update_layout(margin=dict(t=50, l=0, r=0, b=0)) # Ajustar márgenes para el treemap
    st.plotly_chart(apply_editorial_layout(fig_treemap), width='stretch') # Ajustar al ancho de la columna

    # 4. Google Trends Global
    st.subheader("4. Google Trends (Top 5)")
    st.markdown("**Comparativa de las búsquedas en Google de las Top 5 Celebridades más mencionadas en Vogue**")
    
    # Obtener el Top 5 de artistas
    top_artists = [a for a, _ in Counter(all_artists).most_common(5)]
    trends = get_trends(top_artists, start_date, end_date)

    if not trends.empty:
        fig_trends = px.line(trends, title=f"Google Trends: Búsquedas de {', '.join(top_artists)}", 
                             labels={"value": "Interés a lo largo del tiempo", "variable": "Celebridad"})
        st.plotly_chart(apply_editorial_layout(fig_trends), width='stretch') # Ajustar al ancho de la columna
    else:
        st.info("No se pudieron cargar los datos de Google Trends. Verifique la conexión o el rango de fechas.")

    
    # 5. Box Plot de Score de Sentimiento
    st.subheader("5. Score de Sentimiento por Celebridad")
    st.markdown("Distribución del score de confianza del sentimiento (0.0 a 1.0) para los artículos del Top 10 de celebridades.")
    
    top_10_artists = [a for a, _ in Counter(all_artists).most_common(10)]

    # 1. Filtrar los artículos que contienen al menos a uno del top 10
    box_plot_df = df_filtered[
        df_filtered["artistas_en_articulo"].apply(
            lambda artists: any(a in top_10_artists for a in artists)
        )
    ].copy()
    
    # 2. "Explotar" (duplicar filas) para tener una fila por mención de artista/artículo
    box_plot_df_exploded = box_plot_df.explode("artistas_en_articulo")
    
    # 3. Filtrar para quedarnos solo con los artistas del top 10 en las filas explotadas
    box_plot_df_top = box_plot_df_exploded[
        box_plot_df_exploded["artistas_en_articulo"].isin(top_10_artists)
    ].copy()

    # Box Plot
    fig_box = px.box(
        box_plot_df_top,
        x="confidence",  
        y="artistas_en_articulo",  
        orientation="h",
        color="artistas_en_articulo", 
        points=False, # Eliminar los puntos individuales (outliers) para un gráfico más limpio
        title="Score de Confianza (Confidence) de Sentimiento del Top 10 de Celebridades",
        labels={"confidence": "Score de Confianza de Sentimiento (0.0 a 1.0)", "artistas_en_articulo": "Celebridad"},
        hover_data={"confidence": True, "sentiment": True, "titulo": True}
    )

    fig_box.update_layout(showlegend=False) # Ocultar leyenda de colores
    fig_box.update_traces(quartilemethod="exclusive")
    st.plotly_chart(apply_editorial_layout(fig_box), width='stretch') # Ajustar al ancho de la columna


# =========================
# 🧑 SECCIÓN: ANÁLISIS POR CELEBRIDAD
# =========================
else:
    st.header("Análisis Detallado por Celebridad")

    # --- Selector con Autocompletado ---
    all_artists = sorted(
        {a for sub in df_filtered["artistas_en_articulo"] for a in sub}
    )

    search = st.text_input("Escribe el nombre del artista o celebridad", help="Empieza a escribir para filtrar la lista.")

    # Implementación básica de autocompletado/filtro
    matched_artists = [
        a for a in all_artists if search.lower() in a.lower()
    ] if search else []

    if not matched_artists:
        st.info("Escribe para buscar un artista o selecciona uno de la lista completa.")
        # Mostrar una selección con todos si no hay búsqueda, o detener si hay búsqueda sin resultados.
        if not search:
            selected_artist = st.selectbox("Seleccionar artista", all_artists)
        else:
            st.stop()
    else:
        selected_artist = st.selectbox(
            "Artistas encontrados",
            matched_artists
        )
    
    # Si se detuvo, el código de abajo no se ejecuta. Si continúa, se filtra por el artista.
    if 'selected_artist' not in locals():
        st.stop() # Doble check por si el flujo inicial no asignó selected_artist

    # DataFrame filtrado para el artista seleccionado
    artist_df = df_filtered[
        df_filtered["artistas_en_articulo"].apply(lambda x: selected_artist in x)
    ]
    
    if artist_df.empty:
         st.warning(f"No hay artículos para **{selected_artist}** en el rango de fechas seleccionado.")
         st.stop()
         
    # --- 1. Google Trends + Apariciones ---
    st.subheader("1. Tendencia y Apariciones")
    st.markdown("Interés de búsqueda en Google de la celebridad con líneas verticales que indican la fecha de publicación de un artículo en Vogue.")
    
    trends = get_trends([selected_artist], start_date, end_date)
    
    if not trends.empty:
        fig_trends_artist = px.line(
            trends,
            title=f"{selected_artist} – Google Trends vs. Artículos de Vogue",
            labels={"value": "Interés a lo largo del tiempo"},
            color_discrete_sequence=[PALETTE["rose"]]
        ) 

        # AÑADIR LÍNEAS VERTICALES: Se eliminan los argumentos 'annotation_text' y 'annotation_position'
        for d in artist_df["fecha"].dt.date.unique():
            fig_trends_artist.add_vline(
                x=d.strftime("%Y-%m-%d"), 
                line_dash="dot", 
                line_color=PALETTE["dark_gray"]
                # Se eliminaron: annotation_text y annotation_position
            )

        st.plotly_chart(apply_editorial_layout(fig_trends_artist), width='stretch')
    else:
        st.info(f"No hay datos de Google Trends disponibles para **{selected_artist}** en este periodo.")
    # --- 2. Barras de Sentimiento ---
    st.subheader("2. Distribución de Artículos por Sentimiento")
    st.markdown("Conteo de los artículos de la celebridad clasificados por el sentimiento detectado (Positivo, Neutral, Negativo o Desconocido).")

    sentiment_counts = (
        artist_df["sentiment"]
        .value_counts()
        .reset_index()
        .rename(columns={"sentiment": "Sentimiento", "count": "Artículos"})
        .sort_values("Artículos", ascending=False)
    )

    fig_sentiment = px.bar(
            sentiment_counts,
            x="Sentimiento",
            y="Artículos",
            #color="Sentimiento",
            title=f"Artículos sobre {selected_artist} por Sentimiento",
            # Mapear los colores personalizados
            color_discrete_map=SENTIMENT_COLORS
        )
    st.plotly_chart(apply_editorial_layout(fig_sentiment), width='stretch')

    # --- 3. Artículos + Sentimiento ---
    st.subheader("3. Artículos y Sentimiento")
    st.markdown("Lista de todos los artículos de Vogue que mencionan a la celebridad, resaltando el sentimiento y su score de confianza.")

    for _, row in artist_df.iterrows():
        color = sentiment_to_color(row["sentiment"]) # Obtener el color según el sentimiento
        
        # Mostrar la tarjeta de artículo usando HTML para el fondo de color
        st.markdown(
            f"""
            <div style="background:{color};padding:15px;border-radius:8px;margin-bottom:15px;box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: {PALETTE['black']}; font-family: Didot, serif;">{row['titulo']}</h4>
                <small style="display: block; margin-top: 5px; color: {PALETTE['dark_gray']};">
                    Fecha: {row['fecha'].date()} &mdash; 
                    Sentimiento: <strong>{row['sentiment'].capitalize()}</strong> 
                    (Score: {row['confidence']:.2f})
                </small>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if row.get("link"):
            st.markdown(f"[Ver artículo completo]({row['link']})")