"""
FastAPI Backend - Reads predictions from PySpark Parquet output
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import joblib
import pandas as pd
import numpy as np
import os
import json
import boto3
from datetime import datetime

app = FastAPI(title="NFL Real-Time Analytics API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
MODELS_PATH = "/Users/adithyahnair/nfl-project/models"
PARQUET_PATH = "/Users/adithyahnair/nfl-project/data/live_predictions/latest"

# Load ML models
models = {}

def load_models():
    global models
    model_files = {
        'play_classifier': 'play_classifier.joblib',
        'pressure_predictor': 'pressure_predictor.joblib',
        'expected_points': 'expected_points.joblib',
        'scoring_probability': 'scoring_probability.joblib'
    }
    
    for name, filename in model_files.items():
        path = os.path.join(MODELS_PATH, filename)
        if os.path.exists(path):
            models[name] = joblib.load(path)
            print(f"✅ Loaded {name}")
        else:
            print(f"⚠️ Model not found: {path}")

load_models()

class PlayInput(BaseModel):
    down: int
    ydstogo: int
    yardline_100: int
    qtr: int = 1
    half_seconds_remaining: int = 900
    score_differential: int = 0
    shotgun: int = 1
    no_huddle: int = 0
    defenders_in_box: int = 6
    number_of_pass_rushers: int = 4
    posteam_type: str = "home"
    goal_to_go: int = 0
    posteam: Optional[str] = None
    defteam: Optional[str] = None

@app.get("/")
async def root():
    return {
        "message": "NFL Real-Time Analytics API v3.0",
        "models_loaded": list(models.keys()),
        "pyspark_integration": True
    }

@app.get("/health")
async def health():
    parquet_exists = os.path.exists(PARQUET_PATH)
    return {
        "status": "healthy",
        "models_loaded": len(models),
        "model_names": list(models.keys()),
        "pyspark_output_available": parquet_exists
    }

@app.post("/predict")
async def predict(play: PlayInput):
    """Get all predictions for a play using ML models"""
    
    features = prepare_features(play)
    result = {}
    
    # Expected Points
    if 'expected_points' in models:
        ep_features = features[['down', 'ydstogo', 'yardline_100', 'qtr', 
                                'half_seconds_remaining', 'score_differential',
                                'posteam_is_home', 'goal_to_go', 'shotgun', 'no_huddle']]
        result['expected_points'] = round(float(models['expected_points'].predict(ep_features)[0]), 2)
    
    # Scoring Probability
    if 'scoring_probability' in models:
        sp_features = features[['down', 'ydstogo', 'yardline_100', 'qtr',
                                'half_seconds_remaining', 'score_differential',
                                'posteam_is_home', 'goal_to_go', 'shotgun', 'no_huddle']]
        probs = models['scoring_probability'].predict(sp_features)[0]
        result['td_prob'] = round(float(probs[0]), 3)
        result['fg_prob'] = round(float(probs[1]), 3)
        result['no_score_prob'] = round(float(probs[2]), 3)
        result['opp_td_prob'] = round(float(probs[3]), 3)
        result['opp_fg_prob'] = round(float(probs[4]), 3)
        result['safety_prob'] = round(float(probs[5]), 3)
        result['opp_safety_prob'] = round(float(probs[6]), 3)
    
    # Play Type
    if 'play_classifier' in models:
        pc_features = features[['down', 'ydstogo', 'yardline_100', 'qtr',
                                'half_seconds_remaining', 'score_differential',
                                'shotgun', 'no_huddle', 'defenders_in_box',
                                'number_of_pass_rushers']]
        pred = models['play_classifier'].predict(pc_features)[0]
        proba = models['play_classifier'].predict_proba(pc_features)[0]
        result['predicted_play'] = pred
        result['run_probability'] = round(float(proba[0] + proba[1]), 3)
        result['pass_probability'] = round(float(proba[2] + proba[3] + proba[4]), 3)
    
    # Pressure
    if 'pressure_predictor' in models:
        pp_features = features[['down', 'ydstogo', 'yardline_100', 'shotgun',
                                'no_huddle', 'defenders_in_box', 'number_of_pass_rushers']]
        pressure_prob = models['pressure_predictor'].predict_proba(pp_features)[0][1]
        result['pressure_probability'] = round(float(pressure_prob), 3)
        result['pressure_risk'] = 'high' if pressure_prob > 0.5 else 'medium' if pressure_prob > 0.3 else 'low'
    
    return result

def prepare_features(play: PlayInput) -> pd.DataFrame:
    """Prepare features DataFrame from play input"""
    data = {
        'down': [play.down],
        'ydstogo': [play.ydstogo],
        'yardline_100': [play.yardline_100],
        'qtr': [play.qtr],
        'half_seconds_remaining': [play.half_seconds_remaining],
        'score_differential': [play.score_differential],
        'shotgun': [play.shotgun],
        'no_huddle': [play.no_huddle],
        'defenders_in_box': [play.defenders_in_box],
        'number_of_pass_rushers': [play.number_of_pass_rushers],
        'posteam_is_home': [1 if play.posteam_type == 'home' else 0],
        'goal_to_go': [play.goal_to_go]
    }
    return pd.DataFrame(data)

# ============================================================
# PYSPARK INTEGRATION - Read from Parquet
# ============================================================

@app.get("/pyspark/predictions")
async def get_pyspark_predictions():
    """Get latest predictions from PySpark Parquet output"""
    
    if not os.path.exists(PARQUET_PATH):
        return {
            "status": "no_data",
            "message": "PySpark has not processed any data yet. Run spark_stream_processor.py",
            "plays": []
        }
    
    try:
        df = pd.read_parquet(PARQUET_PATH)
        
        if df.empty:
            return {"status": "empty", "plays": []}
        
        # Convert to list of dicts
        plays = df.to_dict(orient='records')
        
        # Clean up NaN values
        for play in plays:
            for key, value in play.items():
                if pd.isna(value):
                    play[key] = None
                elif isinstance(value, (np.integer, np.floating)):
                    play[key] = float(value)
        
        return {
            "status": "success",
            "source": "pyspark",
            "play_count": len(plays),
            "plays": plays
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e), "plays": []}

@app.get("/pyspark/latest")
async def get_latest_pyspark():
    """Get only the most recent play from PySpark output"""
    
    if not os.path.exists(PARQUET_PATH):
        return {"status": "no_data", "play": None}
    
    try:
        df = pd.read_parquet(PARQUET_PATH)
        
        if df.empty:
            return {"status": "empty", "play": None}
        
        # Get latest play
        latest = df.iloc[-1].to_dict()
        
        # Clean NaN
        for key, value in latest.items():
            if pd.isna(value):
                latest[key] = None
            elif isinstance(value, (np.integer, np.floating)):
                latest[key] = float(value)
        
        return {
            "status": "success",
            "source": "pyspark",
            "play": latest
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============================================================
# KINESIS DIRECT (Fallback - kept for compatibility)
# ============================================================

@app.get("/kinesis/status")
async def kinesis_status():
    """Check Kinesis connection status"""
    try:
        kinesis = boto3.client('kinesis', region_name='us-east-1')
        response = kinesis.describe_stream(StreamName='nfl-play-stream')
        
        return {
            "connected": True,
            "stream_name": "nfl-play-stream",
            "status": response['StreamDescription']['StreamStatus'],
            "shard_count": len(response['StreamDescription']['Shards']),
            "note": "Use /pyspark/predictions for PySpark-processed data"
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}

@app.get("/kinesis/fetch")
async def fetch_kinesis():
    """Fetch directly from Kinesis (fallback, bypasses PySpark)"""
    try:
        kinesis = boto3.client('kinesis', region_name='us-east-1')
        
        response = kinesis.describe_stream(StreamName='nfl-play-stream')
        shard_id = response['StreamDescription']['Shards'][0]['ShardId']
        
        shard_iterator = kinesis.get_shard_iterator(
            StreamName='nfl-play-stream',
            ShardId=shard_id,
            ShardIteratorType='TRIM_HORIZON'
        )['ShardIterator']
        
        records_response = kinesis.get_records(ShardIterator=shard_iterator, Limit=100)
        
        plays = []
        for record in records_response['Records']:
            try:
                data = json.loads(record['Data'].decode('utf-8'))
                
                # Add predictions using ML models
                play_input = PlayInput(**{
                    'down': data.get('down', 1),
                    'ydstogo': data.get('ydstogo', 10),
                    'yardline_100': data.get('yardline_100', 75),
                    'qtr': data.get('qtr', 1),
                    'half_seconds_remaining': data.get('half_seconds_remaining', 900),
                    'score_differential': data.get('score_differential', 0),
                    'shotgun': data.get('shotgun', 1),
                    'no_huddle': data.get('no_huddle', 0),
                    'defenders_in_box': data.get('defenders_in_box', 6),
                    'number_of_pass_rushers': data.get('number_of_pass_rushers', 4),
                    'posteam_type': data.get('posteam_type', 'home'),
                    'goal_to_go': data.get('goal_to_go', 0),
                    'posteam': data.get('posteam'),
                    'defteam': data.get('defteam')
                })
                
                predictions = await predict(play_input)
                data.update(predictions)
                plays.append(data)
            except Exception as e:
                continue
        
        return {
            "status": "success",
            "source": "kinesis_direct",
            "play_count": len(plays),
            "plays": plays,
            "note": "For PySpark-processed data, use /pyspark/predictions"
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e), "plays": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
