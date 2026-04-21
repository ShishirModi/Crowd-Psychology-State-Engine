"""
CPSE — Crowd Psychology State Engine
Enterprise Dashboard (Streamlit)

Real-time crowd dynamics classification, risk analysis, and intervention
planning.  Connects to TomTom Traffic & OpenWeatherMap APIs with automatic
fallback to high-fidelity simulation when keys are unavailable.
"""

import streamlit as st
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime

from signals.tomtom import get_signal_provider
from signals.geocoder import TomTomGeocoder
from metrics.compression import CrowdMetrics
from engine.classifier import CrowdClassifier
from interventions.recommender import InterventionRecommender
from utils.config_loader import load_config
from utils.time_helper import get_local_time
from data_layer.vectorizer import CrowdStateVectorizer
from data_layer.database import get_db_client
from engine.anomaly import AnomalyDetector
from dotenv import load_dotenv
import os

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CPSE | Crowd Psychology State Engine",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════
# LIGHT-MODE PROFESSIONAL CSS
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Fonts & Base ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background-color: #f8fafc !important;
    color: #1e293b !important;
}

/* ── Hide Streamlit chrome ────────────────────────────────────────── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ── Main content padding ─────────────────────────────────────────── */
.main .block-container {
    padding: 1.5rem 2rem 3rem !important;
    max-width: 1440px;
}

/* ── Sidebar ──────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption {
    color: #475569 !important;
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #1e293b !important;
}

/* ── Metric values ────────────────────────────────────────────────── */
[data-testid="stMetricValue"] {
    color: #1e293b !important;
    font-size: 24px !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}
[data-testid="stMetricDelta"] {
    font-size: 12px !important;
}

/* ── State Banner ─────────────────────────────────────────────────── */
.state-banner {
    padding: 20px 28px;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    border: 1px solid transparent;
    border-left-width: 5px;
    border-left-style: solid;
}
.state-banner .state-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    opacity: 0.75;
    margin-bottom: 4px;
}
.state-banner .state-value {
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 0.5px;
}
.state-banner .state-right { text-align: right; }
.state-banner .confidence-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    opacity: 0.65;
    margin-bottom: 2px;
}
.state-banner .confidence-value {
    font-size: 30px;
    font-weight: 800;
}
.state-banner .state-summary {
    font-size: 12px;
    opacity: 0.7;
    margin-top: 4px;
    font-weight: 400;
}

