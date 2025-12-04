"""
NFL Real-Time Analytics Dashboard
Streamlit app with API integration
"""

import streamlit as st
import requests
import time

# Page config
st.set_page_config(
    page_title="NFL Real-Time Analytics",
    page_icon="🏈",
    layout="wide"
)

# API Base URL
API_URL = "http://127.0.0.1:8000"

# Sample plays for demo mode
DEMO_PLAYS = [
    {"down": 1, "ydstogo": 10, "yardline_100": 75, "qtr": 1, "shotgun": 1, "defenders_in_box": 6, "number_of_pass_rushers": 4, "posteam_score": 0, "defteam_score": 0, "desc": "1st & 10 at own 25 - Opening drive"},
    {"down": 2, "ydstogo": 3, "yardline_100": 68, "qtr": 1, "shotgun": 0, "defenders_in_box": 7, "number_of_pass_rushers": 4, "posteam_score": 0, "defteam_score": 0, "desc": "2nd & 3 at own 32 - Short yardage"},
    {"down": 1, "ydstogo": 10, "yardline_100": 55, "qtr": 1, "shotgun": 1, "defenders_in_box": 6, "number_of_pass_rushers": 4, "posteam_score": 0, "defteam_score": 0, "desc": "1st & 10 at midfield"},
    {"down": 3, "ydstogo": 8, "yardline_100": 45, "qtr": 1, "shotgun": 1, "defenders_in_box": 5, "number_of_pass_rushers": 5, "posteam_score": 0, "defteam_score": 0, "desc": "3rd & 8 - Passing situation, BLITZ!"},
    {"down": 1, "ydstogo": 10, "yardline_100": 25, "qtr": 2, "shotgun": 1, "defenders_in_box": 6, "number_of_pass_rushers": 4, "posteam_score": 0, "defteam_score": 0, "desc": "1st & 10 - Red Zone!"},
    {"down": 2, "ydstogo": 6, "yardline_100": 18, "qtr": 2, "shotgun": 1, "defenders_in_box": 6, "number_of_pass_rushers": 4, "posteam_score": 0, "defteam_score": 0, "desc": "2nd & 6 at the 18"},
    {"down": 3, "ydstogo": 3, "yardline_100": 8, "qtr": 2, "shotgun": 0, "defenders_in_box": 8, "number_of_pass_rushers": 4, "posteam_score": 0, "defteam_score": 0, "desc": "3rd & 3 - Goal line, heavy box!"},
    {"down": 1, "ydstogo": 10, "yardline_100": 80, "qtr": 3, "shotgun": 1, "defenders_in_box": 6, "number_of_pass_rushers": 4, "posteam_score": 7, "defteam_score": 3, "desc": "1st & 10 - Leading by 4"},
    {"down": 3, "ydstogo": 15, "yardline_100": 65, "qtr": 4, "shotgun": 1, "defenders_in_box": 5, "number_of_pass_rushers": 6, "posteam_score": 14, "defteam_score": 17, "desc": "3rd & 15 - Trailing, heavy blitz!"},
    {"down": 1, "ydstogo": 10, "yardline_100": 40, "qtr": 4, "shotgun": 1, "defenders_in_box": 6, "number_of_pass_rushers": 4, "posteam_score": 21, "defteam_score": 17, "desc": "1st & 10 - 2 minute drill, leading by 4"},
]

def check_api_health():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        return response.json()
    except:
        return None

