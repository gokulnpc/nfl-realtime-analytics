"""
NFL Real-Time Analytics Dashboard
Streamlit app with Live Kinesis + Demo Mode
"""

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
import os
import sys
import time
from datetime import datetime

# Page config
st.set_page_config(
    page_title="NFL Real-Time Analytics",
    page_icon="🏈",
    layout="wide"
)

# Load models
@st.cache_resource
def load_models():
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    play_classifier = joblib.load(os.path.join(base_path, "models", "play_classifier.joblib"))
    pressure_predictor = joblib.load(os.path.join(base_path, "models", "pressure_predictor.joblib"))
    return play_classifier, pressure_predictor

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

def get_kinesis_client():
    """Initialize Kinesis client"""
    try:
        import boto3
        client = boto3.client(
            'kinesis',
            region_name='us-east-1',
            aws_access_key_id=st.session_state.get('aws_access_key', ''),
            aws_secret_access_key=st.session_state.get('aws_secret_key', '')
        )
        return client
    except Exception as e:
        return None

def get_kinesis_records(client, stream_name, shard_id='shardId-000000000000'):
    """Fetch records from Kinesis stream"""
    try:
        shard_iterator = client.get_shard_iterator(
            StreamName=stream_name,
            ShardId=shard_id,
            ShardIteratorType='LATEST'
        )['ShardIterator']
        
        response = client.get_records(ShardIterator=shard_iterator, Limit=10)
        records = []
        for record in response['Records']:
            data = json.loads(record['Data'].decode('utf-8'))
            records.append(data)
        return records
    except Exception as e:
        st.error(f"Kinesis error: {e}")
        return []

def calculate_features(play_data):
    """Calculate all features needed for prediction"""
    down = play_data.get('down', 1)
    ydstogo = play_data.get('ydstogo', 10)
    yardline_100 = play_data.get('yardline_100', 75)
    qtr = play_data.get('qtr', 1)
    shotgun = play_data.get('shotgun', 1)
    no_huddle = play_data.get('no_huddle', 0)
    defenders_in_box = play_data.get('defenders_in_box', 6)
    pass_rushers = play_data.get('number_of_pass_rushers', 4)
    posteam_score = play_data.get('posteam_score', 0)
    defteam_score = play_data.get('defteam_score', 0)
    half_seconds = play_data.get('half_seconds_remaining', 900)
    
    score_differential = posteam_score - defteam_score
    wp = max(0.01, min(0.99, 0.5 + (score_differential * 0.02)))
    
    return {
        'down': down, 'ydstogo': ydstogo, 'yardline_100': yardline_100,
        'score_differential': score_differential, 'qtr': qtr,
        'half_seconds_remaining': half_seconds, 'wp': wp,
        'posteam_timeouts_remaining': 3, 'defteam_timeouts_remaining': 3,
        'shotgun': shotgun, 'no_huddle': no_huddle,
        'defenders_in_box': defenders_in_box, 'number_of_pass_rushers': pass_rushers,
        'n_rb': 1, 'n_te': 1, 'n_wr': 3,
        'goal_to_go': 1 if yardline_100 <= ydstogo else 0,
        'short_yardage': 1 if ydstogo <= 3 else 0,
        'long_yardage': 1 if ydstogo >= 8 else 0,
        'red_zone': 1 if yardline_100 <= 20 else 0,
        'late_down': 1 if down >= 3 else 0,
        'two_minute_drill': 1 if half_seconds <= 120 and abs(score_differential) <= 8 else 0,
        'heavy_box': 1 if defenders_in_box >= 7 else 0,
        'light_box': 1 if defenders_in_box <= 5 else 0,
        'extra_rushers': 1 if pass_rushers >= 5 else 0,
        'pass_heavy_situation': 1 if (down >= 3 and ydstogo >= 5) else 0,
        'run_heavy_situation': 1 if (down <= 2 and ydstogo <= 4) else 0,
        'heavy_personnel': 0,
        'spread_personnel': 1 if shotgun else 0,
        'blitz': 1 if pass_rushers >= 5 else 0,
        'obvious_passing': 1 if (down >= 3 and ydstogo >= 7) else 0,
        'late_game': 1 if qtr >= 4 and half_seconds <= 300 else 0,
        'rushers_ratio': pass_rushers / (defenders_in_box + 1)
    }

