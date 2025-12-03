import pandas as pd
import json
import os
import time
from datetime import datetime

def create_test_files(output_dir, num_files=5, plays_per_file=10):
    """Create JSON files simulating streaming data."""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Clear existing files
    for f in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, f))
    
    # Load source data
    data_path = "/Users/adithyahnair/nfl-project/data/raw/pbp_2023.csv"
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path, low_memory=False)
    
    # Filter to actual plays
    df = df[df['play_type'].notna()].head(num_files * plays_per_file)
    print(f"Using {len(df)} plays")
    
    # Create files
    for file_num in range(num_files):
        start_idx = file_num * plays_per_file
        end_idx = start_idx + plays_per_file
        batch = df.iloc[start_idx:end_idx]
        
        records = []
        for _, row in batch.iterrows():
            record = {
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
            records.append(record)
        
        # Write file
        filename = os.path.join(output_dir, f"plays_{file_num:03d}.json")
        with open(filename, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        
        print(f"Created {filename} with {len(records)} plays")
    
    print(f"\nDone! Created {num_files} files in {output_dir}")


if __name__ == "__main__":
    output_dir = "/Users/adithyahnair/nfl-project/data/streaming-input"
    create_test_files(output_dir, num_files=5, plays_per_file=10)