/* pastel state colours */
.banner-stable      { background:#f0fdf4; border-color:#bbf7d0; border-left-color:#22c55e; color:#15803d; }
.banner-compressing { background:#fffbeb; border-color:#fde68a; border-left-color:#f59e0b; color:#b45309; }
.banner-volatile    { background:#fef2f2; border-color:#fecaca; border-left-color:#f87171; color:#b91c1c; }
.banner-agitated    { background:#faf5ff; border-color:#ddd6fe; border-left-color:#a78bfa; color:#6d28d9; }
.banner-fragmenting { background:#f0f9ff; border-color:#bae6fd; border-left-color:#38bdf8; color:#0369a1; }

/* ── Risk Score Bar ───────────────────────────────────────────────── */
.risk-bar-container {
    background: #ffffff;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 20px;
    border: 1px solid #e2e8f0;
}
.risk-bar-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #64748b;
    margin-bottom: 8px;
}
.risk-bar-outer {
    background: #f1f5f9;
    border-radius: 6px;
    height: 12px;
    overflow: hidden;
}
.risk-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.5s ease;
}
.risk-bar-value {
    font-size: 20px;
    font-weight: 700;
    margin-top: 6px;
}

/* ── Criteria Panels ──────────────────────────────────────────────── */
.criteria-panel {
    background: #f8fafc;
    border-radius: 6px;
    padding: 12px 14px;
    margin-top: 8px;
    border-left: 3px solid #cbd5e1;
    font-size: 12px;
    line-height: 1.6;
    color: #374151;
}
.criteria-panel.safe     { border-left-color: #86efac; }
.criteria-panel.watch    { border-left-color: #fde68a; }
.criteria-panel.warning  { border-left-color: #fdba74; }
.criteria-panel.critical { border-left-color: #fca5a5; }

.criteria-row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    border-bottom: 1px solid rgba(203,213,225,0.5);
}
.criteria-row:last-child { border-bottom: none; }
.criteria-key {
    color: #64748b;
    font-weight: 500;
    font-size: 11px;
}
.criteria-val {
    color: #1e293b;
    font-weight: 600;
    font-size: 11px;
    font-family: 'Inter', monospace;
}
.criteria-verdict {
    margin-top: 8px;
    font-size: 11px;
    color: #475569;
    font-style: italic;
}

/* ── Intervention Cards ───────────────────────────────────────────── */
.intervention-card {
    background: #ffffff;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #cbd5e1;
    transition: box-shadow 0.15s ease;
}
.intervention-card:hover {
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.intervention-card.priority-critical { border-left-color: #fca5a5; }
.intervention-card.priority-high     { border-left-color: #fdba74; }
.intervention-card.priority-medium   { border-left-color: #fde68a; }
.intervention-card.priority-low      { border-left-color: #86efac; }

.intervention-action {
    color: #1e293b;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 5px;
}
.intervention-meta {
    font-size: 11px;
    color: #94a3b8;
}
.intervention-meta span { margin-right: 14px; }

/* ── Section Headers ──────────────────────────────────────────────── */
.section-header {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #94a3b8;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e2e8f0;
}

/* ── Dividers ─────────────────────────────────────────────────────── */
hr { border-color: #e2e8f0 !important; }

/* ── Expanders ────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    background: #ffffff !important;
}

/* ── Buttons ──────────────────────────────────────────────────────── */
[data-testid="stButton"] button {
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}

/* ── Responsive column stacking ───────────────────────────────────── */
@media (max-width: 960px) {
    [data-testid="column"] {
        min-width: calc(50% - 0.5rem) !important;
        flex: 0 0 calc(50% - 0.5rem) !important;
    }
}
@media (max-width: 620px) {
    [data-testid="column"] {
        min-width: 100% !important;
        flex: 0 0 100% !important;
    }
    .main .block-container {
        padding: 1rem 0.75rem !important;
    }
    .state-banner {
        flex-direction: column;
        align-items: flex-start;
        gap: 12px;
    }
}

/* ── Toast ────────────────────────────────────────────────────────── */
.stToast { font-family: 'Inter', sans-serif !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════
if "history" not in st.session_state:
    st.session_state.history = []
if "metrics" not in st.session_state:
    st.session_state.metrics = CrowdMetrics()
if "anomaly_detector" not in st.session_state:
    st.session_state.anomaly_detector = AnomalyDetector()
if "vectorizer" not in st.session_state:
    st.session_state.vectorizer = CrowdStateVectorizer()
if "location" not in st.session_state:
    config = load_config()
    st.session_state.location = config.get("location", {})
    if "name" not in st.session_state.location:
        st.session_state.location["name"] = "Default Location"
if "is_running" not in st.session_state:
    st.session_state.is_running = False

# ═══════════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════
def check_password():
    valid_passwords = ["cpseisawesome"]
    try:
        if "APP_PASSWORD" in st.secrets:
            secret_val = st.secrets["APP_PASSWORD"]
            valid_passwords = secret_val if isinstance(secret_val, list) else [str(secret_val)]
    except Exception:
        pass
    if not valid_passwords:
        env_pw = os.environ.get("APP_PASSWORD")
        valid_passwords = [env_pw] if env_pw else ["cpseisawesome"]

    import secrets as _secrets

    def password_entered():
        user_pass = st.session_state["password"]
        for vp in valid_passwords:
            if _secrets.compare_digest(user_pass, vp):
                st.session_state["password_correct"] = True
                st.session_state["is_admin"] = _secrets.compare_digest(user_pass, valid_passwords[0])
                del st.session_state["password"]
                return
        st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        _render_login(password_entered)
        return False
    elif not st.session_state["password_correct"]:
        _render_login(password_entered, error=True)
        return False
    return True


def _render_login(callback, error=False):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### CPSE — Secure Access")
        st.text_input("Enter access key", type="password", on_change=callback, key="password")
        if error:
            st.error("Access denied — incorrect key.")
        st.caption("Contact your administrator for access credentials.")


if not check_password():
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# SERVICE INIT
# ═══════════════════════════════════════════════════════════════════════════
if "services" not in st.session_state:
    st.session_state.services = {
        "signal_provider": get_signal_provider(),
        "geocoder": TomTomGeocoder(),
        "classifier": CrowdClassifier(),
        "recommender": InterventionRecommender(),
        "db": get_db_client(),
    }

signal_provider = st.session_state.services["signal_provider"]
geocoder = st.session_state.services["geocoder"]
classifier = st.session_state.services["classifier"]
recommender = st.session_state.services["recommender"]


# ═══════════════════════════════════════════════════════════════════════════
# HELPER: Plotly Theme
# ═══════════════════════════════════════════════════════════════════════════
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(248,250,252,0.9)",
    font=dict(family="Inter, sans-serif", color="#64748b", size=11),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=10, color="#64748b"),
    ),
    xaxis=dict(
        gridcolor="rgba(226,232,240,0.9)",
        zerolinecolor="rgba(226,232,240,0.9)",
        linecolor="#e2e8f0",
    ),
    yaxis=dict(
        gridcolor="rgba(226,232,240,0.9)",
        zerolinecolor="rgba(226,232,240,0.9)",
        linecolor="#e2e8f0",
    ),
)

# Pastel palette — used in the state distribution pie and history charts
STATE_COLORS = {
    "Stable":      "#86efac",   # pastel green
    "Compressing": "#fde68a",   # pastel amber
    "Volatile":    "#fca5a5",   # pastel red
    "Agitated":    "#c4b5fd",   # pastel violet
    "Fragmenting": "#bae6fd",   # pastel sky
}

# Muted chart line colours
CHART_COLORS = {
    "congestion":  "#7eb8da",   # steel blue
    "gradient":    "#c4a35a",   # warm gold
    "velocity":    "#a89ad4",   # soft purple
    "anomaly":     "#d47a7a",   # muted rose
}


def risk_bar_color(score):
    if score > 75:
        return "#f87171"    # pastel red
    elif score > 50:
        return "#fb923c"    # pastel orange
    elif score > 25:
        return "#fbbf24"    # pastel amber
    return "#4ade80"        # pastel green


def render_criteria_panel(rating, rows_dict, verdict=""):
    """Render a criteria breakdown panel as HTML."""
    rows_html = ""
    for k, v in rows_dict.items():
        rows_html += f'<div class="criteria-row"><span class="criteria-key">{k}</span><span class="criteria-val">{v}</span></div>'
    verdict_html = f'<div class="criteria-verdict">{verdict}</div>' if verdict else ""
    return f'<div class="criteria-panel {rating}">{rows_html}{verdict_html}</div>'


# ── Safe defaults for environmental variables ────────────────────────────────
# These are always overwritten inside the sidebar expander, but defining them
# here prevents NameErrors if the expander code raises before assignment.
env_weather_val  = 0.0
env_width        = 1.0
env_event        = False
env_event_val    = 0.0
use_live_weather = False
weather_cond     = "Unknown"
env_weather      = "Clear"

# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## CPSE Control Center")
    st.caption("Crowd Psychology State Engine v2.0")
    st.markdown("---")

    # Database connection status badge
    _db = st.session_state.services.get("db") if "services" in st.session_state else None
    if _db is not None:
        if _db.connected:
            st.markdown(
                '<div style="background:#f0fdf4;border:1px solid #86efac;border-left:3px solid #22c55e;'
                'border-radius:6px;padding:8px 12px;font-size:11px;color:#15803d;">'
                '<b>DB</b> Connected — Neon PostgreSQL</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:#fef2f2;border:1px solid #fca5a5;border-left:3px solid #f87171;'
                'border-radius:6px;padding:8px 12px;font-size:11px;color:#b91c1c;">'
                f'<b>DB</b> {_db.status_label}</div>',
                unsafe_allow_html=True,
            )
    st.markdown("---")

    # Location
    st.markdown('<p class="section-header">MONITORING LOCATION</p>', unsafe_allow_html=True)
    current_loc_name = st.session_state.location.get("name", "Unknown")
    st.info(f"**{current_loc_name}**")

    search_query = st.text_input("Search Location", placeholder="e.g. Times Square, NYC")
    if st.button("Search", use_container_width=True):
        if search_query:
            results = geocoder.search(search_query)
            if results:
                st.session_state.search_results = results
                st.success(f"Found {len(results)} matches.")
            else:
                st.error("No results found.")

    if "search_results" in st.session_state:
        options = {f"{i+1}. {r['name']}": r for i, r in enumerate(st.session_state.search_results)}
        selected_option = st.selectbox("Select Result", list(options.keys()))
        if st.button("Set as Monitor Target", use_container_width=True):
            sel = options[selected_option]
            new_loc = {"lat": sel["lat"], "lon": sel["lon"], "name": sel["name"]}
            current = st.session_state.location
            if current.get("lat") != new_loc["lat"] or current.get("lon") != new_loc["lon"]:
                st.session_state.history = []
                st.session_state.metrics = CrowdMetrics()
                st.session_state.anomaly_detector = AnomalyDetector()
            st.session_state.location = new_loc
            del st.session_state.search_results
            st.rerun()

    st.markdown("---")

    # Controls
    st.markdown('<p class="section-header">ANALYSIS CONTROLS</p>', unsafe_allow_html=True)

    if st.session_state.is_running:
        if st.button("Stop Analysis", type="primary", use_container_width=True):
            st.session_state.is_running = False
            st.rerun()
    else:
        if st.button("Start Analysis", type="primary", use_container_width=True):
            st.session_state.is_running = True
            st.rerun()

    auto_refresh = st.checkbox("Live Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Interval (s)", 10, 300, 30)

    st.markdown("---")

    # Environment
    with st.expander("Environmental Conditions", expanded=False):
        from signals.weather import OpenWeatherMapSignal

        weather_provider = OpenWeatherMapSignal()
        use_live_weather = False
        weather_cond = "Unknown"

        if weather_provider.api_key:
            use_live_weather = st.checkbox("Use Live Weather", value=True)
        else:
            st.warning("Set `OPENWEATHERMAP_API_KEY` for live weather.")

        if not use_live_weather:
            env_weather = st.select_slider("Weather Condition", options=["Clear", "Rain", "Storm"], value="Clear")
            weather_map = {"Clear": 0.0, "Rain": 0.5, "Storm": 1.0}
            env_weather_val = weather_map[env_weather]
        else:
            loc = st.session_state.location
            w_risk, w_cond, _ = weather_provider.fetch_weather_risk(loc["lat"], loc["lon"])
            if w_risk is not None:
                env_weather_val = w_risk
                weather_cond = w_cond
                st.success(f"Live: **{w_cond}** (Risk: {w_risk:.2f})")
            else:
                st.error("Weather fetch failed — using manual.")
                env_weather = st.select_slider("Weather (Fallback)", options=["Clear", "Rain", "Storm"], value="Clear")
                weather_map = {"Clear": 0.0, "Rain": 0.5, "Storm": 1.0}
                env_weather_val = weather_map[env_weather]
                use_live_weather = False

        env_width = st.slider("Passage Width Factor", 0.1, 2.0, 1.0, help="< 1.0 = Bottleneck, > 1.0 = Open plaza")
        env_event = st.checkbox("Active Event / Protest", value=False)
        env_event_val = 1.0 if env_event else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# VIEW CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════
view_mode = "Live Monitor"
if st.session_state.get("is_admin", False):
    st.sidebar.markdown("---")
    st.sidebar.markdown('<p class="section-header">ADMIN CONSOLE</p>', unsafe_allow_html=True)
    view_mode = st.sidebar.radio("View Mode", ["Live Monitor", "Database Records"])


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE VIEW
# ═══════════════════════════════════════════════════════════════════════════
main_container = st.empty()

if view_mode == "Database Records":
    with main_container.container():
        st.markdown("## Historical Telemetry Records")
        st.caption("Query and analyze persisted crowd telemetry from Neon PostgreSQL.")

        # ── Bug 1 fix: check .connected, not truthiness of the object ────────
        db = st.session_state.services.get("db")
        if db is None:
            st.error("Database service not initialised.")
            st.stop()

        if not db.connected:
            st.warning(
                f"Database not connected — {db.status_label}. "
                "Set the `NEON_PASS` environment variable and restart the app."
            )
            st.stop()

        # ── Filters ───────────────────────────────────────────────────────────
        location_options = ["All"] + db.fetch_unique_locations()

        st.markdown('<p class="section-header">QUERY FILTERS</p>', unsafe_allow_html=True)
        f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
        with f1:
            db_location = st.selectbox("Location", location_options, key="filter_loc")
        with f2:
            db_limit = st.slider("Limit", 10, 500, 100, step=10, key="filter_lim")
        with f3:
            st.write("")
            st.write("")
            db_anomaly = st.checkbox("Anomalies Only", key="filter_anom")
        with f4:
            st.write("")
            st.write("")
            if st.button("Refresh", type="primary"):
                st.rerun()

        st.markdown("---")

        # ── Bug 2 fix: fetch OUTSIDE spinner so st.stop() never runs inside it ─
        with st.spinner("Querying Neon DB..."):
            data = db.fetch_filtered_logs(
                limit=db_limit,
                location=db_location,
                anomaly_only=db_anomaly,
            )

        # Empty-state guard — AFTER the spinner has already closed cleanly
        if not data:
            st.info("No records found. Run an analysis session first, then return here.")
            st.stop()

        df = pd.DataFrame(data)

        # Normalise created_at to naive UTC for consistent display
        if "created_at" in df.columns and pd.api.types.is_datetime64_any_dtype(df["created_at"]):
            df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.tz_localize(None)

        # ── KPI row ───────────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Records", f"{len(df):,}")

        avg_cong = df["congestion"].mean() if "congestion" in df.columns else 0
        k2.metric("Avg Congestion", f"{avg_cong:.3f}")

        if "anomaly_score" in df.columns:
            n_anom = int((df["anomaly_score"] > 2.5).sum())
        else:
            n_anom = 0
        k3.metric("Anomalies Detected", f"{n_anom:,}")

        # Bug 3 fix: guard against all-NaN state column before .mode()
        if "state" in df.columns:
            clean_states = df["state"].dropna()
            mode_state = clean_states.mode().iloc[0] if len(clean_states) > 0 else "N/A"
        else:
            mode_state = "N/A"
        k4.metric("Dominant State", mode_state)

        st.markdown("---")

        # ── Trend chart (only when a single location is selected) ─────────────
        if db_location != "All" and "created_at" in df.columns and "congestion" in df.columns:
            st.markdown(
                f'<p class="section-header">CONGESTION TREND — {db_location.upper()}</p>',
                unsafe_allow_html=True,
            )
            chart_df = df.sort_values("created_at")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=chart_df["created_at"], y=chart_df["congestion"],
                mode="lines+markers", name="Congestion",
                line=dict(color=CHART_COLORS["congestion"], width=2),
                marker=dict(size=4),
                fill="tozeroy", fillcolor="rgba(126,184,218,0.12)",
            ))
            if "gradient" in chart_df.columns:
                fig.add_trace(go.Scatter(
                    x=chart_df["created_at"], y=chart_df["gradient"],
                    mode="lines", name="Gradient",
                    line=dict(color=CHART_COLORS["gradient"], width=1.5, dash="dot"),
                ))
            if "anomaly_score" in chart_df.columns:
                fig.add_trace(go.Scatter(
                    x=chart_df["created_at"], y=chart_df["anomaly_score"],
                    mode="lines", name="Anomaly Z",
                    line=dict(color=CHART_COLORS["anomaly"], width=1.2, dash="dash"),
                ))
                fig.add_hline(
                    y=2.5, line_dash="dot",
                    line_color="rgba(212,122,122,0.5)",
                    annotation_text="Z=2.5", annotation_font_color="#d47a7a",
                )
            fig.update_layout(**PLOTLY_LAYOUT, height=360, yaxis_range=[0, 1.1])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Select a specific location to view the trend chart.")

        # ── Data table ────────────────────────────────────────────────────────
        st.markdown('<p class="section-header">DETAILED LOGS</p>', unsafe_allow_html=True)

        # Friendly column rename for display
        display_df = df.rename(columns={
            "created_at":    "Timestamp",
            "location_name": "Location",
            "latitude":      "Lat",
            "longitude":     "Lon",
            "congestion":    "Congestion",
            "speed":         "Speed (km/h)",
            "gradient":      "Gradient",
            "velocity_var":  "Velocity CV",
            "anomaly_score": "Anomaly Z",
            "risk_score":    "Risk Score",
            "state":         "State",
        })
        # Drop internal columns not useful for the operator
        display_df = display_df.drop(columns=[c for c in ["id", "session_id", "Lat", "Lon"] if c in display_df.columns])

        col_cfg: dict = {}
        if "Timestamp"    in display_df.columns:
            col_cfg["Timestamp"]    = st.column_config.DatetimeColumn("Timestamp", format="D MMM YYYY, HH:mm:ss")
        if "Congestion"   in display_df.columns:
            col_cfg["Congestion"]   = st.column_config.ProgressColumn("Congestion",   min_value=0, max_value=1, format="%.3f")
        if "Anomaly Z"    in display_df.columns:
            col_cfg["Anomaly Z"]    = st.column_config.NumberColumn("Anomaly Z",      format="%.2f")
        if "Risk Score"   in display_df.columns:
            col_cfg["Risk Score"]   = st.column_config.ProgressColumn("Risk Score",   min_value=0, max_value=100, format="%.0f")
        if "Speed (km/h)" in display_df.columns:
            col_cfg["Speed (km/h)"] = st.column_config.NumberColumn("Speed (km/h)",   format="%.1f")

        st.dataframe(display_df, column_config=col_cfg, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV Export", csv,
            "cpse_telemetry.csv", "text/csv",
            key="dl-csv",
        )


# ═══════════════════════════════════════════════════════════════════════════
# LIVE MONITOR VIEW
# ═══════════════════════════════════════════════════════════════════════════
else:
    with main_container.container():

        # ── Header ────────────────────────────────────────────────────────
        h1, h2 = st.columns([3, 1])
        with h1:
            st.markdown("## Crowd Psychology State Engine")
            st.caption("Real-time crowd dynamics classification, risk analysis & intervention planning")
        with h2:
            loc = st.session_state.location
            st.markdown(f"**{loc.get('name', 'Unknown')}**")
            st.caption(f"{loc.get('lat', 0):.4f}°N, {loc.get('lon', 0):.4f}°E")

        signal_provider.set_location(loc["lat"], loc["lon"], loc.get("name", "Unknown"))

        # ── Data Collection ───────────────────────────────────────────────
        if not st.session_state.is_running:
            st.info("Analysis paused. Click **Start Analysis** in the sidebar to begin real-time monitoring.")
            congestion = gradient = velocity_var = anomaly_score = 0.0
            current_speed = 0.0
            state = "Stable"
            confidence = 0.0
            local_time = get_local_time(loc["lat"], loc["lon"])
            breakdown = {}
            gradient_details = {}
            vv_details = {}
            anomaly_details = {}
            risk_score = 0
        else:
            with st.spinner("Syncing with live signal feeds..."):
                telemetry = signal_provider.fetch_telemetry()
                congestion = telemetry["congestion"]
                current_speed = telemetry["current_speed"]

                metrics_engine = st.session_state.metrics
                metrics_engine.update(congestion, current_speed)

                gradient, gradient_quality, gradient_details = metrics_engine.compute_compression_gradient()
                velocity_var, vv_details = metrics_engine.compute_velocity_variance()

                vectorizer = st.session_state.vectorizer
                anomaly_detector = st.session_state.anomaly_detector
                is_simulated = telemetry.get("is_simulated", False)

                if is_simulated:
                    st.toast("Using simulated data — API keys not configured")

                crowd_vector = vectorizer.create_state_vector(congestion, velocity_var, gradient)
                env_vector = vectorizer.create_environmental_vector(env_width, env_weather_val, env_event_val)

                is_anomaly, anomaly_score, anomaly_details = anomaly_detector.update_and_detect(crowd_vector)

                history_len = len(metrics_engine.congestion_history)
                state, confidence, breakdown = classifier.classify(
                    gradient,
                    velocity_var,
                    anomaly_score,
                    is_simulated=is_simulated,
                    history_len=history_len,
                    gradient_quality=gradient_quality,
                    env_weather_risk=env_weather_val,
                    env_width_factor=env_width,
                    env_event_active=env_event,
                )

                risk_score = breakdown.get("risk_score", {}).get("value", 0)
                local_time = get_local_time(loc["lat"], loc["lon"])

                # Persist
                record = {
                    "time": local_time,
                    "congestion": congestion,
                    "gradient": gradient,
                    "velocity_var": velocity_var,
                    "anomaly_score": anomaly_score,
                    "state": state,
                    "risk_score": risk_score,
                    "speed": current_speed,
                }
                st.session_state.history.append(record)
                if len(st.session_state.history) > 60:
                    st.session_state.history.pop(0)

                db_record = record.copy()
                db_record.update({
                    "location_name": loc.get("name", "Unknown"),
                    "lat": loc["lat"],
                    "lon": loc["lon"],
                })
                st.session_state.services["db"].insert_telemetry(db_record)

        # ══════════════════════════════════════════════════════════════════
        # DASHBOARD LAYOUT
        # ══════════════════════════════════════════════════════════════════

        # ── 1. State Banner ───────────────────────────────────────────────
        base_state = state.split(" (")[0]
        banner_class = f"banner-{base_state.lower()}" if base_state.lower() in {"stable","compressing","volatile","agitated","fragmenting"} else "banner-stable"
        state_info = breakdown.get("state_info", {})

        st.markdown(f"""
        <div class="state-banner {banner_class}">
            <div>
                <div class="state-label">Current Crowd State</div>
                <div class="state-value">{state.upper()}</div>
                <div style="font-size:12px;opacity:0.8;margin-top:4px;">{state_info.get('summary', '')}</div>
            </div>
            <div class="state-right">
                <div class="confidence-label">Confidence</div>
                <div class="confidence-value">{int(confidence*100)}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── 2. Composite Risk Score Bar ───────────────────────────────────
        bar_color = risk_bar_color(risk_score)
        risk_info = breakdown.get("risk_score", {})
        st.markdown(f"""
        <div class="risk-bar-container">
            <div style="display:flex;justify-content:space-between;align-items:baseline;">
                <div class="risk-bar-label">Composite Risk Score</div>
                <div class="risk-bar-value" style="color:{bar_color};">{risk_score}/100</div>
            </div>
            <div class="risk-bar-outer">
                <div class="risk-bar-fill" style="width:{risk_score}%;background:linear-gradient(90deg,#22c55e,#eab308,#f97316,#ef4444);"></div>
            </div>
            <div style="font-size:11px;color:#94a3b8;margin-top:6px;">{risk_info.get('verdict','')}</div>
            <div style="font-size:10px;color:#64748b;margin-top:2px;">Formula: {risk_info.get('formula','')}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── 3. Primary Metrics with Detailed Criteria ─────────────────────
        st.markdown('<p class="section-header">CROWD DYNAMICS METRICS</p>', unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)

        # -- Congestion Level --
        with m1:
            st.metric("Congestion Level", f"{congestion:.3f}")
            cg_bd = breakdown.get("compression_gradient", {})
            panel_data = {
                "Value": f"{congestion:.4f}",
                "Source": "TomTom Traffic API",
                "Formula": "1 − (Speed / FreeFlow)",
                "Range": "0.0 (free) → 1.0 (gridlock)",
                "Current Speed": f"{current_speed:.1f} km/h",
            }
            if gradient_details:
                panel_data["Trend"] = gradient_details.get("trend", "N/A")
                panel_data["Window"] = f"{gradient_details.get('window_seconds', 0)}s / {gradient_details.get('max_window_seconds', 60)}s"
            rating = cg_bd.get("rating", "safe") if cg_bd else "safe"
            st.markdown(render_criteria_panel(rating, panel_data, cg_bd.get("verdict", "")), unsafe_allow_html=True)

        # -- Compression Gradient --
        with m2:
            st.metric("Compression Gradient", f"{gradient:.4f}")
            gd = gradient_details if gradient_details else {}
            panel_data = {
                "Value": f"{gradient:.4f}",
                "Formula": "0.6×Level + 0.4×Slope×5",
                "Slope": f"{gd.get('slope', 0):+.6f}/sample",
                "Slope/Min": f"{gd.get('slope_per_minute', 0):+.4f}",
                "R² Fit": f"{gd.get('fit_quality_r2', 0):.4f}",
                "Method": gd.get("method", "N/A"),
                "Thresholds": f"Stable<{classifier.t_stable} | Comp<{classifier.t_compressing} | Vol<{classifier.t_volatile}",
            }
            cg_bd = breakdown.get("compression_gradient", {})
            rating = cg_bd.get("rating", "safe")
            st.markdown(render_criteria_panel(rating, panel_data, gd.get("verdict", "")), unsafe_allow_html=True)

        # -- Velocity Variance --
        with m3:
            st.metric("Velocity Variance (CV)", f"{velocity_var:.4f}")
            vd = vv_details if vv_details else {}
            panel_data = {
                "Value": f"{velocity_var:.4f}",
                "Formula": "σ(Speed) / μ(Speed)",
                "Mean Speed": f"{vd.get('mean_speed', 0):.2f} km/h",
                "Std Dev": f"{vd.get('std_dev', 0):.2f}",
                "Range": f"{vd.get('min_speed', 0):.1f}–{vd.get('max_speed', 0):.1f} km/h",
                "Turbulence": vd.get("turbulence_level", "N/A"),
                "Thresholds": "CV>0.10 mild | >0.25 escalate | >0.40 severe",
            }
            vv_bd = breakdown.get("velocity_variance", {})
            rating = vv_bd.get("rating", "safe")
            st.markdown(render_criteria_panel(rating, panel_data, vd.get("verdict", "")), unsafe_allow_html=True)

        # -- Anomaly Score --
        with m4:
            delta_val = "Normal" if anomaly_score < 2.5 else "ANOMALY"
            st.metric("Anomaly Score (Z)", f"{anomaly_score:.3f}", delta=delta_val, delta_color="inverse")
            ad = anomaly_details if anomaly_details else {}
            panel_data = {
                "Value": f"{anomaly_score:.4f}",
                "Formula": "max(|Xᵢ − μᵢ| / σᵢ)",
                "Status": ad.get("status", "N/A"),
                "Threshold": f"Z > {ad.get('threshold', 2.5)}",
                "History": f"{ad.get('history_depth', 0)} / {ad.get('min_required', 20)} min samples",
                "Mean Z": f"{ad.get('mean_z_score', 0):.4f}" if ad.get("status") == "active" else "Calibrating",
            }
            if ad.get("outlier_features"):
                panel_data["Outliers"] = ", ".join(ad["outlier_features"])
            an_bd = breakdown.get("anomaly_score", {})
            rating = an_bd.get("rating", "safe")
            st.markdown(render_criteria_panel(rating, panel_data, ad.get("verdict", "")), unsafe_allow_html=True)

        # ── 4. Confidence Breakdown ───────────────────────────────────────
        conf_bd = breakdown.get("confidence", {})
        if conf_bd:
            with st.expander("Confidence Score Breakdown", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Penalties Applied**")
                    if conf_bd.get("penalties"):
                        for p in conf_bd["penalties"]:
                            st.markdown(f"- {p}")
                    else:
                        st.markdown("- None")
                with c2:
                    st.markdown("**Bonuses Applied**")
                    if conf_bd.get("bonuses"):
                        for b in conf_bd["bonuses"]:
                            st.markdown(f"- {b}")
                    else:
                        st.markdown("- None")
                st.caption(conf_bd.get("verdict", ""))

        # ── 5. Environment Context ────────────────────────────────────────
        st.markdown("---")
        st.markdown('<p class="section-header">ENVIRONMENTAL CONTEXT</p>', unsafe_allow_html=True)
        e1, e2, e3 = st.columns(3)
        with e1:
            weather_display = weather_cond if (use_live_weather and weather_cond != "Unknown") else (env_weather if not use_live_weather else "Unknown")
            st.metric("Weather Condition", weather_display)
            env_bd = breakdown.get("environment", {})
            panel_data = {
                "Risk Factor": f"{env_weather_val:.2f}",
                "Source": "Live API" if use_live_weather else "Manual Override",
                "Scale": "0.0 Clear → 1.0 Extreme",
            }
            st.markdown(render_criteria_panel(
                "warning" if env_weather_val > 0.5 else ("watch" if env_weather_val > 0 else "safe"),
                panel_data
            ), unsafe_allow_html=True)
        with e2:
            st.metric("Passage Width", f"{env_width:.1f}x")
            panel_data = {
                "Factor": f"{env_width:.2f}",
                "Interpretation": "Bottleneck" if env_width < 0.5 else ("Narrow" if env_width < 1.0 else "Normal/Wide"),
                "Impact": "Amplifies compression" if env_width < 1.0 else "No amplification",
            }
            st.markdown(render_criteria_panel(
                "warning" if env_width < 0.5 else ("watch" if env_width < 1.0 else "safe"),
                panel_data
            ), unsafe_allow_html=True)
        with e3:
            evt_status = "ACTIVE" if env_event else "None"
            st.metric("Event Status", evt_status)
            panel_data = {
                "Active": "Yes" if env_event else "No",
                "Risk Factor": f"{env_event_val:.1f}",
                "Impact": "+5% confidence penalty, may escalate state" if env_event else "No impact",
            }
            st.markdown(render_criteria_panel(
                "warning" if env_event else "safe",
                panel_data
            ), unsafe_allow_html=True)

        env_bd = breakdown.get("environment", {})
        if env_bd.get("verdict") and env_bd["verdict"] != "No adverse environmental conditions.":
            st.warning(f"**Environmental Impact**: {env_bd['verdict']}")

        # ── 6. Charts ─────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown('<p class="section-header">SIGNAL TELEMETRY & ANALYSIS</p>', unsafe_allow_html=True)

        if st.session_state.history and len(st.session_state.history) > 1:
            df = pd.DataFrame(st.session_state.history)

            chart_col1, chart_col2 = st.columns([3, 2])

            with chart_col1:
                # Multi-signal area chart
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    row_heights=[0.6, 0.4],
                    subplot_titles=("Crowd Density & Compression", "Turbulence & Anomaly"),
                )

                fig.add_trace(go.Scatter(
                    x=df["time"], y=df["congestion"],
                    name="Congestion",
                    mode="lines+markers",
                    line=dict(color=CHART_COLORS["congestion"], width=2),
                    marker=dict(size=4),
                    fill="tozeroy",
                    fillcolor="rgba(126,184,218,0.12)",
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=df["time"], y=df["gradient"],
                    name="Gradient",
                    mode="lines",
                    line=dict(color=CHART_COLORS["gradient"], width=1.8, dash="dot"),
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=df["time"], y=df["velocity_var"],
                    name="Velocity Var (CV)",
                    mode="lines+markers",
                    line=dict(color=CHART_COLORS["velocity"], width=1.8),
                    marker=dict(size=3),
                    fill="tozeroy",
                    fillcolor="rgba(168,154,212,0.10)",
                ), row=2, col=1)

                fig.add_trace(go.Scatter(
                    x=df["time"], y=df["anomaly_score"],
                    name="Anomaly Z-Score",
                    mode="lines",
                    line=dict(color=CHART_COLORS["anomaly"], width=1.5, dash="dash"),
                ), row=2, col=1)

                # Anomaly threshold line
                fig.add_hline(y=2.5, line_dash="dot", line_color="rgba(212,122,122,0.5)",
                              annotation_text="Z=2.5", annotation_font_color="#d47a7a",
                              row=2, col=1)

                fig.update_layout(
                    **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
                    height=480,
                    showlegend=True,
                )
                fig.update_yaxes(range=[0, 1.15], row=1, col=1, gridcolor="rgba(226,232,240,0.8)")
                fig.update_yaxes(gridcolor="rgba(226,232,240,0.8)", row=2, col=1)
                fig.update_xaxes(gridcolor="rgba(226,232,240,0.8)")

                st.plotly_chart(fig, use_container_width=True)

            with chart_col2:
                # Risk Score gauge
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=risk_score,
                    title={"text": "Risk Score", "font": {"size": 13, "color": "#64748b"}},
                    number={"font": {"size": 34, "color": "#1e293b"}},
                    gauge={
                        "axis": {"range": [0, 100], "tickcolor": "#cbd5e1", "tickfont": {"color": "#94a3b8"}},
                        "bar": {"color": bar_color, "thickness": 0.65},
                        "bgcolor": "#f8fafc",
                        "bordercolor": "#e2e8f0",
                        "steps": [
                            {"range": [0,  25], "color": "rgba(134,239,172,0.20)"},
                            {"range": [25, 50], "color": "rgba(253,230,138,0.20)"},
                            {"range": [50, 75], "color": "rgba(253,186,116,0.20)"},
                            {"range": [75,100], "color": "rgba(252,165,165,0.20)"},
                        ],
                        "threshold": {
                            "line": {"color": "#fca5a5", "width": 3},
                            "thickness": 0.8,
                            "value": 75,
                        },
                    },
                ))
                fig_gauge.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", color="#64748b"),
                    height=240,
                    margin=dict(l=30, r=30, t=50, b=20),
                )
                st.plotly_chart(fig_gauge, use_container_width=True)

                # State distribution (pie)
                if "state" in df.columns and len(df) > 2:
                    state_counts = df["state"].apply(lambda s: s.split(" (")[0]).value_counts()
                    colors = [STATE_COLORS.get(s, "#64748b") for s in state_counts.index]
                    fig_pie = go.Figure(go.Pie(
                        labels=state_counts.index,
                        values=state_counts.values,
                        marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
                        hole=0.55,
                        textinfo="label+percent",
                        textfont=dict(size=11, color="#374151"),
                    ))
                    fig_pie.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter, sans-serif", color="#64748b"),
                        height=220,
                        margin=dict(l=10, r=10, t=10, b=10),
                        showlegend=False,
                        title=dict(text="State Distribution", font=dict(size=12, color="#64748b")),
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

        else:
            st.info("Collecting initial data points — charts will appear after 2+ samples.")

        # ── 7. Anomaly Feature Breakdown ──────────────────────────────────
        if anomaly_details and anomaly_details.get("per_feature"):
            with st.expander("Anomaly Detection — Per-Feature Breakdown", expanded=False):
                features = anomaly_details["per_feature"]
                if features:
                    feat_df = pd.DataFrame(features)
                    # Create feature radar
                    fig_feat = go.Figure()
                    fig_feat.add_trace(go.Bar(
                        x=[f["feature"] for f in features],
                        y=[f["z_score"] for f in features],
                        marker_color=[
                            "#fca5a5" if f["is_outlier"] else "#a0c4e4" for f in features
                        ],
                        marker_line=dict(color="#ffffff", width=1),
                        text=[f"{f['z_score']:.2f}" for f in features],
                        textposition="outside",
                        textfont=dict(color="#374151", size=11),
                    ))
                    fig_feat.add_hline(y=2.5, line_dash="dot", line_color="rgba(212,122,122,0.6)",
                                       annotation_text="Anomaly Threshold (Z=2.5)",
                                       annotation_font_color="#d47a7a")
                    fig_feat.update_layout(
                        **PLOTLY_LAYOUT,
                        height=250,
                        title=dict(text="Z-Scores per Feature", font=dict(size=13, color="#64748b")),
                        yaxis_title="Z-Score",
                    )
                    st.plotly_chart(fig_feat, use_container_width=True)

                    # Detail table
                    st.dataframe(
                        feat_df[["feature", "value", "mean", "std", "z_score", "is_outlier"]],
                        use_container_width=True,
                        column_config={
                            "feature": "Feature",
                            "value": st.column_config.NumberColumn("Current", format="%.4f"),
                            "mean": st.column_config.NumberColumn("Baseline μ", format="%.4f"),
                            "std": st.column_config.NumberColumn("Baseline σ", format="%.4f"),
                            "z_score": st.column_config.NumberColumn("Z-Score", format="%.4f"),
                            "is_outlier": st.column_config.CheckboxColumn("Outlier?"),
                        },
                    )

        # ── 8. Intervention Plan ──────────────────────────────────────────
        st.markdown("---")
        st.markdown('<p class="section-header">INTERVENTION PLAN</p>', unsafe_allow_html=True)

        plan = recommender.get_recommendations(state)

        plan_header, plan_body = st.columns([1, 3])
        with plan_header:
            level = plan.get("level", "ROUTINE")
            color = plan.get("pastel_bg", "#f0fdf4")
            text_color = plan.get("text_color", "#15803d")
            border_color = plan.get("border_color", "#86efac")
            st.markdown(f"""
            <div style="background:{color};border:1px solid {border_color};border-left:4px solid {border_color};
                        border-radius:8px;padding:20px 16px;text-align:center;">
                <div style="font-size:15px;font-weight:800;color:{text_color};letter-spacing:1px;">{level}</div>
                <div style="font-size:11px;color:#64748b;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Response Level</div>
            </div>
            """, unsafe_allow_html=True)

        with plan_body:
            actions = plan.get("actions", [])
            for action in actions:
                priority = action.get("priority", "Low").lower()
                priority_class = f"priority-{priority}"
                st.markdown(f"""
                <div class="intervention-card {priority_class}">
                    <div class="intervention-action">{action.get('action', '')}</div>
                    <div class="intervention-meta">
                        <span>Priority: <b>{action.get('priority', 'N/A')}</b></span>
                        <span>Owner: <b>{action.get('owner', 'N/A')}</b></span>
                        <span>Outcome: {action.get('outcome', 'N/A')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # ── 9. Location Map ───────────────────────────────────────────────
        st.markdown("---")
        st.markdown('<p class="section-header">MONITORING LOCATION</p>', unsafe_allow_html=True)
        try:
            map_data = pd.DataFrame({"lat": [loc["lat"]], "lon": [loc["lon"]]})
            st.map(map_data, zoom=14)
        except Exception as e:
            st.error(f"Map rendering error: {e}")

        # ── 10. Metric Reference ──────────────────────────────────────────
        with st.expander("Metric Reference Guide", expanded=False):
            ref1, ref2 = st.columns(2)
            with ref1:
                st.markdown("""
**Congestion Level** (0.0 – 1.0)
- Ratio of speed reduction vs. free-flow capacity
- `0.0` = Free movement at expected speed
- `0.5` = Speed halved from free-flow
- `1.0` = Complete gridlock / standstill
- *Source*: TomTom Traffic Flow API

**Compression Gradient** (0.0 – 1.0)
- Weighted combination: 60% current density + 40% rate-of-change
- Slope computed via least-squares linear regression over 60s window
- R² quality metric indicates reliability of trend estimate
- Thresholds: Stable < 0.1 | Compressing < 0.5 | Volatile < 0.8
                """)
            with ref2:
                st.markdown("""
**Velocity Variance — CV** (0.0+)
- Coefficient of Variation = σ(speed) / μ(speed)
- Detects stop-and-go shockwaves that precede crush events
- CV > 0.10: Mild turbulence | > 0.25: Escalation trigger | > 0.40: Severe
- Falls back to raw σ when mean speed approaches zero

**Anomaly Score — Z-Score** (0.0+)
- Maximum per-feature Z-Score across the crowd state vector
- Requires 20+ samples to calibrate baseline statistics
- Z > 2.5 = Statistically significant outlier
- Z > 4.0 = Extreme outlier — investigate immediately
- Features: [density, turbulence, pressure, time_factor]
                """)

    # ── Auto-Refresh ──────────────────────────────────────────────────
    if auto_refresh and st.session_state.is_running:
        time.sleep(refresh_rate)
        st.rerun()
