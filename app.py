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
from data_layer.database import get_db_client
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

# --- AUTHENTICATION ---
def check_password():
    """Returns `True` if the user had a correct password."""
    
    # Check if password is set in secrets, otherwise default to empty
    # In Streamlit Cloud, set "APP_PASSWORD" in secrets.toml
    # Supports single string or list of strings
    valid_passwords = ["cpseisawesome"]
    
    try:
        if "APP_PASSWORD" in st.secrets:
            secret_val = st.secrets["APP_PASSWORD"]
            if isinstance(secret_val, list):
                valid_passwords = secret_val
            else:
                valid_passwords = [str(secret_val)]
    except Exception:
        # Secrets file missing or invalid, fall back to environment variables
        pass
        
    # Fallback to Environment Variable (for local dev without secrets.toml)
    if not valid_passwords:
        if "APP_PASSWORD" in os.environ:
            valid_passwords = [os.environ["APP_PASSWORD"]]
        else:
            # Final fallback to default for local ease of use
            valid_passwords = ["cpseisawesome"]
        
    if not valid_passwords:
        st.error("⚠️ Configuration Error: `APP_PASSWORD` is not set. Please configure it in `.streamlit/secrets.toml` or your environment variables.")
        st.stop()

    import secrets
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        user_pass = st.session_state["password"]
        correct = False
        for valid_pass in valid_passwords:
            # Use constant-time comparison to prevent timing attacks
            if secrets.compare_digest(user_pass, valid_pass):
                correct = True
                break
                
        if correct:
            st.session_state["password_correct"] = True
            # Check if it was the Admin password (the first one in the list)
            # We re-verify to set the flag
            if secrets.compare_digest(user_pass, valid_passwords[0]):
                st.session_state["is_admin"] = True
            else:
                st.session_state["is_admin"] = False
                
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input
        st.text_input(
            "Please enter the application password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.text_input(
            "Please enter the application password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()

# --- SERVICE INITIALIZATION (PER SESSION) ---
# Initialize services in session_state to ensure isolation between users
if 'services' not in st.session_state:
    st.session_state.services = {
        'signal_provider': get_signal_provider(),
        'geocoder': TomTomGeocoder(),
        'classifier': CrowdClassifier(),
        'recommender': InterventionRecommender(),
        'db': get_db_client()
    }

# Access services from session state
signal_provider = st.session_state.services['signal_provider']
geocoder = st.session_state.services['geocoder']
classifier = st.session_state.services['classifier']
recommender = st.session_state.services['recommender']

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

# --- VIEW CONTROLLER ---
view_mode = "Live Monitor"

# Only show toggle if Admin
if st.session_state.get("is_admin", False):
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛡️ Admin Console")
    view_mode = st.sidebar.radio("View Mode", ["Live Monitor", "Database Records"])

# --- MAIN CONTENT ---
# Use a single container for the main loop to prevent "ghosting" artifacts
main_container = st.empty()

if view_mode == "Database Records":
    with main_container.container():
        st.title("🗄️ Database Records")
        
        db = st.session_state.services.get('db')
        if db:
            # 1. Fetch Unique Locations for Dropdown
            location_options = ["All"]
            unique_locs = db.fetch_unique_locations()
            if unique_locs:
                location_options.extend(unique_locs)

            # 2. KPI Cards (Global or Initial)
            # We'll calculate KPIs AFTER filtering, so we need to move filters UP or do a two-pass?
            # User asked for: "Add filter options right below 'Total Records'"
            # This implies: KPI -> (Line Break) -> Filters -> Table/Charts?
            # Or Filters -> KPIs?
            # Standard pattern: Filters -> KPIs -> Data
            # If user wants filters BELOW "Total Records" (KPI), they want:
            # [KPIs]
            # [Filters]
            # [Data]
            
            # Let's do:
            # 1. Filters
            # 2. Query
            # 3. KPIs
            # 4. Data
            # This makes the most sense flow-wise, even if user said "below".
            # If I put filters below KPIs, the KPIs would show stale/global data before the filter applies?
            # Or maybe they want to see "Total Records in DB" vs "Filtered Records"?
            # Let's stick to Filters at top for usability, or maybe columns.
            
            # Actually, let's look at the user request accurately: "Add filter options right below 'Total Records'"
            # Maybe they mean the filters should be part of the dashboard body, not sidebar.
            
            # Let's try a layout:
            # Row 1: Filters (Cols)
            # Row 2: KPIs
            # Row 3: Charts/Table
            
            # 1. KPI Placeholder (Top)
            kpi_container = st.container()
            
            # 2. Filters (Middle)
            st.markdown("### 🔍 Query Filters")
            
            # Fetch Unique Locations for Dropdown
            location_options = ["All"]
            unique_locs = None
            if db:
                unique_locs = db.fetch_unique_locations()
                if unique_locs:
                    location_options.extend(unique_locs)
            
            f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1, 1, 1])
            with f_col1:
                # Key ensures state retention
                db_location = st.selectbox("Location", location_options, key="filter_loc")
            with f_col2:
                db_limit = st.slider("Limit", 50, 500, 100, step=50, key="filter_lim")
            with f_col3:
                st.write("") 
                st.write("")
                db_anomaly = st.checkbox("Anomalies Only", key="filter_anom")
            with f_col4:
                st.write("") 
                st.write("")
                if st.button("Refresh", type="primary"):
                     st.rerun()

            st.markdown("---")

            with st.spinner("Querying Supabase..."):
                # Fetch with filters
                data = db.fetch_filtered_logs(
                    limit=db_limit, 
                    location=db_location, 
                    anomaly_only=db_anomaly
                )
                
                if data:
                    df = pd.DataFrame(data)
                    
                    # Populate KPI Container (Visually Top)
                    with kpi_container:
                        kpi1, kpi2, kpi3 = st.columns(3)
                        kpi1.metric("Total Records", len(df))
                        
                        avg_cong = df['congestion'].mean() if 'congestion' in df.columns else 0
                        kpi2.metric("Avg Congestion", f"{avg_cong:.2f}")
                        
                        anomalies = df[df['anomaly_score'] > 2.5] if 'anomaly_score' in df.columns else pd.DataFrame()
                        kpi3.metric("Anomalies Found", len(anomalies))
                        st.markdown("---") # Separator below KPIs
                    
                    # Charts (Conditional)
                    if db_location != "All":
                        st.subheader(f"📈 Congestion Trend: {db_location}")
                        if 'created_at' in df.columns and 'congestion' in df.columns:
                            chart_df = df.sort_values('created_at')
                            st.line_chart(chart_df, x='created_at', y='congestion')
                    else:
                        st.caption("ℹ️ Select a specific location to view trend charts.")
                    
                    # Data Table
                    st.subheader("📋 Detailed Logs")
                    st.dataframe(
                        df, 
                        # Removed use_container_width to avoid deprecation warning
                        # Default is usually responsive enough or fixed width
                        column_config={
                            "created_at": st.column_config.DatetimeColumn("Timestamp", format="D MMM, HH:mm:ss"),
                            "congestion": st.column_config.ProgressColumn("Congestion", min_value=0, max_value=1),
                            "anomaly_score": st.column_config.NumberColumn("Anomaly Score", format="%.2f"),
                            "is_simulated": st.column_config.CheckboxColumn("Simulated")
                        }
                    )
                    
                    # CSV Download
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download CSV",
                        csv,
                        "crowd_telemetry_dump.csv",
                        "text/csv",
                        key='download-csv'
                    )
                else:
                    st.info("No records found matching current filters.")
        else:
            st.error("Database service not initialized.")

