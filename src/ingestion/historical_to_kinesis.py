"""
Historical Data to Kinesis
Sends historical play-by-play data to Kinesis for testing
"""

import pandas as pd
import boto3
import json
import time
from datetime import datetime

def send_historical_to_kinesis(data_path, stream_name='nfl-play-events', delay=0.5, max_plays=50):
    """Send historical plays to Kinesis stream."""
    
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path, low_memory=False)
    
    # Filter to actual plays
    df = df[df['play_type'].notna()].head(max_plays)
    print(f"Sending {len(df)} plays to Kinesis stream: {stream_name}\n")
    
    kinesis = boto3.client('kinesis', region_name='us-east-1')
    
    for i, (idx, row) in enumerate(df.iterrows()):
        play_data = {
            "game_id": str(row.get("game_id", "")),
            "play_id": int(row.get("play_id", 0)) if pd.notna(row.get("play_id")) else 0,
            "quarter": int(row.get("qtr", 0)) if pd.notna(row.get("qtr")) else 0,
            "down": int(row.get("down", 0)) if pd.notna(row.get("down")) else 0,
            "ydstogo": int(row.get("ydstogo", 0)) if pd.notna(row.get("ydstogo")) else 0,
            "yardline_100": int(row.get("yardline_100", 0)) if pd.notna(row.get("yardline_100")) else 0,
            "posteam": str(row.get("posteam", "")),
            "defteam": str(row.get("defteam", "")),
            "play_type": str(row.get("play_type", "")),
            "shotgun": int(row.get("shotgun", 0)) if pd.notna(row.get("shotgun")) else 0,
            "no_huddle": int(row.get("no_huddle", 0)) if pd.notna(row.get("no_huddle")) else 0,
            "offense_formation": str(row.get("offense_formation", "")) if pd.notna(row.get("offense_formation")) else "",
            "defenders_in_box": int(row.get("defenders_in_box", 0)) if pd.notna(row.get("defenders_in_box")) else 0,
            "number_of_pass_rushers": int(row.get("number_of_pass_rushers", 0)) if pd.notna(row.get("number_of_pass_rushers")) else 0,
            "was_pressure": int(row.get("was_pressure", 0)) if pd.notna(row.get("was_pressure")) else 0,
            "time_to_throw": float(row.get("time_to_throw", 0)) if pd.notna(row.get("time_to_throw")) else 0.0,
            "epa": float(row.get("epa", 0)) if pd.notna(row.get("epa")) else 0.0,
            "event_time": datetime.now().isoformat()
        }
        
        try:
            response = kinesis.put_record(
                StreamName=stream_name,
                Data=json.dumps(play_data).encode('utf-8'),
                PartitionKey=str(play_data['game_id'])
            )
            print(f"Play {i+1}: {play_data['posteam']} vs {play_data['defteam']} | "
                  f"Q{play_data['quarter']} {play_data['down']}&{play_data['ydstogo']} | "
                  f"{play_data['play_type']} | Shard: {response['ShardId']}")
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(delay)
    
    print(f"\nDone! Sent {len(df)} plays to Kinesis.")


if __name__ == "__main__":
    import sys
    
    data_path = "/Users/adithyahnair/nfl-project/data/raw/pbp_2023.csv"
    max_plays = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    
    send_historical_to_kinesis(data_path, max_plays=max_plays)
