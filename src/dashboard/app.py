"""
NFL Real-Time Analytics Dashboard
Streamlit app for play prediction and pressure analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

try:
    play_classifier, pressure_predictor = load_models()
    models_loaded = True
except Exception as e:
    models_loaded = False
    st.error(f"Error loading models: {e}")

# Title
st.title("🏈 NFL Real-Time Play Analytics")
st.markdown("Predict play types and QB pressure probability in real-time")

# Sidebar - Game Situation Input
st.sidebar.header("⚙️ Game Situation")

col1, col2 = st.sidebar.columns(2)
with col1:
    down = st.selectbox("Down", [1, 2, 3, 4], index=0)
    qtr = st.selectbox("Quarter", [1, 2, 3, 4], index=0)
with col2:
    ydstogo = st.number_input("Yards to Go", min_value=1, max_value=99, value=10)
    yardline_100 = st.number_input("Yard Line", min_value=1, max_value=99, value=75)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Score")
col3, col4 = st.sidebar.columns(2)
with col3:
    team_score = st.number_input("Your Team", min_value=0, max_value=99, value=14)
with col4:
    opp_score = st.number_input("Opponent", min_value=0, max_value=99, value=10)

score_differential = team_score - opp_score

st.sidebar.markdown("---")
st.sidebar.subheader("🏟️ Formation")
shotgun = st.sidebar.checkbox("Shotgun", value=True)
no_huddle = st.sidebar.checkbox("No Huddle", value=False)

col5, col6 = st.sidebar.columns(2)
with col5:
    defenders_in_box = st.number_input("Defenders in Box", min_value=3, max_value=9, value=6)
with col6:
    pass_rushers = st.number_input("Pass Rushers", min_value=2, max_value=8, value=4)

st.sidebar.markdown("---")
st.sidebar.subheader("👥 Personnel")
col7, col8, col9 = st.sidebar.columns(3)
with col7:
    n_rb = st.number_input("RBs", min_value=0, max_value=3, value=1)
with col8:
    n_te = st.number_input("TEs", min_value=0, max_value=4, value=1)
with col9:
    n_wr = st.number_input("WRs", min_value=0, max_value=5, value=3)

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Time")
minutes = st.sidebar.slider("Minutes Left in Half", 0, 30, 10)
seconds = st.sidebar.slider("Seconds", 0, 59, 0)
half_seconds_remaining = minutes * 60 + seconds

# Calculate derived features
wp = 0.5 + (score_differential * 0.02)  # Simplified win probability
wp = max(0.01, min(0.99, wp))

goal_to_go = 1 if yardline_100 <= ydstogo else 0
short_yardage = 1 if ydstogo <= 3 else 0
long_yardage = 1 if ydstogo >= 8 else 0
red_zone = 1 if yardline_100 <= 20 else 0
late_down = 1 if down >= 3 else 0
two_minute_drill = 1 if half_seconds_remaining <= 120 and abs(score_differential) <= 8 else 0
heavy_box = 1 if defenders_in_box >= 7 else 0
light_box = 1 if defenders_in_box <= 5 else 0
extra_rushers = 1 if pass_rushers >= 5 else 0
pass_heavy_situation = 1 if (down >= 3 and ydstogo >= 5) or (score_differential < -8 and qtr >= 3) else 0
run_heavy_situation = 1 if (down <= 2 and ydstogo <= 4) or (score_differential > 14 and qtr >= 3) else 0
heavy_personnel = 1 if n_rb >= 2 or n_te >= 2 else 0
spread_personnel = 1 if n_wr >= 3 and shotgun else 0

# Build feature dict for play classifier
play_features = {
    'down': down, 'ydstogo': ydstogo, 'yardline_100': yardline_100,
    'score_differential': score_differential, 'qtr': qtr,
    'half_seconds_remaining': half_seconds_remaining, 'wp': wp,
    'posteam_timeouts_remaining': 3, 'defteam_timeouts_remaining': 3,
    'shotgun': int(shotgun), 'no_huddle': int(no_huddle),
    'defenders_in_box': defenders_in_box, 'number_of_pass_rushers': pass_rushers,
    'n_rb': n_rb, 'n_te': n_te, 'n_wr': n_wr,
    'goal_to_go': goal_to_go, 'short_yardage': short_yardage,
    'long_yardage': long_yardage, 'red_zone': red_zone,
    'late_down': late_down, 'two_minute_drill': two_minute_drill,
    'heavy_box': heavy_box, 'light_box': light_box,
    'extra_rushers': extra_rushers, 'pass_heavy_situation': pass_heavy_situation,
    'run_heavy_situation': run_heavy_situation, 'heavy_personnel': heavy_personnel,
    'spread_personnel': spread_personnel
}

# Build feature dict for pressure predictor
pressure_features = {
    'down': down, 'ydstogo': ydstogo, 'yardline_100': yardline_100,
    'score_differential': score_differential, 'qtr': qtr,
    'half_seconds_remaining': half_seconds_remaining, 'wp': wp,
    'posteam_timeouts_remaining': 3, 'defteam_timeouts_remaining': 3,
    'shotgun': int(shotgun), 'no_huddle': int(no_huddle),
    'defenders_in_box': defenders_in_box, 'number_of_pass_rushers': pass_rushers,
    'n_rb': n_rb, 'n_te': n_te, 'n_wr': n_wr,
    'blitz': extra_rushers, 'obvious_passing': pass_heavy_situation,
    'red_zone': red_zone, 'late_game': 1 if qtr >= 4 and half_seconds_remaining <= 300 else 0,
    'rushers_ratio': pass_rushers / (defenders_in_box + 1)
}

# Main content
if models_loaded:
    st.markdown("---")
    
    # Predictions
    col_pred1, col_pred2 = st.columns(2)
    
    with col_pred1:
        st.subheader("🎯 Play Type Prediction")
        
        # Get play prediction
        features_df = pd.DataFrame([play_features])[play_classifier['feature_columns']]
        
        # Stage 1: Run vs Pass
        is_pass = play_classifier['model_run_pass'].predict(features_df.values)[0]
        
        if is_pass:
            pass_pred = play_classifier['model_pass_type'].predict(features_df.values)[0]
            predicted_play = play_classifier['le_pass'].classes_[pass_pred]
        else:
            is_outside = play_classifier['model_run_type'].predict(features_df.values)[0]
            predicted_play = 'outside_run' if is_outside else 'inside_run'
        
        # Display prediction with color
        play_colors = {
            'inside_run': '🟤', 'outside_run': '🟠',
            'screen': '��', 'short_pass': '🔵', 'deep_pass': '🟣'
        }
        
        play_labels = {
            'inside_run': 'Inside Run', 'outside_run': 'Outside Run',
            'screen': 'Screen Pass', 'short_pass': 'Short Pass', 'deep_pass': 'Deep Pass'
        }
        
        st.metric(
            label="Predicted Play",
            value=f"{play_colors.get(predicted_play, '⚪')} {play_labels.get(predicted_play, predicted_play)}"
        )
        
        # Run vs Pass probability
        run_pass_proba = play_classifier['model_run_pass'].predict_proba(features_df.values)[0]
        
        st.markdown("**Run vs Pass Probability:**")
        col_r, col_p = st.columns(2)
        with col_r:
            st.progress(float(run_pass_proba[0]))
            st.caption(f"Run: {run_pass_proba[0]*100:.1f}%")
        with col_p:
            st.progress(float(run_pass_proba[1]))
            st.caption(f"Pass: {run_pass_proba[1]*100:.1f}%")
    
    with col_pred2:
        st.subheader("💥 Pressure Prediction")
        
        # Get pressure prediction
        pressure_df = pd.DataFrame([pressure_features])[pressure_predictor['feature_columns']]
        pressure_prob = pressure_predictor['model'].predict_proba(pressure_df.values)[0][1]
        
        # Display with gauge-like visualization
        st.metric(
            label="Pressure Probability",
            value=f"{pressure_prob*100:.1f}%"
        )
        
        # Color-coded bar
        if pressure_prob < 0.25:
            color = "🟢"
            risk = "Low Risk"
        elif pressure_prob < 0.40:
            color = "🟡"
            risk = "Medium Risk"
        else:
            color = "🔴"
            risk = "High Risk"
        
        st.progress(float(pressure_prob))
        st.markdown(f"**{color} {risk}**")
        
        # Blitz indicator
        if pass_rushers >= 5:
            st.warning("⚠️ BLITZ DETECTED! 5+ pass rushers")
    
    st.markdown("---")
    
    # Situation Analysis
    st.subheader("📋 Situation Analysis")
    
    col_sit1, col_sit2, col_sit3 = st.columns(3)
    
    with col_sit1:
        st.markdown("**Down & Distance:**")
        situation = f"{down}{'st' if down==1 else 'nd' if down==2 else 'rd' if down==3 else 'th'} & {ydstogo}"
        st.info(situation)
        
        if goal_to_go:
            st.success("🎯 Goal to Go!")
        if red_zone:
            st.error("🔴 Red Zone")
    
    with col_sit2:
        st.markdown("**Game State:**")
        if score_differential > 0:
            st.success(f"✅ Leading by {score_differential}")
        elif score_differential < 0:
            st.error(f"❌ Trailing by {abs(score_differential)}")
        else:
            st.info("🟰 Tied Game")
        
        if two_minute_drill:
            st.warning("⏱️ Two-Minute Drill!")
    
    with col_sit3:
        st.markdown("**Tendencies:**")
        if pass_heavy_situation:
            st.info("📡 Pass-Heavy Situation")
        if run_heavy_situation:
            st.info("🏃 Run-Heavy Situation")
        if heavy_personnel:
            st.info("💪 Heavy Personnel")
        if spread_personnel:
            st.info("📶 Spread Formation")

    st.markdown("---")
    
    # Model Info
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