else:
    # Existing Live Monitor logic...
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
                
                # Unpack tuple: (gradient, quality)
                gradient, gradient_quality = metrics.compute_compression_gradient()
                velocity_var = metrics.compute_velocity_variance()

                # --- Phase 2: Vectorization & Anomaly ---
                # Access session state instances
                vectorizer = st.session_state.vectorizer
                anomaly_detector = st.session_state.anomaly_detector
                
                # Check for simulation flag
                is_simulated = telemetry.get("is_simulated", False)
                if is_simulated:
                    st.toast("⚠️ Using Simulated Data", icon="⚠️")
            
                # Create vectors (incorporating environment from sidebar)
                crowd_vector = vectorizer.create_state_vector(congestion, velocity_var, gradient)
                
                # OPTIONAL: usage of env vector in future logic
                env_vector = vectorizer.create_environmental_vector(env_width, env_weather_val, env_event_val)
                
                # Detect Anomaly
                is_anomaly, anomaly_score = anomaly_detector.update_and_detect(crowd_vector)
                
                # Classify with Anomaly Awareness
                history_len = len(metrics.congestion_history)
                state, confidence = classifier.classify(
                    gradient, 
                    velocity_var, 
                    anomaly_score,
                    is_simulated=is_simulated,
                    history_len=history_len,
                    gradient_quality=gradient_quality
                )
                
                # Local Time
                local_time = get_local_time(loc['lat'], loc['lon'])
                
                # Store History (In-Memory for UI responsiveness)
                telemetry_record = {
                    "time": local_time,
                    "congestion": congestion,
                    "gradient": gradient,
                    "velocity_var": velocity_var, 
                    "anomaly_score": anomaly_score,
                    "state": state
                }
                st.session_state.history.append(telemetry_record)
                if len(st.session_state.history) > 50:
                    st.session_state.history.pop(0)
    
                # Persist to Supabase (Background-ish)
                # Add extra fields needed for DB
                db_record = telemetry_record.copy()
                db_record.update({
                    "location_name": loc.get('name', 'Unknown'),
                    "lat": loc['lat'],
                    "lon": loc['lon'],
                    "speed": current_speed
                })
                st.session_state.services['db'].insert_telemetry(db_record)
        
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
            # Inverse: Green if low (Normal), Red if high (Unusual)
            delta_color = "normal" if anomaly_score < 2.5 else "inverse" 
            st.metric("Anomaly Score", f"{anomaly_score:.2f}", delta=delta_val, delta_color="inverse")
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
            try:
                map_data = pd.DataFrame({'lat': [loc['lat']], 'lon': [loc['lon']]})
                st.map(map_data, zoom=14)
            except Exception as e:
                st.error(f"Map Error: {e}")
        
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

    # Auto-Refresh Logic (Only in Live Mode)
    if auto_refresh and st.session_state.is_running:
        time.sleep(refresh_rate)
        st.rerun()