def predict_play(features, play_classifier):
    """Get play type prediction"""
    features_df = pd.DataFrame([features])[play_classifier['feature_columns']]
    is_pass = play_classifier['model_run_pass'].predict(features_df.values)[0]
    run_pass_proba = play_classifier['model_run_pass'].predict_proba(features_df.values)[0]
    
    if is_pass:
        pass_pred = play_classifier['model_pass_type'].predict(features_df.values)[0]
        predicted_play = play_classifier['le_pass'].classes_[pass_pred]
    else:
        is_outside = play_classifier['model_run_type'].predict(features_df.values)[0]
        predicted_play = 'outside_run' if is_outside else 'inside_run'
    
    return predicted_play, run_pass_proba

def predict_pressure(features, pressure_predictor):
    """Get pressure prediction"""
    pressure_features = {k: features[k] for k in pressure_predictor['feature_columns'] if k in features}
    pressure_df = pd.DataFrame([pressure_features])[pressure_predictor['feature_columns']]
    pressure_prob = pressure_predictor['model'].predict_proba(pressure_df.values)[0][1]
    return pressure_prob

# Load models
try:
    play_classifier, pressure_predictor = load_models()
    models_loaded = True
except Exception as e:
    models_loaded = False
    st.error(f"Error loading models: {e}")

# Title
st.title("🏈 NFL Real-Time Play Analytics")

# Mode selection
st.sidebar.header("📡 Data Source")
mode = st.sidebar.radio("Select Mode", ["🎮 Demo Mode", "🔴 Live Kinesis", "⚙️ Manual Input"])

if mode == "🔴 Live Kinesis":
    st.sidebar.markdown("---")
    st.sidebar.subheader("AWS Credentials")
    aws_access = st.sidebar.text_input("Access Key ID", type="password")
    aws_secret = st.sidebar.text_input("Secret Access Key", type="password")
    stream_name = st.sidebar.text_input("Stream Name", value="nfl-play-stream")
    
    if aws_access and aws_secret:
        st.session_state['aws_access_key'] = aws_access
        st.session_state['aws_secret_key'] = aws_secret

