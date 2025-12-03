"""
Kinesis Producer - Sends play data to Kinesis streams
"""

import boto3
import json
import time
import pandas as pd
from datetime import datetime

class KinesisProducer:
    def __init__(self, stream_name, region='us-east-1'):
        self.stream_name = stream_name
        self.client = boto3.client('kinesis', region_name=region)
    
    def send_record(self, data, partition_key=None):
        """Send a single record to Kinesis."""
        if partition_key is None:
            partition_key = str(data.get('game_id', 'default'))
        
        response = self.client.put_record(
            StreamName=self.stream_name,
            Data=json.dumps(data).encode('utf-8'),
            PartitionKey=partition_key
        )
        return response
    
    def send_batch(self, records):
        """Send multiple records to Kinesis."""
        kinesis_records = []
        for record in records:
            partition_key = str(record.get('game_id', 'default'))
            kinesis_records.append({
                'Data': json.dumps(record).encode('utf-8'),
                'PartitionKey': partition_key
            })
        
        response = self.client.put_records(
            StreamName=self.stream_name,
            Records=kinesis_records
        )
        return response


def create_play_event(row):
    """Convert dataframe row to play event."""
    return {
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
        "offense_formation": str(row.get("offense_formation", "")),
        "defenders_in_box": int(row.get("defenders_in_box", 0)) if pd.notna(row.get("defenders_in_box")) else 0,
        "number_of_pass_rushers": int(row.get("number_of_pass_rushers", 0)) if pd.notna(row.get("number_of_pass_rushers")) else 0,
        "was_pressure": int(row.get("was_pressure", 0)) if pd.notna(row.get("was_pressure")) else 0,
        "time_to_throw": float(row.get("time_to_throw", 0)) if pd.notna(row.get("time_to_throw")) else 0.0,
        "epa": float(row.get("epa", 0)) if pd.notna(row.get("epa")) else 0.0,
        "event_time": datetime.now().isoformat()
    }


def main():
    # Load data
    data_path = "/Users/adithyahnair/nfl-project/data/raw/pbp_2023.csv"
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path, low_memory=False)
    print(f"Loaded {len(df)} plays")
    
    # Create producer
    producer = KinesisProducer('nfl-play-events')
    
    # Send first 10 plays
    print("\nSending 10 plays to Kinesis...")
    for i, (idx, row) in enumerate(df.head(10).iterrows()):
        event = create_play_event(row)
        response = producer.send_record(event)
        print(f"Play {i+1}: Sent to shard {response['ShardId']}")
        time.sleep(0.5)
    
    print("\nDone!")


if __name__ == "__main__":
    main()