def get_prediction(play_data):
    """Get prediction from API"""
    try:
        response = requests.post(f"{API_URL}/predict", json=play_data, timeout=5)
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def get_kinesis_status():
    """Get Kinesis connection status"""
    try:
        response = requests.get(f"{API_URL}/kinesis/status", timeout=5)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def fetch_kinesis_records():
    """Fetch records from Kinesis"""
    try:
        response = requests.get(f"{API_URL}/kinesis/fetch", timeout=10)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def display_prediction(prediction, play_data=None):
    """Display prediction results"""
    col1, col2 = st.columns(2)
    
    play_labels = {
        'inside_run': '🟤 Inside Run', 'outside_run': '🟠 Outside Run',
        'screen': '🟡 Screen Pass', 'short_pass': '🔵 Short Pass', 'deep_pass': '🟣 Deep Pass'
    }
    
    with col1:
        st.subheader("🎯 Play Type Prediction")
        predicted = prediction.get('predicted_play', 'unknown')
        st.metric("Predicted Play", play_labels.get(predicted, predicted))
        
        st.markdown("**Run vs Pass:**")
        col_r, col_p = st.columns(2)
        with col_r:
            run_prob = prediction.get('run_probability', 0)
            st.progress(float(run_prob))
            st.caption(f"Run: {run_prob*100:.1f}%")
        with col_p:
            pass_prob = prediction.get('pass_probability', 0)
            st.progress(float(pass_prob))
            st.caption(f"Pass: {pass_prob*100:.1f}%")
    
    with col2:
        st.subheader("💥 Pressure Prediction")
        pressure_prob = prediction.get('pressure_probability', 0)
        st.metric("Pressure Probability", f"{pressure_prob*100:.1f}%")
        st.progress(float(pressure_prob))
        
        risk = prediction.get('risk_level', 'medium')
        if risk == "low":
            st.success("🟢 Low Risk")
        elif risk == "medium":
            st.warning("🟡 Medium Risk")
        else:
            st.error("🔴 High Risk")
        
        if play_data and play_data.get('number_of_pass_rushers', 0) >= 5:
            st.error("⚠️ BLITZ! 5+ rushers coming!")

# Title
st.title("🏈 NFL Real-Time Play Analytics")

# Check API health
api_health = check_api_health()
if api_health:
    models_status = "✓" if api_health.get('models_loaded') else "✗"
    kinesis_status = "✓" if api_health.get('kinesis_configured') else "✗"
    st.sidebar.success(f"✅ API Connected | Models: {models_status} | Kinesis: {kinesis_status}")
else:
    st.sidebar.error("❌ API Offline")
    st.error("API is not running. Start it with: `python3 -m uvicorn src.api.main:app --reload --port 8000`")
    st.stop()

# Mode selection
st.sidebar.header("📡 Data Source")
mode = st.sidebar.radio("Select Mode", ["🎮 Demo Mode", "🔴 Live Kinesis", "⚙️ Manual Input"])

st.markdown("---")

# ============ DEMO MODE ============
if mode == "🎮 Demo Mode":
    st.subheader("🎮 Demo Mode - Simulated Game")
    
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 2])
    with col_ctrl1:
        if st.button("▶️ Start/Resume"):
            st.session_state['demo_running'] = True
    with col_ctrl2:
        if st.button("⏸️ Pause"):
            st.session_state['demo_running'] = False
    with col_ctrl3:
        speed = st.slider("Speed (seconds per play)", 1, 5, 3)
    
    if 'demo_index' not in st.session_state:
        st.session_state['demo_index'] = 0
    if 'demo_running' not in st.session_state:
        st.session_state['demo_running'] = False
    
    current_play = DEMO_PLAYS[st.session_state['demo_index'] % len(DEMO_PLAYS)]
    st.info(f"📍 **Play {st.session_state['demo_index'] + 1}:** {current_play['desc']}")
    
    prediction = get_prediction(current_play)
    
    if prediction:
        display_prediction(prediction, current_play)
        
        st.markdown("---")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            st.metric("Down & Distance", f"{current_play['down']} & {current_play['ydstogo']}")
        with col_s2:
            st.metric("Yard Line", f"{100 - current_play['yardline_100']}")
        with col_s3:
            st.metric("Quarter", current_play['qtr'])
        with col_s4:
            score_diff = current_play['posteam_score'] - current_play['defteam_score']
            st.metric("Score", f"{current_play['posteam_score']}-{current_play['defteam_score']}", delta=f"{score_diff:+d}")
    
    if st.session_state['demo_running']:
        time.sleep(speed)
        st.session_state['demo_index'] += 1
        st.rerun()