if models_loaded:
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
        
        # Get current play
        current_play = DEMO_PLAYS[st.session_state['demo_index'] % len(DEMO_PLAYS)]
        
        # Display play info
        st.info(f"📍 **Play {st.session_state['demo_index'] + 1}:** {current_play['desc']}")
        
        # Calculate features and predict
        features = calculate_features(current_play)
        predicted_play, run_pass_proba = predict_play(features, play_classifier)
        pressure_prob = predict_pressure(features, pressure_predictor)
        
        # Display predictions
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Play Type Prediction")
            play_labels = {
                'inside_run': '🟤 Inside Run', 'outside_run': '🟠 Outside Run',
                'screen': '🟡 Screen Pass', 'short_pass': '🔵 Short Pass', 'deep_pass': '🟣 Deep Pass'
            }
            st.metric("Predicted Play", play_labels.get(predicted_play, predicted_play))
            
            st.markdown("**Run vs Pass:**")
            col_r, col_p = st.columns(2)
            with col_r:
                st.progress(float(run_pass_proba[0]))
                st.caption(f"Run: {run_pass_proba[0]*100:.1f}%")
            with col_p:
                st.progress(float(run_pass_proba[1]))
                st.caption(f"Pass: {run_pass_proba[1]*100:.1f}%")
        
        with col2:
            st.subheader("💥 Pressure Prediction")
            st.metric("Pressure Probability", f"{pressure_prob*100:.1f}%")
            st.progress(float(pressure_prob))
            
            if pressure_prob < 0.25:
                st.success("🟢 Low Risk")
            elif pressure_prob < 0.40:
                st.warning("🟡 Medium Risk")
            else:
                st.error("🔴 High Risk")
            
            if current_play['number_of_pass_rushers'] >= 5:
                st.error("⚠️ BLITZ! 5+ rushers coming!")
        
        # Situation display
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
        
        # Auto-advance
        if st.session_state['demo_running']:
            time.sleep(speed)
            st.session_state['demo_index'] += 1
            st.rerun()
    
    # ============ LIVE KINESIS MODE ============
    elif mode == "🔴 Live Kinesis":
        st.subheader("🔴 Live Kinesis Stream")
        
        if not st.session_state.get('aws_access_key') or not st.session_state.get('aws_secret_key'):
            st.warning("⚠️ Enter AWS credentials in the sidebar to connect to Kinesis")
        else:
            client = get_kinesis_client()
            if client:
                st.success("✅ Connected to AWS")
                
                if st.button("🔄 Fetch Latest Plays"):
                    records = get_kinesis_records(client, stream_name)
                    if records:
                        for record in records:
                            features = calculate_features(record)
                            predicted_play, run_pass_proba = predict_play(features, play_classifier)
                            pressure_prob = predict_pressure(features, pressure_predictor)
                            
                            with st.container():
                                st.json(record)
                                st.write(f"Prediction: {predicted_play}, Pressure: {pressure_prob*100:.1f}%")
                    else:
                        st.info("No new records in stream")
            else:
                st.error("❌ Failed to connect to AWS")
    
    # ============ MANUAL INPUT MODE ============
    elif mode == "⚙️ Manual Input":
        st.subheader("⚙️ Manual Input Mode")
        
        # Sidebar inputs
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
        
        # Build play data
        play_data = {
            'down': down, 'ydstogo': ydstogo, 'yardline_100': yardline_100,
            'qtr': qtr, 'shotgun': int(shotgun), 'no_huddle': int(no_huddle),
            'defenders_in_box': defenders_in_box, 'number_of_pass_rushers': pass_rushers,
            'posteam_score': team_score, 'defteam_score': opp_score,
            'half_seconds_remaining': 900
        }
        
        features = calculate_features(play_data)
        predicted_play, run_pass_proba = predict_play(features, play_classifier)
        pressure_prob = predict_pressure(features, pressure_predictor)
        
        # Display
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Play Type Prediction")
            play_labels = {
                'inside_run': '🟤 Inside Run', 'outside_run': '🟠 Outside Run',
                'screen': '🟡 Screen Pass', 'short_pass': '🔵 Short Pass', 'deep_pass': '🟣 Deep Pass'
            }
            st.metric("Predicted Play", play_labels.get(predicted_play, predicted_play))
            
            st.markdown("**Run vs Pass:**")
            col_r, col_p = st.columns(2)
            with col_r:
                st.progress(float(run_pass_proba[0]))
                st.caption(f"Run: {run_pass_proba[0]*100:.1f}%")
            with col_p:
                st.progress(float(run_pass_proba[1]))
                st.caption(f"Pass: {run_pass_proba[1]*100:.1f}%")
        
        with col2:
            st.subheader("💥 Pressure Prediction")
            st.metric("Pressure Probability", f"{pressure_prob*100:.1f}%")
            st.progress(float(pressure_prob))
            
            if pressure_prob < 0.25:
                st.success("🟢 Low Risk")
            elif pressure_prob < 0.40:
                st.warning("🟡 Medium Risk")
            else:
                st.error("🔴 High Risk")
            
            if pass_rushers >= 5:
                st.error("⚠️ BLITZ! 5+ rushers coming!")

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
        """)

else:
    st.error("Models not loaded. Please check the models directory.")