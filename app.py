import streamlit as st
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from signals.tomtom import get_signal_provider
from signals.geocoder import TomTomGeocoder
from metrics.compression import CrowdMetrics
from engine.classifier import CrowdClassifier
from interventions.recommender import InterventionRecommender
from utils.config_loader import load_config
from utils.time_helper import get_local_time
from data_layer.vectorizer import CrowdStateVectorizer
from engine.anomaly import AnomalyDetector
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="CPSE | Crowd Psychology State Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for aesthetics and dark mode compatibility
st.markdown("""
<style>
    /* Global Font */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Metric Cards */
    .stMetric {
        background-color: #1E1E24; /* Deep modern dark */
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #3A3A42;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    .stMetric:hover {
        transform: translateY(-2px);
        border-color: #5A5A62;
    }
    
    /* State Box */
    .state-box {
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 25px;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    .stable { background: linear-gradient(135deg, #28a745, #218838); }
    .compressing { background: linear-gradient(135deg, #fd7e14, #d35400); }
    .volatile { background: linear-gradient(135deg, #dc3545, #c82333); }
    .agitated { background: linear-gradient(135deg, #6f42c1, #59359a); }
    .fragmenting { background: linear-gradient(135deg, #20c997, #138496); }
    
    /* Metric Typography */
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 32px !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #A0A0A8 !important; 
        font-size: 14px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Recommendations */
    .rec-box {
        background-color: #2D2D35;
        border-left: 5px solid #FFC107;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Application State Initialization
if 'history' not in st.session_state:
    st.session_state.history = []
if 'metrics' not in st.session_state:
    st.session_state.metrics = CrowdMetrics()
if 'anomaly_detector' not in st.session_state:
    st.session_state.anomaly_detector = AnomalyDetector()
if 'vectorizer' not in st.session_state:
    st.session_state.vectorizer = CrowdStateVectorizer()
if 'location' not in st.session_state:
    config = load_config()
    st.session_state.location = config.get('location', {})
    if 'name' not in st.session_state.location:
        st.session_state.location['name'] = "Default Location"
if 'is_running' not in st.session_state:
    st.session_state.is_running = False

# Load modules
signal_provider = get_signal_provider()
geocoder = TomTomGeocoder()
classifier = CrowdClassifier()
recommender = InterventionRecommender()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧠 CPSE Control")
    st.markdown("---")
    
    st.subheader("📍 Location Monitor")
    current_loc_name = st.session_state.location.get('name', 'Unknown')
    st.info(f"Currently Monitoring:\n**{current_loc_name}**")
    
    # Search functionality
    search_query = st.text_input("Change Location", placeholder="e.g. Times Square")
    if st.button("Search"):
        if search_query:
            results = geocoder.search(search_query)
            if results:
                st.session_state.search_results = results
                st.success(f"Found {len(results)} matches.")
            else:
                st.error("No results found.")
    
    if 'search_results' in st.session_state:
        options = {f"{i+1}. {r['name']}": r for i, r in enumerate(st.session_state.search_results)}
        selected_option = st.selectbox("Select Result", list(options.keys()))
        
        if st.button("Update Monitor"):
            sel = options[selected_option]
            new_loc = {'lat': sel['lat'], 'lon': sel['lon'], 'name': sel['name']}
            
            # Only reset if location changes
            current = st.session_state.location
            if current.get('lat') != new_loc['lat'] or current.get('lon') != new_loc['lon']:
                st.session_state.history = []
                st.session_state.metrics = CrowdMetrics()
                st.session_state.anomaly_detector = AnomalyDetector() # Explicit reset
            
            st.session_state.location = new_loc
            del st.session_state.search_results
            st.rerun()

    st.markdown("---")
    st.subheader("⚙️ Settings")
    
    # Analysis Control
    if st.session_state.is_running:
        if st.button("⏹ Stop Analysis", type="primary"):
            st.session_state.is_running = False
            st.rerun()
    else:
        if st.button("▶ Start Analysis", type="primary"):
            st.session_state.is_running = True
            st.rerun()

    # Refresh Logic
    auto_refresh = st.checkbox("Live Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Rate (s)", 10, 300, 30)


    # Scenario Controls (Environmental Logic)
    with st.expander("🌍 Scenario Conditions"):
        st.caption("Adjust hyper-local environmental factors.")
        
        # Weather Integration
        from signals.weather import OpenWeatherMapSignal
        weather_provider = OpenWeatherMapSignal()
        
        use_live_weather = False
        weather_risk_live = None
        weather_cond = "Unknown"
        
        # Check if API Key available without exposing it
        
        if weather_provider.api_key:
             use_live_weather = st.checkbox("Use Live Weather (OpenWeatherMap)", value=True)
        else:
             st.warning("Set OPENWEATHERMAP_API_KEY to enable live weather.")
             # Fallback to verify if it's in os.environ but maybe empty
             if "OPENWEATHERMAP_API_KEY" in os.environ:
                 st.error("Key found in env but might be empty.")
        
        if use_live_weather:
             # Fetch once or on refresh? 
             # For performance, maybe fetch inside the main loop but control here?
             # Actually, fetching here is fine as sidebar reruns on reload
             # But better to fetch in main loop to sync with location updates.
             pass 

        # Manual Controls (Always available as fallback or override)
        if not use_live_weather:
            env_weather = st.select_slider("Weather Cond (Manual)", options=["Clear", "Rain", "Storm"], value="Clear")
            weather_map = {"Clear": 0.0, "Rain": 0.5, "Storm": 1.0}
            env_weather_val = weather_map[env_weather]
        else:
             # Fetch now
             loc = st.session_state.location
             w_risk, w_cond, _ = weather_provider.fetch_weather_risk(loc['lat'], loc['lon'])
             if w_risk is not None:
                 env_weather_val = w_risk
                 weather_cond = w_cond
                 st.success(f"Live: {w_cond} (Risk: {w_risk})")
             else:
                 st.error("Weather fetch failed. Using manual.")
                 env_weather = st.select_slider("Weather Cond (Fallback)", options=["Clear", "Rain", "Storm"], value="Clear")
                 weather_map = {"Clear": 0.0, "Rain": 0.5, "Storm": 1.0}
                 env_weather_val = weather_map[env_weather]

        env_width = st.slider("Passage Width", 0.1, 2.0, 1.0, help="< 1.0 = Bottlenecks (Alleys), > 1.0 = Open Plazas")
        env_event = st.checkbox("Active Event/Protest", value=False)
        env_event_val = 1.0 if env_event else 0.0

    # About
    with st.expander("ℹ️ Project Info"):
        st.markdown("""
        **CPSE (Crowd Psychology State Engine)**
        
        Real-time crowd dynamics classification.
        - **Signals**: TomTom Traffic API
        - **Privacy**: No PII collected.
        - **Anomaly**: Statistical profiling (Z-Score).
        """)

# --- MAIN CONTENT ---
# Use a single container for the main loop to prevent "ghosting" artifacts
main_container = st.empty()

with main_container.container():
    st.title("Crowd Psychology State Engine")
    st.markdown("Real-time crowd dynamics classification and intervention system.")
    
    # Ensure provider has current location
    loc = st.session_state.location
    signal_provider.set_location(loc['lat'], loc['lon'], loc.get('name', 'Unknown'))
    
    if not st.session_state.is_running:
        st.info("Analysis stopped. Click 'Start Analysis' in the sidebar to begin monitoring.")
        # Initialize placeholder values for UI when stopped
        congestion = 0.0
        current_speed = 0.0
        gradient = 0.0
        velocity_var = 0.0
        anomaly_score = 0.0
        state = "Stable"
        confidence = 0.0
        local_time = get_local_time(loc['lat'], loc['lon'])
    else:
        # Fetch Data (Telemetry)
        with st.spinner('Syncing with live signals...'):
            telemetry = signal_provider.fetch_telemetry()
            congestion = telemetry['congestion']
            current_speed = telemetry['current_speed']
            
            # Update metrics (pass speed too)
            metrics = st.session_state.metrics
            metrics.update(congestion, current_speed)
            
            gradient = metrics.compute_compression_gradient()
            velocity_var = metrics.compute_velocity_variance()
        
            # --- Phase 2: Vectorization & Anomaly ---
            # Access session state instances
            vectorizer = st.session_state.vectorizer
            anomaly_detector = st.session_state.anomaly_detector
        
            # Create vectors (incorporating environment from sidebar)
            crowd_vector = vectorizer.create_state_vector(congestion, velocity_var, gradient)
            
            # OPTIONAL: usage of env vector in future logic
            env_vector = vectorizer.create_environmental_vector(env_width, env_weather_val, env_event_val)
            
            # Detect Anomaly
            is_anomaly, anomaly_score = anomaly_detector.update_and_detect(crowd_vector)
            
            # Classify with Anomaly Awareness
            state, confidence = classifier.classify(gradient, velocity_var, anomaly_score)
            
            # Local Time
            local_time = get_local_time(loc['lat'], loc['lon'])
            
            # Store History
            st.session_state.history.append({
                "time": local_time,
                "congestion": congestion,
                "gradient": gradient,
                "velocity_var": velocity_var, 
                "anomaly_score": anomaly_score,
                "state": state
            })
            if len(st.session_state.history) > 50:
                st.session_state.history.pop(0)
    
    # --- DASHBOARD LAYOUT ---
    
    # 1. State Banner (Redesigned)
    valid_states = {"stable", "compressing", "volatile", "agitated", "fragmenting"}
    base_state = state.split(" (")[0].lower()
    if base_state not in valid_states: base_state = "stable"
    
    safe_state_display = state.upper() 
    st.markdown(f'<div class="state-box {base_state}">STATE: {safe_state_display} | CONFIDENCE: {int(confidence*100)}%</div>', unsafe_allow_html=True)
    
    # 2. KPI Metrics (Enriched with Calculations)
    st.subheader("📊 Crowd Dynamics Metrics")
    
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    with m_col1:
        st.metric("Congestion Level", f"{congestion:.2f}")
        st.caption("**Formula**: `1.0 - (CurrentSpeed / FreeFlow)`")
        st.caption("*Source: TomTom Traffic API*")
        
    with m_col2:
        st.metric("Compression Gradient", f"{gradient:.2f}", delta_color="inverse")
        st.caption("**Formula**: `Rate of density change (d/dt)`")
        st.caption("*High +Value = Rapid Compression Risk*")
        
    with m_col3:
        st.metric("Velocity Variance", f"{velocity_var:.2f}")
        st.caption("**Formula**: `Variance(Speed History)`")
        st.caption("*High Variance = Turbulence/Shockwaves*")
        
    with m_col4:
        delta_val = "Normal" if anomaly_score < 2.5 else "Unusual"
        delta_color = "normal" if anomaly_score < 2.5 else "inverse"
        st.metric("Anomaly Score", f"{anomaly_score:.2f}", delta=delta_val, delta_color=delta_color)
        st.caption("**Formula**: `Z-Score = (X - Mean) / StdDev`")
        st.caption("*Deviations > 2.5 are statistical anomalies.*")

    # 3. Weather & Environment (New)
    st.markdown("---")
    env_col1, env_col2 = st.columns(2)
    with env_col1:
        st.subheader("🌤️ Environmental Context")
        if use_live_weather and weather_cond:
             st.info(f"**Live Weather**: {weather_cond} (Risk Factor: {env_weather_val:.2f})")
        else:
             st.info(f"**Manual Weather**: {env_weather} (Risk Factor: {env_weather_val:.2f})")
             
    with env_col2:
         st.subheader("⚡ Event Context")
         evt_status = "Active Event" if env_event else "No Known Event"
         st.metric("Event Risk", f"{env_event_val:.1f}", delta=evt_status, delta_color="off")


    # 4. Charts & Recommendations
    st.markdown("---")
    row3_col1, row3_col2 = st.columns([2, 1])
    
    with row3_col1:
        st.subheader("📈 Live Signal Telemetry")
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            fig = px.line(df, x="time", y=["congestion", "gradient", "velocity_var"], markers=True, height=350)
            fig.update_layout(yaxis_range=[0, 1.2])
            st.plotly_chart(fig, width="stretch")  
        else:
            st.info("Gathering initial data points...")
    
        # Map View
        st.subheader("🗺️ Location Map")
        map_data = pd.DataFrame({'lat': [loc['lat']], 'lon': [loc['lon']]})
        st.map(map_data, zoom=14)
    
    with row3_col2:
        st.subheader("🛡️ Intervention Plan")
        actions = recommender.get_recommendations(state)
        
        if not actions or actions == ["No specific recommendations."]:
             st.markdown("""
             <div class="rec-box" style="border-left-color: #28a745;">
                ✅ <b>No Active Threats</b><br>
                Monitor standard protocols.
             </div>
             """, unsafe_allow_html=True)
        else:
            for action in actions:
                st.markdown(f"""
                <div class="rec-box">
                   👉 {action}
                </div>
                """, unsafe_allow_html=True)
            
        with st.expander("📚 Metric Reference Guide"):
            st.markdown("""
            **Congestion (0.0 - 1.0)**
            - Represents crowd/traffic density.
            - `0.0`: Free movement.
            - `1.0`: Gridlock/Standstill.
            
            **Compression Gradient**
            - How fast density is rising.
            - Sudden spikes indicate inflow surges.
            
            **Velocity Variance**
            - Measures turbulence (stop-and-go waves).
            - High variance often precedes panic or crush.
            
            **Anomaly Score (Z-Score)**
            - Statistical deviation from the "Normal" baseline.
            - Requires ~20 data points (1-2 mins) to calibrate.
            """)

# Auto-Refresh Logic
if auto_refresh and st.session_state.is_running:
    time.sleep(refresh_rate)
    st.rerun()
