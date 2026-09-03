import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 1. Configuración de la página
st.set_page_config(
    page_title="PBG Corrientes | Dashboard Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Inyección de CSS Personalizado para Tema Oscuro Moderno y Glassmorphism
st.markdown(
    """
    <style>
    /* Fondo principal y tipo de fuente */
    .main {
        background-color: #0E1117;
        color: #FAFAFA;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Estilo de Tarjetas KPI con Glassmorphism */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: rgba(0, 212, 255, 0.4);
    }
    .metric-title {
        color: #8C9BAE;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .metric-value {
        color: #00E5FF;
        font-size: 1.6rem;
        font-weight: 700;
    }
    .metric-delta {
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 6px;
    }
    .delta-positive { color: #00E676; }
    .delta-negative { color: #FF5252; }

    /* Ocultar elementos innecesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Personalizar Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    </style>
""",
    unsafe_allow_html=True,
)


# 3. Cargar y Procesar Datos
@st.cache_data
def load_and_process_data():
    df = pd.read_csv("pbg_corrientes.csv", sep=";", encoding="latin1")

    period_cols = [c for c in df.columns if c.startswith("20")]

    for col in period_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    years = list(range(2004, 2025))
    quarters = [1, 2, 3, 4]

    def proyectar_2025(row):
        proyecciones = {}
        for q in quarters:
            cols_q = [f"{y}_{q}" for y in years[-5:]]
            y_vals = row[cols_q].values.astype(float)
            x_vals = np.array(years[-5:])
            mask = ~np.isnan(y_vals)

            if np.sum(mask) >= 2:
                m, b = np.polyfit(x_vals[mask], y_vals[mask], 1)
                pred_2025 = m * 2025 + b
            else:
                pred_2025 = (
                    np.nanmean(y_vals) if np.sum(mask) > 0 else np.nan
                )

            proyecciones[f"2025_{q}"] = round(float(pred_2025), 2)
        return pd.Series(proyecciones)

    df_2025 = df.apply(proyectar_2025, axis=1)
    df_full = pd.concat([df, df_2025], axis=1)

    return df_full, [c for c in df_full.columns if c.startswith("20")]


df_raw, all_period_cols = load_and_process_data()

# 4. Header del Dashboard
st.markdown(
    """
    <div style="padding: 10px 0px 20px 0px;">
        <h1 style="color: #FFFFFF; font-size: 2.3rem; font-weight: 800; margin:0;">
            ⚡ Dashboard Producto Bruto Geográfico (PBG)
        </h1>
        <p style="color: #8C9BAE; font-size: 1rem; margin-top: 5px;">
            Provincia de Corrientes • Serie Histórica (2004–2024) y Proyección Inteligente (2025)
        </p>
    </div>
""",
    unsafe_allow_html=True,
)

# 5. Sidebar / Controles
st.sidebar.markdown("### ⚙️ Panel de Control")

actividades = df_raw["Descripción"].dropna().unique().tolist()
actividad_selected = st.sidebar.selectbox(
    "Seleccionar Sector / Indicador:",
    actividades,
    index=actividades.index("Producto Bruto Geográfico")
    if "Producto Bruto Geográfico" in actividades
    else 0,
)

rango_anios = st.sidebar.slider(
    "Rango Temporal:",
    min_value=2004,
    max_value=2025,
    value=(2017, 2025),
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "💡 **Info:** La proyección 2025 utiliza regresión lineal estacional ajustada al último quinquenio (2020-2024)."
)

# Transformación de datos
df_row = df_raw[df_raw["Descripción"] == actividad_selected]

df_long = df_row.melt(
    id_vars=["Letra", "Código de actividad", "Descripción"],
    value_vars=all_period_cols,
    var_name="Periodo",
    value_name="Monto",
)

df_long["Año"] = df_long["Periodo"].apply(lambda x: int(x.split("_")[0]))
df_long["Trimestre"] = df_long["Periodo"].apply(
    lambda x: f"Q{x.split('_')[1]}"
)
df_long["Tipo"] = df_long["Año"].apply(
    lambda x: "Proyectado" if x == 2025 else "Histórico"
)

df_filtered = df_long[
    (df_long["Año"] >= rango_anios[0]) & (df_long["Año"] <= rango_anios[1])
]

# 6. Tarjetas Métricas Personalizadas
val_2024_total = df_long[df_long["Año"] == 2024]["Monto"].sum()
val_2025_total = df_long[df_long["Año"] == 2025]["Monto"].sum()
val_2024_4 = df_long[df_long["Periodo"] == "2024_4"]["Monto"].values[0]
val_2025_4 = df_long[df_long["Periodo"] == "2025_4"]["Monto"].values[0]

var_interanual = ((val_2025_total - val_2024_total) / val_2024_total) * 100
class_delta = "delta-positive" if var_interanual >= 0 else "delta-negative"
icon_delta = "▲" if var_interanual >= 0 else "▼"

col1, col2, col3, col4 = st.columns(4)


def fmt(val):
    return f"$ {val:,.0f}".replace(",", ".")


with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">PBG Total 2024</div>
            <div class="metric-value">{fmt(val_2024_total)}</div>
            <div class="metric-delta" style="color:#8C9BAE;">M$ de pesos</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Proyección 2025</div>
            <div class="metric-value" style="color:#7C4DFF;">{fmt(val_2025_total)}</div>
            <div class="metric-delta {class_delta}">{icon_delta} {var_interanual:.2f}% vs 2024</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Cierre 2024 (Q4)</div>
            <div class="metric-value">{fmt(val_2024_4)}</div>
            <div class="metric-delta" style="color:#8C9BAE;">Histórico</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Estimación 2025 (Q4)</div>
            <div class="metric-value" style="color:#00E5FF;">{fmt(val_2025_4)}</div>
            <div class="metric-delta" style="color:#00E5FF;">Proyectado</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# 7. Gráfico de Tendencia Principal con Estilo Cyberpunk / Neon
st.markdown(f"### 📈 Trayectoria Temporal: **{actividad_selected}**")

fig = go.Figure()

df_hist = df_filtered[df_filtered["Tipo"] == "Histórico"]
df_proj = df_filtered[df_filtered["Tipo"] == "Proyectado"]
last_hist = df_hist.tail(1)
df_proj_connected = pd.concat([last_hist, df_proj])

# Área sombreada bajo la curva
fig.add_trace(
    go.Scatter(
        x=df_hist["Periodo"],
        y=df_hist["Monto"],
        mode="lines+markers",
        name="Histórico",
        line=dict(color="#00E5FF", width=3, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(0, 229, 255, 0.05)",
        marker=dict(
            size=6,
            color="#00E5FF",
            line=dict(color="#FFFFFF", width=1)  # <-- Cambio aquí
        ),
    )
)

fig.add_trace(
    go.Scatter(
        x=df_proj_connected["Periodo"],
        y=df_proj_connected["Monto"],
        mode="lines+markers",
        name="Proyección 2025",
        line=dict(color="#7C4DFF", width=3, dash="dash", shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(124, 77, 255, 0.08)",
        marker=dict(size=8, color="#7C4DFF", symbol="diamond"),
    )
)

fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8C9BAE", family="Inter"),
    xaxis=dict(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.05)",
        showline=True,
        linecolor="rgba(255,255,255,0.1)",
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.05)",
        showline=True,
        linecolor="rgba(255,255,255,0.1)",
        title="Miles de Pesos",
    ),
    hovermode="x unified",
    height=420,
    margin=dict(l=10, r=10, t=20, b=10),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(color="#FAFAFA"),
    ),
)

