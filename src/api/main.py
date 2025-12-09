"""
NFL Real-Time Analytics API
FastAPI backend with all ML models
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import pandas as pd
import numpy as np
import joblib
import json
import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
KINESIS_STREAM = os.getenv('KINESIS_STREAM_NAME', 'nfl-play-stream')

app = FastAPI(
    title="NFL Real-Time Analytics API",
    description="API for play prediction, expected points, and scoring probability",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models storage
models = {}
kinesis_client = None

@app.on_event("startup")
async def startup():
    global kinesis_client
    
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Load all models
    try:
        models['play_classifier'] = joblib.load(os.path.join(base_path, "models", "play_classifier.joblib"))
        print("✅ Play Classifier loaded")
    except Exception as e:
        print(f"⚠️ Play Classifier not loaded: {e}")
    
    try:
        models['pressure_predictor'] = joblib.load(os.path.join(base_path, "models", "pressure_predictor.joblib"))
        print("✅ Pressure Predictor loaded")
    except Exception as e:
        print(f"⚠️ Pressure Predictor not loaded: {e}")
    
    try:
        models['expected_points'] = joblib.load(os.path.join(base_path, "models", "expected_points.joblib"))
        print("✅ Expected Points loaded")
    except Exception as e:
        print(f"⚠️ Expected Points not loaded: {e}")
    
    try:
        models['scoring_probability'] = joblib.load(os.path.join(base_path, "models", "scoring_probability.joblib"))
        print("✅ Scoring Probability loaded")
    except Exception as e:
        print(f"⚠️ Scoring Probability not loaded: {e}")
    
    # Initialize Kinesis client
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        try:
            kinesis_client = boto3.client(
                'kinesis',
                region_name=AWS_REGION,
                aws_access_key_id=AWS_ACCESS_KEY,
                aws_secret_access_key=AWS_SECRET_KEY
            )
            print(f"✅ Kinesis client initialized for stream: {KINESIS_STREAM}")
        except Exception as e:
            print(f"⚠️ Kinesis not initialized: {e}")
    else:
        print("⚠️ AWS credentials not found")


# Request/Response Models
class PlayData(BaseModel):
    down: int = 1
    ydstogo: int = 10
    yardline_100: int = 75
    qtr: int = 1
    half_seconds_remaining: int = 900
    posteam_timeouts_remaining: int = 3
    defteam_timeouts_remaining: int = 3
    score_differential: int = 0
    posteam_score: int = 0
    defteam_score: int = 0
    posteam_type: str = "home"
    shotgun: int = 1
    no_huddle: int = 0
    goal_to_go: int = 0
    # For play classifier / pressure predictor
    defenders_in_box: int = 6
    number_of_pass_rushers: int = 4


class FullPredictionResponse(BaseModel):
    # Expected Points (real-time ready)
    expected_points: float
    # Scoring Probabilities (real-time ready)
    td_prob: float
    fg_prob: float
    no_score_prob: float
    opp_td_prob: float
    opp_fg_prob: float
    safety_prob: float
    opp_safety_prob: float
    # Play Classification (needs post-snap data)
    predicted_play: str
    run_probability: float
    pass_probability: float
    # Pressure Prediction (needs post-snap data)
    pressure_probability: float
    pressure_risk: str


# Helper Functions
def calculate_play_features(play: PlayData) -> dict:
    """Calculate features for play classifier"""
    score_diff = play.posteam_score - play.defteam_score if play.score_differential == 0 else play.score_differential
    wp = max(0.01, min(0.99, 0.5 + (score_diff * 0.02)))
    
    return {
        'down': play.down,
        'ydstogo': play.ydstogo,
        'yardline_100': play.yardline_100,
        'score_differential': score_diff,
        'qtr': play.qtr,
        'half_seconds_remaining': play.half_seconds_remaining,
        'wp': wp,
        'posteam_timeouts_remaining': play.posteam_timeouts_remaining,
        'defteam_timeouts_remaining': play.defteam_timeouts_remaining,
        'shotgun': play.shotgun,
        'no_huddle': play.no_huddle,
        'defenders_in_box': play.defenders_in_box,
        'number_of_pass_rushers': play.number_of_pass_rushers,
        'n_rb': 1, 'n_te': 1, 'n_wr': 3,
        'goal_to_go': play.goal_to_go,
        'short_yardage': 1 if play.ydstogo <= 3 else 0,
        'long_yardage': 1 if play.ydstogo >= 8 else 0,
        'red_zone': 1 if play.yardline_100 <= 20 else 0,
        'late_down': 1 if play.down >= 3 else 0,
        'two_minute_drill': 1 if play.half_seconds_remaining <= 120 and abs(score_diff) <= 8 else 0,
        'heavy_box': 1 if play.defenders_in_box >= 7 else 0,
        'light_box': 1 if play.defenders_in_box <= 5 else 0,
        'extra_rushers': 1 if play.number_of_pass_rushers >= 5 else 0,
        'pass_heavy_situation': 1 if (play.down >= 3 and play.ydstogo >= 5) else 0,
        'run_heavy_situation': 1 if (play.down <= 2 and play.ydstogo <= 4) else 0,
        'heavy_personnel': 0,
        'spread_personnel': 1 if play.shotgun else 0,
        'blitz': 1 if play.number_of_pass_rushers >= 5 else 0,
        'obvious_passing': 1 if (play.down >= 3 and play.ydstogo >= 7) else 0,
        'late_game': 1 if play.qtr >= 4 and play.half_seconds_remaining <= 300 else 0,
        'rushers_ratio': play.number_of_pass_rushers / (play.defenders_in_box + 1)
    }


def calculate_ep_features(play: PlayData) -> dict:
    """Calculate features for expected points model"""
    return {
        'down': play.down,
        'ydstogo': play.ydstogo,
        'yardline_100': play.yardline_100,
        'half_seconds_remaining': play.half_seconds_remaining,
        'posteam_timeouts_remaining': play.posteam_timeouts_remaining,
        'defteam_timeouts_remaining': play.defteam_timeouts_remaining,
        'score_differential': play.score_differential if play.score_differential != 0 else play.posteam_score - play.defteam_score,
        'posteam_is_home': 1 if play.posteam_type == 'home' else 0,
        'qtr': play.qtr,
        'goal_to_go': play.goal_to_go,
        'shotgun': play.shotgun,
        'no_huddle': play.no_huddle
    }


def predict_play_type(features: dict) -> dict:
    """Get play type prediction"""
    pc = models.get('play_classifier')
    if not pc:
        return {'predicted_play': 'unknown', 'run_probability': 0.5, 'pass_probability': 0.5}
    
    features_df = pd.DataFrame([features])[pc['feature_columns']]
    is_pass = pc['model_run_pass'].predict(features_df.values)[0]
    run_pass_proba = pc['model_run_pass'].predict_proba(features_df.values)[0]
    
    if is_pass:
        pass_pred = pc['model_pass_type'].predict(features_df.values)[0]
        predicted_play = pc['le_pass'].classes_[pass_pred]
    else:
        is_outside = pc['model_run_type'].predict(features_df.values)[0]
        predicted_play = 'outside_run' if is_outside else 'inside_run'
    
    return {
        'predicted_play': predicted_play,
        'run_probability': float(run_pass_proba[0]),
        'pass_probability': float(run_pass_proba[1])
    }


def predict_pressure(features: dict) -> dict:
    """Get pressure prediction"""
    pp = models.get('pressure_predictor')
    if not pp:
        return {'pressure_probability': 0.3, 'pressure_risk': 'medium'}
    
    pressure_features = {k: features[k] for k in pp['feature_columns'] if k in features}
    pressure_df = pd.DataFrame([pressure_features])[pp['feature_columns']]
    pressure_prob = float(pp['model'].predict_proba(pressure_df.values)[0][1])
    
    if pressure_prob < 0.25:
        risk = "low"
    elif pressure_prob < 0.40:
        risk = "medium"
    else:
        risk = "high"
    
    return {'pressure_probability': pressure_prob, 'pressure_risk': risk}


def predict_expected_points(features: dict) -> float:
    """Get expected points prediction"""
    ep = models.get('expected_points')
    if not ep:
        return 0.0
    
    df = pd.DataFrame([features])
    for col in ep['feature_columns']:
        if col not in df.columns:
            df[col] = 0
    X = df[ep['feature_columns']].fillna(0)
    return float(ep['model'].predict(X)[0])


def predict_scoring_probs(features: dict) -> dict:
    """Get scoring probability predictions"""
    sp = models.get('scoring_probability')
    if not sp:
        return {
            'td_prob': 0.2, 'fg_prob': 0.15, 'no_score_prob': 0.4,
            'opp_td_prob': 0.1, 'opp_fg_prob': 0.1,
            'safety_prob': 0.025, 'opp_safety_prob': 0.025
        }
    
    df = pd.DataFrame([features])
    for col in sp['feature_columns']:
        if col not in df.columns:
            df[col] = 0
    X = df[sp['feature_columns']].fillna(0)
    
    probs = {}
    for prob_col, model in sp['models'].items():
        probs[prob_col] = float(model.predict(X)[0])
    
    # Normalize
    total = sum(probs.values())
    if total > 0:
        probs = {k: v/total for k, v in probs.items()}
    
    return probs


# API Endpoints
@app.get("/")
async def root():
    return {"message": "NFL Real-Time Analytics API v2.0", "status": "running"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "models": {
            "play_classifier": "play_classifier" in models,
            "pressure_predictor": "pressure_predictor" in models,
            "expected_points": "expected_points" in models,
            "scoring_probability": "scoring_probability" in models
        },
        "kinesis_configured": kinesis_client is not None,
        "stream_name": KINESIS_STREAM
    }


@app.post("/predict", response_model=FullPredictionResponse)
async def predict_all(play: PlayData):
    """Get all predictions for a play"""
    
    # Calculate features
    play_features = calculate_play_features(play)
    ep_features = calculate_ep_features(play)
    
    # Get predictions
    play_pred = predict_play_type(play_features)
    pressure_pred = predict_pressure(play_features)
    expected_points = predict_expected_points(ep_features)
    scoring_probs = predict_scoring_probs(ep_features)
    
    return FullPredictionResponse(
        expected_points=round(expected_points, 2),
        td_prob=round(scoring_probs.get('td_prob', 0), 4),
        fg_prob=round(scoring_probs.get('fg_prob', 0), 4),
        no_score_prob=round(scoring_probs.get('no_score_prob', 0), 4),
        opp_td_prob=round(scoring_probs.get('opp_td_prob', 0), 4),
        opp_fg_prob=round(scoring_probs.get('opp_fg_prob', 0), 4),
        safety_prob=round(scoring_probs.get('safety_prob', 0), 4),
        opp_safety_prob=round(scoring_probs.get('opp_safety_prob', 0), 4),
        predicted_play=play_pred['predicted_play'],
        run_probability=round(play_pred['run_probability'], 4),
        pass_probability=round(play_pred['pass_probability'], 4),
        pressure_probability=round(pressure_pred['pressure_probability'], 4),
        pressure_risk=pressure_pred['pressure_risk']
    )


@app.post("/predict/expected-points")
async def predict_ep(play: PlayData):
    """Get expected points prediction (real-time ready)"""
    features = calculate_ep_features(play)
    ep = predict_expected_points(features)
    return {"expected_points": round(ep, 2)}


@app.post("/predict/scoring")
async def predict_scoring(play: PlayData):
    """Get scoring probability predictions (real-time ready)"""
    features = calculate_ep_features(play)
    probs = predict_scoring_probs(features)
    return {k: round(v, 4) for k, v in probs.items()}


@app.post("/predict/play-type")
async def predict_play(play: PlayData):
    """Get play type prediction (needs post-snap data for best results)"""
    features = calculate_play_features(play)
    pred = predict_play_type(features)
    return pred


@app.post("/predict/pressure")
async def predict_press(play: PlayData):
    """Get pressure prediction (needs post-snap data for best results)"""
    features = calculate_play_features(play)
    pred = predict_pressure(features)
    return pred


@app.get("/kinesis/status")
async def kinesis_status():
    """Check Kinesis connection status"""
    if not kinesis_client:
        return {"status": "not_configured", "message": "AWS credentials not found"}
    
    try:
        response = kinesis_client.describe_stream(StreamName=KINESIS_STREAM)
        shards = response['StreamDescription']['Shards']
        return {
            "status": "connected",
            "stream_name": KINESIS_STREAM,
            "stream_status": response['StreamDescription']['StreamStatus'],
            "shard_count": len(shards),
            "shards": [s['ShardId'] for s in shards]
        }
    except ClientError as e:
        return {"status": "error", "message": str(e)}


@app.get("/kinesis/fetch")
async def kinesis_fetch(limit: int = 10):
    """Fetch latest records from Kinesis and return predictions"""
    if not kinesis_client:
        raise HTTPException(status_code=400, detail="Kinesis not configured")
    
    try:
        stream_info = kinesis_client.describe_stream(StreamName=KINESIS_STREAM)
        shards = stream_info['StreamDescription']['Shards']
        
        if not shards:
            return {"status": "empty", "records": [], "predictions": []}
        
        shard_id = shards[0]['ShardId']
        shard_iterator = kinesis_client.get_shard_iterator(
            StreamName=KINESIS_STREAM,
            ShardId=shard_id,
            ShardIteratorType='TRIM_HORIZON'
        )['ShardIterator']
        
        response = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=limit)
        
        records = []
        predictions = []
        
        for record in response['Records']:
            data = json.loads(record['Data'].decode('utf-8'))
            records.append(data)
            
            play = PlayData(**{k: data.get(k, getattr(PlayData(), k)) for k in PlayData.__fields__})
            
            play_features = calculate_play_features(play)
            ep_features = calculate_ep_features(play)
            
            pred = {
                'expected_points': round(predict_expected_points(ep_features), 2),
                'scoring_probs': {k: round(v, 4) for k, v in predict_scoring_probs(ep_features).items()},
                'play_type': predict_play_type(play_features),
                'pressure': predict_pressure(play_features)
            }
            predictions.append(pred)
        
        return {
            "status": "success",
            "record_count": len(records),
            "records": records,
            "predictions": predictions
        }
        
    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
