"""
FastAPI Backend - Full ESPN Data v2 + Rule-Based Predictions
Supports enhanced data: headshots, receiving leaders, full odds, tickets
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any
import pandas as pd
import numpy as np
import os
import json
import boto3
from datetime import datetime
from pathlib import Path
# Add at top of file, after imports
from threading import Lock


app = FastAPI(title="NFL Real-Time Analytics API", version="4.3")

# Global state for tracking Kinesis position
kinesis_state = {
    'last_sequence_number': None,
    'shard_iterator': None,
    'lock': Lock()
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
PARQUET_PATH = PROJECT_ROOT / "data" / "live_predictions" / "latest"

print(f"📁 Project Root: {PROJECT_ROOT}")
print(f"🧮 Using rule-based predictions (ML models require more features)")

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

def clean_data_for_json(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif isinstance(data, (np.integer,)):
        return int(data)
    elif isinstance(data, (np.floating,)):
        return float(data) if not np.isnan(data) else None
    elif isinstance(data, np.ndarray):
        return data.tolist()
    elif pd.isna(data):
        return None
    return data

def get_predictions(play_data: dict) -> dict:
    """Generate predictions using rule-based formulas"""
    
    down = play_data.get('down', 1)
    ydstogo = play_data.get('ydstogo', 10)
    yardline_100 = play_data.get('yardline_100', 75)
    qtr = play_data.get('qtr', 1)
    seconds = play_data.get('half_seconds_remaining', 900)
    score_diff = play_data.get('score_differential', 0)
    shotgun = play_data.get('shotgun', 1)
    defenders = play_data.get('defenders_in_box', 6)
    rushers = play_data.get('number_of_pass_rushers', 4)
    
    # Expected Points (based on field position and down)
    ep = (100 - yardline_100) * 0.06 - 1.0
    if down == 1: ep += 0.5
    elif down == 2: ep += 0.1
    elif down == 3: ep -= 0.4
    elif down == 4: ep -= 1.2
    if ydstogo <= 3: ep += 0.4
    elif ydstogo >= 10: ep -= 0.3
    if yardline_100 <= 20: ep += 1.5
    if yardline_100 <= 10: ep += 1.0
    if yardline_100 <= 5: ep += 0.5
    
    # TD Probability
    if yardline_100 <= 5: td_prob = 0.55
    elif yardline_100 <= 10: td_prob = 0.40
    elif yardline_100 <= 20: td_prob = 0.28
    elif yardline_100 <= 50: td_prob = 0.15
    else: td_prob = 0.08
    if down == 1: td_prob *= 1.1
    elif down == 4: td_prob *= 0.5
    td_prob = min(td_prob, 0.95)
    
    # FG Probability
    fg_distance = yardline_100 + 17
    if fg_distance <= 30: fg_prob = 0.92
    elif fg_distance <= 40: fg_prob = 0.82
    elif fg_distance <= 50: fg_prob = 0.65
    elif fg_distance <= 55: fg_prob = 0.45
    else: fg_prob = 0.25
    
    # No Score Probability
    no_score_prob = max(0.05, 1.0 - td_prob - fg_prob * 0.3)
    
    # Pass Probability (based on situation)
    pass_prob = 0.55  # Base
    if ydstogo >= 7: pass_prob = 0.72
    if ydstogo >= 10: pass_prob = 0.78
    if down == 3 and ydstogo >= 5: pass_prob = 0.82
    if seconds < 120 and score_diff < 0: pass_prob = 0.85  # Two-minute drill
    if ydstogo <= 2: pass_prob = 0.40  # Short yardage
    if shotgun == 1: pass_prob += 0.10
    pass_prob = min(pass_prob, 0.95)
    run_prob = 1.0 - pass_prob
    
    # Predicted play
    if ydstogo <= 2: predicted = 'run'
    elif down == 4 and yardline_100 > 40: predicted = 'punt'
    elif down == 4 and yardline_100 <= 40: predicted = 'field_goal'
    elif pass_prob > 0.6: predicted = 'pass'
    else: predicted = 'run'
    
    # Pressure Risk
    pressure_prob = 0.25  # Base
    if rushers >= 5: pressure_prob = 0.45
    if rushers >= 6: pressure_prob = 0.55
    if defenders >= 8: pressure_prob += 0.10
    if down == 3 and ydstogo >= 7: pressure_prob += 0.10
    pressure_prob = min(pressure_prob, 0.80)
    
    if pressure_prob >= 0.45: pressure_risk = 'high'
    elif pressure_prob >= 0.30: pressure_risk = 'medium'
    else: pressure_risk = 'low'
    
    return {
        'expected_points': round(ep, 2),
        'td_prob': round(td_prob, 3),
        'fg_prob': round(fg_prob, 3),
        'no_score_prob': round(no_score_prob, 3),
        'opp_td_prob': round(0.05, 3),
        'opp_fg_prob': round(0.02, 3),
        'pass_probability': round(pass_prob, 3),
        'run_probability': round(run_prob, 3),
        'predicted_play': predicted,
        'pressure_probability': round(pressure_prob, 3),
        'pressure_risk': pressure_risk
    }

@app.get("/")
async def root():
    return {
        "message": "NFL Real-Time Analytics API v4.3",
        "prediction_method": "rule-based",
        "full_espn_data": True,
        "enhanced_fields": [
            "player_headshots",
            "receiving_leaders", 
            "full_stat_lines",
            "enhanced_odds",
            "home_away_records",
            "tickets",
            "geo_broadcasts",
            "win_probability_history"
        ]
    }

@app.get("/health")
async def health():
    kinesis_ok = False
    try:
        boto3.client('kinesis', region_name='us-east-1').describe_stream(StreamName='nfl-play-stream')
        kinesis_ok = True
    except: pass
    
    return {
        "status": "healthy",
        "prediction_method": "rule-based",
        "pyspark_output_available": PARQUET_PATH.exists(),
        "kinesis_connected": kinesis_ok
    }

@app.post("/predict")
async def predict(play: PlayInput):
    return {"input": play.dict(), "predictions": get_predictions(play.dict())}

@app.get("/kinesis/status")
async def kinesis_status():
    try:
        kinesis = boto3.client('kinesis', region_name='us-east-1')
        resp = kinesis.describe_stream(StreamName='nfl-play-stream')
        return {"connected": True, "status": resp['StreamDescription']['StreamStatus']}
    except Exception as e:
        return {"connected": False, "error": str(e)}

# @app.get("/kinesis/fetch")
# async def fetch_kinesis():
    try:
        kinesis = boto3.client('kinesis', region_name='us-east-1')
        resp = kinesis.describe_stream(StreamName='nfl-play-stream')
        shard_id = resp['StreamDescription']['Shards'][0]['ShardId']
        
        shard_iter = kinesis.get_shard_iterator(
            StreamName='nfl-play-stream', ShardId=shard_id, ShardIteratorType='TRIM_HORIZON'
        )['ShardIterator']
        
        records = kinesis.get_records(ShardIterator=shard_iter, Limit=100)['Records']
        
        plays = []
        for rec in records:
            try:
                raw = json.loads(rec['Data'].decode('utf-8'))
                preds = get_predictions(raw)
                
                play = {
                    # === Identifiers ===
                    "game_id": raw.get('game_id'),
                    "event_uid": raw.get('event_uid'),
                    "timestamp": raw.get('timestamp'),
                    "source": raw.get('source'),
                    
                    # === Situation (for predictions) ===
                    "down": raw.get('down'),
                    "ydstogo": raw.get('ydstogo'),
                    "yardline_100": raw.get('yardline_100'),
                    "qtr": raw.get('qtr'),
                    "half_seconds_remaining": raw.get('half_seconds_remaining'),
                    "score_differential": raw.get('score_differential'),
                    "goal_to_go": raw.get('goal_to_go'),
                    "posteam": raw.get('posteam'),
                    "defteam": raw.get('defteam'),
                    "posteam_type": raw.get('posteam_type'),
                    
                    # === Game Status ===
                    "status": raw.get('status'),
                    "situation": raw.get('situation'),
                    
                    # === Teams - Basic ===
                    "home_team": raw.get('home_team'),
                    "away_team": raw.get('away_team'),
                    "home_score": raw.get('home_score'),
                    "away_score": raw.get('away_score'),
                    
                    # === Teams - Full (includes leaders with headshots, records) ===
                    "home_team_full": raw.get('home_team_full'),
                    "away_team_full": raw.get('away_team_full'),
                    
                    # === NEW: Game-Level Leaders (top across both teams) ===
                    "gameLeaders": raw.get('gameLeaders'),
                    
                    # === Weather ===
                    "weather": raw.get('weather'),
                    
                    # === Venue ===
                    "venue": raw.get('venue'),
                    
                    # === Odds (enhanced with moneylines, spread odds) ===
                    "odds": raw.get('odds'),
                    
                    # === ESPN Win Probability ===
                    "predictor": raw.get('predictor'),
                    
                    # === NEW: Win Probability History (for charts) ===
                    "winProbabilityHistory": raw.get('winProbabilityHistory'),
                    
                    # === Broadcasts ===
                    "broadcasts": raw.get('broadcasts'),
                    
                    # === NEW: Geo Broadcasts (streaming options) ===
                    "geoBroadcasts": raw.get('geoBroadcasts'),
                    
                    # === NEW: Tickets ===
                    "tickets": raw.get('tickets'),
                    
                    # === NEW: Links (gamecast, boxscore) ===
                    "links": raw.get('links'),
                    
                    # === Last Play ===
                    "lastPlay": raw.get('lastPlay'),
                    
                    # === Event Metadata ===
                    "event": raw.get('event'),
                    
                    # === Game Info ===
                    "gameInfo": raw.get('gameInfo'),
                    
                    # === Predictions (rule-based) ===
                    "ml_predictions": preds,
                    **preds  # Flat predictions for easy access
                }
                plays.append(clean_data_for_json(play))
            except Exception as e:
                print(f"Error processing record: {e}")
        
        return {"status": "success", "source": "kinesis", "play_count": len(plays), "plays": plays}
    except Exception as e:
        return {"status": "error", "error": str(e), "plays": []}
    
@app.get("/kinesis/fetch") 
async def fetch_kinesis():
    """Fetch NEW records from Kinesis (tracks position)"""
    try:
        with kinesis_state['lock']:
            kinesis = boto3.client('kinesis', region_name='us-east-1')
            
            # Get or create shard iterator
            if not kinesis_state['shard_iterator']:
                resp = kinesis.describe_stream(StreamName='nfl-play-stream')
                shard_id = resp['StreamDescription']['Shards'][0]['ShardId']
                
                if kinesis_state['last_sequence_number']:
                    # Resume from last position
                    kinesis_state['shard_iterator'] = kinesis.get_shard_iterator(
                        StreamName='nfl-play-stream',
                        ShardId=shard_id,
                        ShardIteratorType='AFTER_SEQUENCE_NUMBER',
                        StartingSequenceNumber=kinesis_state['last_sequence_number']
                    )['ShardIterator']
                else:
                    # First call - start from latest
                    kinesis_state['shard_iterator'] = kinesis.get_shard_iterator(
                        StreamName='nfl-play-stream',
                        ShardId=shard_id,
                        ShardIteratorType='LATEST'
                    )['ShardIterator']
            
            # Fetch records
            response = kinesis.get_records(
                ShardIterator=kinesis_state['shard_iterator'], 
                Limit=10
            )
            
            records = response['Records']
            kinesis_state['shard_iterator'] = response['NextShardIterator']
            
            # Update sequence number
            if records:
                kinesis_state['last_sequence_number'] = records[-1]['SequenceNumber']
            
            # Process records
            plays = []
            for rec in records:
                raw = json.loads(rec['Data'].decode('utf-8'))
                preds = get_predictions(raw)
                play = {**raw, 'ml_predictions': preds, **preds}
                plays.append(clean_data_for_json(play))
            
            return {
                "status": "success", 
                "source": "kinesis", 
                "play_count": len(plays), 
                "plays": plays,
                "has_new_data": len(plays) > 0
            }
            
    except Exception as e:
        # Reset iterator on error
        kinesis_state['shard_iterator'] = None
        return {"status": "error", "error": str(e), "plays": []}


@app.post("/kinesis/reset")
async def reset_kinesis():
    """Reset Kinesis position to start fresh"""
    kinesis_state['last_sequence_number'] = None
    kinesis_state['shard_iterator'] = None
    return {"status": "reset", "message": "Will fetch from LATEST on next call"}

@app.get("/kinesis/latest")
async def fetch_latest():
    result = await fetch_kinesis()
    if result.get('plays'):
        return {"status": "success", "play": result['plays'][-1]}
    return {"status": "no_data", "play": None}

@app.get("/pyspark/predictions")
async def get_pyspark():
    if not PARQUET_PATH.exists():
        return {"status": "no_data", "plays": []}
    try:
        df = pd.read_parquet(PARQUET_PATH)
        return {"status": "success", "plays": [clean_data_for_json(p) for p in df.to_dict('records')]}
    except Exception as e:
        return {"status": "error", "message": str(e), "plays": []}

@app.get("/teams")
async def get_teams():
    teams = [
        {"abbr": "ARI", "name": "Arizona Cardinals", "color": "97233F"},
        {"abbr": "ATL", "name": "Atlanta Falcons", "color": "A71930"},
        {"abbr": "BAL", "name": "Baltimore Ravens", "color": "241773"},
        {"abbr": "BUF", "name": "Buffalo Bills", "color": "00338D"},
        {"abbr": "CAR", "name": "Carolina Panthers", "color": "0085CA"},
        {"abbr": "CHI", "name": "Chicago Bears", "color": "0B162A"},
        {"abbr": "CIN", "name": "Cincinnati Bengals", "color": "FB4F14"},
        {"abbr": "CLE", "name": "Cleveland Browns", "color": "311D00"},
        {"abbr": "DAL", "name": "Dallas Cowboys", "color": "003594"},
        {"abbr": "DEN", "name": "Denver Broncos", "color": "FB4F14"},
        {"abbr": "DET", "name": "Detroit Lions", "color": "0076B6"},
        {"abbr": "GB", "name": "Green Bay Packers", "color": "203731"},
        {"abbr": "HOU", "name": "Houston Texans", "color": "03202F"},
        {"abbr": "IND", "name": "Indianapolis Colts", "color": "002C5F"},
        {"abbr": "JAX", "name": "Jacksonville Jaguars", "color": "006778"},
        {"abbr": "KC", "name": "Kansas City Chiefs", "color": "E31837"},
        {"abbr": "LAC", "name": "Los Angeles Chargers", "color": "0080C6"},
        {"abbr": "LAR", "name": "Los Angeles Rams", "color": "003594"},
        {"abbr": "LV", "name": "Las Vegas Raiders", "color": "000000"},
        {"abbr": "MIA", "name": "Miami Dolphins", "color": "008E97"},
        {"abbr": "MIN", "name": "Minnesota Vikings", "color": "4F2683"},
        {"abbr": "NE", "name": "New England Patriots", "color": "002244"},
        {"abbr": "NO", "name": "New Orleans Saints", "color": "D3BC8D"},
        {"abbr": "NYG", "name": "New York Giants", "color": "0B2265"},
        {"abbr": "NYJ", "name": "New York Jets", "color": "125740"},
        {"abbr": "PHI", "name": "Philadelphia Eagles", "color": "004C54"},
        {"abbr": "PIT", "name": "Pittsburgh Steelers", "color": "FFB612"},
        {"abbr": "SEA", "name": "Seattle Seahawks", "color": "002244"},
        {"abbr": "SF", "name": "San Francisco 49ers", "color": "AA0000"},
        {"abbr": "TB", "name": "Tampa Bay Buccaneers", "color": "D50A0A"},
        {"abbr": "TEN", "name": "Tennessee Titans", "color": "0C2340"},
        {"abbr": "WAS", "name": "Washington Commanders", "color": "5A1414"}
    ]
    for t in teams:
        t['logo'] = f"https://a.espncdn.com/i/teamlogos/nfl/500/{t['abbr'].lower()}.png"
    return {"teams": teams}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)