st.plotly_chart(fig, use_container_width=True)

# 8. Gráficos Secundarios (Comparativa Anual y Rosco)
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 📊 Totales Comparativos Anuales")
    df_annual = (
        df_filtered.groupby(["Año", "Tipo"])["Monto"].sum().reset_index()
    )

    fig_bar = px.bar(
        df_annual,
        x="Año",
        y="Monto",
        color="Tipo",
        color_discrete_map={"Histórico": "#00E5FF", "Proyectado": "#7C4DFF"},
        template="plotly_dark",
    )

    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8C9BAE"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title=""),
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(title=""),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.markdown("### 🍕 Participación Sectorial (2025)")
    df_sectores = df_raw[
        (df_raw["Letra"].notnull())
        & (df_raw["Código de actividad"].isnull())
        & (df_raw["Letra"] != "PBG")
    ].copy()

    cols_2025 = ["2025_1", "2025_2", "2025_3", "2025_4"]
    df_sectores["Total_2025"] = df_sectores[cols_2025].sum(axis=1)

    fig_pie = px.pie(
        df_sectores,
        values="Total_2025",
        names="Descripción",
        hole=0.55,
        color_discrete_sequence=px.colors.sequential.Darkmint_r,
    )

    fig_pie.update_traces(
        textposition="outside", textinfo="label+percent", marker=dict(line=dict(color="#0E1117", width=2))
    )

    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FAFAFA"),
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# 9. Descarga e Inspección de Datos
st.markdown("---")
with st.expander("🔍 Explorar o Descargar el Dataset Consolidado"):
    st.dataframe(df_raw, use_container_width=True)

    csv_data = df_raw.to_csv(sep=";", decimal=",", index=False).encode(
        "latin1"
    )
    st.download_button(
        label="📥 Descargar CSV Proyectado 2025",
        data=csv_data,
        file_name="pbg_corrientes_2025_modern.csv",
        mime="text/csv",
    )