# ============ LIVE KINESIS MODE ============
elif mode == "🔴 Live Kinesis":
    st.subheader("🔴 Live Kinesis Stream")
    
    # Check Kinesis status
    kinesis_info = get_kinesis_status()
    
    if kinesis_info.get('status') == 'connected':
        st.success(f"✅ Connected to stream: **{kinesis_info.get('stream_name')}**")
        st.caption(f"Shards: {kinesis_info.get('shard_count')} | Status: {kinesis_info.get('stream_status')}")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            auto_refresh = st.checkbox("🔄 Auto-refresh (5s)")
        
        with col_btn2:
            if st.button("📥 Fetch Latest Plays"):
                st.session_state['fetch_kinesis'] = True
        
        if st.session_state.get('fetch_kinesis') or auto_refresh:
            with st.spinner("Fetching from Kinesis..."):
                result = fetch_kinesis_records()
            
            if result.get('status') == 'success':
                records = result.get('records', [])
                predictions = result.get('predictions', [])
                
                if records:
                    st.success(f"Found {len(records)} records")
                    for i, (record, pred) in enumerate(zip(records, predictions)):
                        with st.expander(f"Play {i+1}"):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.json(record)
                            with col_b:
                                display_prediction(pred, record)
                else:
                    st.info("No new records in stream. Try sending some test data!")
            else:
                st.warning(f"Fetch issue: {result.get('message', 'Unknown error')}")
            
            st.session_state['fetch_kinesis'] = False
            
            if auto_refresh:
                time.sleep(5)
                st.rerun()
    
    elif kinesis_info.get('status') == 'not_configured':
        st.warning("⚠️ Kinesis not configured. Add AWS credentials to `.env` file in the project root.")
        st.code("""
# .env file
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
KINESIS_STREAM_NAME=nfl-play-stream
        """)
    else:
        st.error(f"❌ Kinesis error: {kinesis_info.get('message', 'Unknown error')}")

# ============ MANUAL INPUT MODE ============
elif mode == "⚙️ Manual Input":
    st.subheader("⚙️ Manual Input Mode")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Game Situation")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        down = st.selectbox("Down", [1, 2, 3, 4])
        qtr = st.selectbox("Quarter", [1, 2, 3, 4])
    with col2:
        ydstogo = st.number_input("Yards to Go", 1, 99, 10)
        yardline_100 = st.number_input("Yard Line", 1, 99, 75)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Score")
    col3, col4 = st.sidebar.columns(2)
    with col3:
        team_score = st.number_input("Your Team", 0, 99, 14)
    with col4:
        opp_score = st.number_input("Opponent", 0, 99, 10)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Formation")
    shotgun = st.sidebar.checkbox("Shotgun", True)
    no_huddle = st.sidebar.checkbox("No Huddle", False)
    
    col5, col6 = st.sidebar.columns(2)
    with col5:
        defenders_in_box = st.number_input("Defenders in Box", 3, 9, 6)
    with col6:
        pass_rushers = st.number_input("Pass Rushers", 2, 8, 4)
    
    play_data = {
        'down': down, 'ydstogo': ydstogo, 'yardline_100': yardline_100,
        'qtr': qtr, 'shotgun': int(shotgun), 'no_huddle': int(no_huddle),
        'defenders_in_box': defenders_in_box, 'number_of_pass_rushers': pass_rushers,
        'posteam_score': team_score, 'defteam_score': opp_score,
        'half_seconds_remaining': 900
    }
    
    prediction = get_prediction(play_data)
    
    if prediction:
        display_prediction(prediction, play_data)

# Model info
st.markdown("---")
with st.expander("ℹ️ Model Information"):
    st.markdown("""
    **Play Classifier (5-class Hierarchical):**
    - Stage 1: Run vs Pass (99.6% accuracy)
    - Stage 2a: Inside vs Outside Run (56.9% accuracy)  
    - Stage 2b: Screen vs Short vs Deep Pass (74.8% accuracy)
    - Combined 5-class accuracy: 68.8%
    
    **Pressure Predictor:**
    - AUC-ROC: 61.1%
    - Key features: Blitz indicator, pass rushers, obvious passing situations
    
    **Training Data:** 9 NFL seasons (2016-2024), ~302K plays
    
    **API Endpoints:**
    - `GET /health` - API health check
    - `POST /predict` - Get predictions
    - `GET /kinesis/status` - Kinesis connection status
    - `GET /kinesis/fetch` - Fetch live plays
    """)