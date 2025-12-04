"""
NFL Real-Time Analytics API
FastAPI backend for Kinesis streaming and predictions
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
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
    description="API for play prediction and Kinesis streaming",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load models on startup
models = {}
kinesis_client = None

@app.on_event("startup")
async def startup():
    global kinesis_client
    
    # Load ML models
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        models['play_classifier'] = joblib.load(os.path.join(base_path, "models", "play_classifier.joblib"))
        models['pressure_predictor'] = joblib.load(os.path.join(base_path, "models", "pressure_predictor.joblib"))
        print("✅ Models loaded successfully")
    except Exception as e:
        print(f"❌ Error loading models: {e}")
    
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
            print(f"❌ Error initializing Kinesis: {e}")
    else:
        print("⚠️ AWS credentials not found in .env file")

# Request/Response models
class PlayData(BaseModel):
    down: int = 1
    ydstogo: int = 10
    yardline_100: int = 75
    qtr: int = 1
    shotgun: int = 1
    no_huddle: int = 0
    defenders_in_box: int = 6
    number_of_pass_rushers: int = 4
    posteam_score: int = 0
    defteam_score: int = 0
    half_seconds_remaining: int = 900
    n_rb: int = 1
    n_te: int = 1
    n_wr: int = 3

class PredictionResponse(BaseModel):
    predicted_play: str
    run_probability: float
    pass_probability: float
    pressure_probability: float
    risk_level: str

class KinesisRecord(BaseModel):
    play_data: dict
    prediction: dict
    timestamp: str

def calculate_features(play_data: PlayData) -> dict:
    """Calculate all features needed for prediction"""
    score_differential = play_data.posteam_score - play_data.defteam_score
    wp = max(0.01, min(0.99, 0.5 + (score_differential * 0.02)))
    
    return {
        'down': play_data.down,
        'ydstogo': play_data.ydstogo,
        'yardline_100': play_data.yardline_100,
        'score_differential': score_differential,
        'qtr': play_data.qtr,
        'half_seconds_remaining': play_data.half_seconds_remaining,
        'wp': wp,
        'posteam_timeouts_remaining': 3,
        'defteam_timeouts_remaining': 3,
        'shotgun': play_data.shotgun,
        'no_huddle': play_data.no_huddle,
        'defenders_in_box': play_data.defenders_in_box,
        'number_of_pass_rushers': play_data.number_of_pass_rushers,
        'n_rb': play_data.n_rb,
        'n_te': play_data.n_te,
        'n_wr': play_data.n_wr,
        'goal_to_go': 1 if play_data.yardline_100 <= play_data.ydstogo else 0,
        'short_yardage': 1 if play_data.ydstogo <= 3 else 0,
        'long_yardage': 1 if play_data.ydstogo >= 8 else 0,
        'red_zone': 1 if play_data.yardline_100 <= 20 else 0,
        'late_down': 1 if play_data.down >= 3 else 0,
        'two_minute_drill': 1 if play_data.half_seconds_remaining <= 120 and abs(score_differential) <= 8 else 0,
        'heavy_box': 1 if play_data.defenders_in_box >= 7 else 0,
        'light_box': 1 if play_data.defenders_in_box <= 5 else 0,
        'extra_rushers': 1 if play_data.number_of_pass_rushers >= 5 else 0,
        'pass_heavy_situation': 1 if (play_data.down >= 3 and play_data.ydstogo >= 5) else 0,
        'run_heavy_situation': 1 if (play_data.down <= 2 and play_data.ydstogo <= 4) else 0,
        'heavy_personnel': 1 if play_data.n_rb >= 2 or play_data.n_te >= 2 else 0,
        'spread_personnel': 1 if play_data.n_wr >= 3 and play_data.shotgun else 0,
        'blitz': 1 if play_data.number_of_pass_rushers >= 5 else 0,
        'obvious_passing': 1 if (play_data.down >= 3 and play_data.ydstogo >= 7) else 0,
        'late_game': 1 if play_data.qtr >= 4 and play_data.half_seconds_remaining <= 300 else 0,
        'rushers_ratio': play_data.number_of_pass_rushers / (play_data.defenders_in_box + 1)
    }

def get_prediction(features: dict) -> dict:
    """Get play and pressure predictions"""
    play_classifier = models.get('play_classifier')
    pressure_predictor = models.get('pressure_predictor')
    
    if not play_classifier or not pressure_predictor:
        raise HTTPException(status_code=500, detail="Models not loaded")
    
    # Play prediction
    features_df = pd.DataFrame([features])[play_classifier['feature_columns']]
    is_pass = play_classifier['model_run_pass'].predict(features_df.values)[0]
    run_pass_proba = play_classifier['model_run_pass'].predict_proba(features_df.values)[0]
    
    if is_pass:
        pass_pred = play_classifier['model_pass_type'].predict(features_df.values)[0]
        predicted_play = play_classifier['le_pass'].classes_[pass_pred]
    else:
        is_outside = play_classifier['model_run_type'].predict(features_df.values)[0]
        predicted_play = 'outside_run' if is_outside else 'inside_run'
    
    # Pressure prediction
    pressure_features = {k: features[k] for k in pressure_predictor['feature_columns'] if k in features}
    pressure_df = pd.DataFrame([pressure_features])[pressure_predictor['feature_columns']]
    pressure_prob = float(pressure_predictor['model'].predict_proba(pressure_df.values)[0][1])
    
    # Risk level
    if pressure_prob < 0.25:
        risk_level = "low"
    elif pressure_prob < 0.40:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    return {
        'predicted_play': predicted_play,
        'run_probability': float(run_pass_proba[0]),
        'pass_probability': float(run_pass_proba[1]),
        'pressure_probability': pressure_prob,
        'risk_level': risk_level
    }

# API Endpoints

@app.get("/")
async def root():
    return {"message": "NFL Real-Time Analytics API", "status": "running"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "models_loaded": bool(models.get('play_classifier') and models.get('pressure_predictor')),
        "kinesis_configured": kinesis_client is not None,
        "stream_name": KINESIS_STREAM
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict(play_data: PlayData):
    """Get play type and pressure prediction for given game situation"""
    features = calculate_features(play_data)
    prediction = get_prediction(features)
    return prediction

@app.get("/kinesis/status")
async def kinesis_status():
    """Check Kinesis connection status"""
    if not kinesis_client:
        return {"status": "not_configured", "message": "AWS credentials not found in .env"}
    
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
    """Fetch latest records from Kinesis stream"""
    if not kinesis_client:
        raise HTTPException(status_code=400, detail="Kinesis not configured. Add AWS credentials to .env")
    
    try:
        # Get shard list
        stream_info = kinesis_client.describe_stream(StreamName=KINESIS_STREAM)
        shards = stream_info['StreamDescription']['Shards']
        
        if not shards:
            return {"status": "empty", "records": [], "predictions": []}
        
        # Get iterator for first shard
        shard_id = shards[0]['ShardId']
        shard_iterator = kinesis_client.get_shard_iterator(
            StreamName=KINESIS_STREAM,
            ShardId=shard_id,
            ShardIteratorType='LATEST'
        )['ShardIterator']
        
        # Fetch records
        response = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=limit)
        
        records = []
        predictions = []
        
        for record in response['Records']:
            data = json.loads(record['Data'].decode('utf-8'))
            records.append(data)
            
            # Convert to PlayData and predict
            play_data = PlayData(
                down=data.get('down', 1),
                ydstogo=data.get('ydstogo', 10),
                yardline_100=data.get('yardline_100', 75),
                qtr=data.get('qtr', 1),
                shotgun=data.get('shotgun', 1),
                no_huddle=data.get('no_huddle', 0),
                defenders_in_box=data.get('defenders_in_box', 6),
                number_of_pass_rushers=data.get('number_of_pass_rushers', 4),
                posteam_score=data.get('posteam_score', 0),
                defteam_score=data.get('defteam_score', 0),
                half_seconds_remaining=data.get('half_seconds_remaining', 900)
            )
            
            features = calculate_features(play_data)
            prediction = get_prediction(features)
            predictions.append(prediction)
        
        return {
            "status": "success",
            "record_count": len(records),
            "records": records,
            "predictions": predictions
        }
        
    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/kinesis/send")
async def kinesis_send(records: List[dict]):
    """Send records to Kinesis stream (for testing)"""
    if not kinesis_client:
        raise HTTPException(status_code=400, detail="Kinesis not configured")
    
    try:
        responses = []
        for record in records:
            response = kinesis_client.put_record(
                StreamName=KINESIS_STREAM,
                Data=json.dumps(record).encode('utf-8'),
                PartitionKey='play'
            )
            responses.append(response['SequenceNumber'])
        
        return {"status": "success", "records_sent": len(records), "sequence_numbers": responses}
        
    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)