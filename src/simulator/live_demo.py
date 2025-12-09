#!/usr/bin/env python3
"""
NFL Live Demo Simulator
Replays historical plays through Kinesis for demonstration
"""

import boto3
import json
import time
import pandas as pd
import random
from datetime import datetime

STREAM_NAME = 'nfl-play-stream'
REGION = 'us-east-1'

# Sample exciting game scenarios
DEMO_SCENARIOS = [
    {"name": "4th Quarter Comeback", "game_id": "demo_001", "plays": [
        {"down": 1, "ydstogo": 10, "yardline_100": 75, "qtr": 4, "half_seconds_remaining": 300, "score_differential": -7, "posteam": "KC", "defteam": "SF", "desc": "Chiefs down 7, 5 min left"},
        {"down": 2, "ydstogo": 3, "yardline_100": 68, "qtr": 4, "half_seconds_remaining": 255, "score_differential": -7, "posteam": "KC", "defteam": "SF", "desc": "Quick 7 yard gain"},
        {"down": 1, "ydstogo": 10, "yardline_100": 55, "qtr": 4, "half_seconds_remaining": 220, "score_differential": -7, "posteam": "KC", "defteam": "SF", "desc": "Crossing midfield"},
        {"down": 3, "ydstogo": 6, "yardline_100": 42, "qtr": 4, "half_seconds_remaining": 180, "score_differential": -7, "posteam": "KC", "defteam": "SF", "desc": "3rd down conversion needed"},
        {"down": 1, "ydstogo": 10, "yardline_100": 28, "qtr": 4, "half_seconds_remaining": 140, "score_differential": -7, "posteam": "KC", "defteam": "SF", "desc": "Into the red zone!"},
        {"down": 2, "ydstogo": 8, "yardline_100": 18, "qtr": 4, "half_seconds_remaining": 95, "score_differential": -7, "posteam": "KC", "defteam": "SF", "desc": "Under 2 minutes"},
        {"down": 1, "ydstogo": 5, "yardline_100": 5, "qtr": 4, "half_seconds_remaining": 45, "score_differential": -7, "posteam": "KC", "defteam": "SF", "goal_to_go": 1, "desc": "1st & Goal at the 5!"},
        {"down": 2, "ydstogo": 2, "yardline_100": 2, "qtr": 4, "half_seconds_remaining": 12, "score_differential": -7, "posteam": "KC", "defteam": "SF", "goal_to_go": 1, "desc": "GAME ON THE LINE!"},
    ]},
    {"name": "Red Zone Showdown", "game_id": "demo_002", "plays": [
        {"down": 1, "ydstogo": 10, "yardline_100": 20, "qtr": 2, "half_seconds_remaining": 600, "score_differential": 0, "posteam": "DAL", "defteam": "PHI", "desc": "Cowboys in the red zone"},
        {"down": 2, "ydstogo": 6, "yardline_100": 16, "qtr": 2, "half_seconds_remaining": 555, "score_differential": 0, "posteam": "DAL", "defteam": "PHI", "desc": "4 yard gain"},
        {"down": 3, "ydstogo": 4, "yardline_100": 14, "qtr": 2, "half_seconds_remaining": 510, "score_differential": 0, "posteam": "DAL", "defteam": "PHI", "desc": "3rd and short"},
        {"down": 1, "ydstogo": 8, "yardline_100": 8, "qtr": 2, "half_seconds_remaining": 465, "score_differential": 0, "posteam": "DAL", "defteam": "PHI", "goal_to_go": 1, "desc": "1st & Goal at the 8!"},
        {"down": 2, "ydstogo": 5, "yardline_100": 5, "qtr": 2, "half_seconds_remaining": 420, "score_differential": 0, "posteam": "DAL", "defteam": "PHI", "goal_to_go": 1, "desc": "2nd & Goal"},
        {"down": 3, "ydstogo": 3, "yardline_100": 3, "qtr": 2, "half_seconds_remaining": 375, "score_differential": 0, "posteam": "DAL", "defteam": "PHI", "goal_to_go": 1, "desc": "3rd & Goal - TD or FG?"},
    ]},
    {"name": "Two Minute Drill", "game_id": "demo_003", "plays": [
        {"down": 1, "ydstogo": 10, "yardline_100": 80, "qtr": 2, "half_seconds_remaining": 120, "score_differential": -3, "posteam": "BUF", "defteam": "MIA", "no_huddle": 1, "desc": "Two minute warning - down by 3"},
        {"down": 1, "ydstogo": 10, "yardline_100": 65, "qtr": 2, "half_seconds_remaining": 95, "score_differential": -3, "posteam": "BUF", "defteam": "MIA", "no_huddle": 1, "desc": "15 yard completion!"},
        {"down": 2, "ydstogo": 7, "yardline_100": 52, "qtr": 2, "half_seconds_remaining": 70, "score_differential": -3, "posteam": "BUF", "defteam": "MIA", "no_huddle": 1, "desc": "Hurry up offense"},
        {"down": 1, "ydstogo": 10, "yardline_100": 38, "qtr": 2, "half_seconds_remaining": 48, "score_differential": -3, "posteam": "BUF", "defteam": "MIA", "no_huddle": 1, "desc": "Into FG range"},
        {"down": 1, "ydstogo": 10, "yardline_100": 25, "qtr": 2, "half_seconds_remaining": 25, "score_differential": -3, "posteam": "BUF", "defteam": "MIA", "no_huddle": 1, "desc": "Spike it or go for more?"},
        {"down": 2, "ydstogo": 10, "yardline_100": 25, "qtr": 2, "half_seconds_remaining": 8, "score_differential": -3, "posteam": "BUF", "defteam": "MIA", "no_huddle": 1, "desc": "One shot at the end zone!"},
    ]},
]

def send_to_kinesis(client, play_data):
    """Send play to Kinesis stream"""
    try:
        response = client.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(play_data).encode('utf-8'),
            PartitionKey=str(play_data.get('game_id', 'demo'))
        )
        return response
    except Exception as e:
        print(f"Error sending to Kinesis: {e}")
        return None

def run_scenario(client, scenario, delay=3):
    """Run a single game scenario"""
    print(f"\n{'='*60}")
    print(f"🏈 SCENARIO: {scenario['name']}")
    print(f"{'='*60}")
    
    for i, play in enumerate(scenario['plays'], 1):
        # Add metadata
        play_data = {
            **play,
            'game_id': scenario['game_id'],
            'play_number': i,
            'shotgun': play.get('shotgun', 1),
            'no_huddle': play.get('no_huddle', 0),
            'goal_to_go': play.get('goal_to_go', 0),
            'defenders_in_box': random.randint(5, 8),
            'number_of_pass_rushers': random.randint(3, 6),
            'posteam_type': 'home' if i % 2 == 0 else 'away',
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"\n📍 Play {i}/{len(scenario['plays'])}: {play['desc']}")
        print(f"   Down: {play['down']} | Distance: {play['ydstogo']} | Yard Line: {100 - play['yardline_100']}")
        print(f"   Time: {play['half_seconds_remaining']//60}:{play['half_seconds_remaining']%60:02d} | Score Diff: {play['score_differential']:+d}")
        
        response = send_to_kinesis(client, play_data)
        if response:
            print(f"   ✅ Sent to Kinesis (Shard: {response['ShardId'][:20]}...)")
        
        if i < len(scenario['plays']):
            print(f"   ⏳ Next play in {delay} seconds...")
            time.sleep(delay)
    
    print(f"\n🏁 Scenario '{scenario['name']}' complete!")

def run_historical_replay(client, num_plays=20, delay=2):
    """Replay historical plays from CSV"""
    print("\n📼 Loading historical data...")
    
    try:
        df = pd.read_csv('/Users/adithyahnair/nfl-project/data/raw/pbp_2023.csv', low_memory=False)
        df = df[df['play_type'].isin(['run', 'pass'])].dropna(subset=['down', 'ydstogo', 'yardline_100'])
        
        # Pick a random game
        games = df['game_id'].unique()
        game_id = random.choice(games)
        game_plays = df[df['game_id'] == game_id].head(num_plays)
        
        print(f"🏈 Replaying {len(game_plays)} plays from game {game_id}")
        print(f"{'='*60}")
        
        for i, (_, row) in enumerate(game_plays.iterrows(), 1):
            play_data = {
                'game_id': str(row['game_id']),
                'down': int(row['down']) if pd.notna(row['down']) else 1,
                'ydstogo': int(row['ydstogo']) if pd.notna(row['ydstogo']) else 10,
                'yardline_100': int(row['yardline_100']) if pd.notna(row['yardline_100']) else 75,
                'qtr': int(row['qtr']) if pd.notna(row['qtr']) else 1,
                'half_seconds_remaining': int(row['half_seconds_remaining']) if pd.notna(row['half_seconds_remaining']) else 900,
                'score_differential': int(row['score_differential']) if pd.notna(row['score_differential']) else 0,
                'posteam': str(row['posteam']) if pd.notna(row['posteam']) else 'UNK',
                'defteam': str(row['defteam']) if pd.notna(row['defteam']) else 'UNK',
                'shotgun': int(row['shotgun']) if pd.notna(row['shotgun']) else 0,
                'no_huddle': int(row['no_huddle']) if pd.notna(row['no_huddle']) else 0,
                'goal_to_go': int(row['goal_to_go']) if pd.notna(row['goal_to_go']) else 0,
                'defenders_in_box': int(row['defenders_in_box']) if pd.notna(row['defenders_in_box']) else 6,
                'number_of_pass_rushers': int(row['number_of_pass_rushers']) if pd.notna(row['number_of_pass_rushers']) else 4,
                'play_type': str(row['play_type']),
                'posteam_type': 'home' if row.get('posteam_type') == 'home' else 'away',
                'desc': str(row['desc'])[:100] if pd.notna(row.get('desc')) else '',
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n📍 Play {i}/{len(game_plays)}")
            print(f"   {play_data['posteam']} vs {play_data['defteam']}")
            print(f"   {play_data['down']} & {play_data['ydstogo']} at {100 - play_data['yardline_100']}")
            
            response = send_to_kinesis(client, play_data)
            if response:
                print(f"   ✅ Sent to Kinesis")
            
            if i < len(game_plays):
                time.sleep(delay)
        
        print(f"\n🏁 Historical replay complete!")
        
    except Exception as e:
        print(f"Error loading historical data: {e}")

def main():
    print("\n" + "="*60)
    print("🏈 NFL LIVE DEMO SIMULATOR")
    print("="*60)
    
    # Initialize Kinesis client
    try:
        client = boto3.client('kinesis', region_name=REGION)
        # Verify stream exists
        client.describe_stream(StreamName=STREAM_NAME)
        print(f"✅ Connected to Kinesis stream: {STREAM_NAME}")
    except Exception as e:
        print(f"❌ Kinesis error: {e}")
        print("Make sure the stream exists: aws kinesis create-stream --stream-name nfl-play-stream --shard-count 1")
        return
    
    while True:
        print("\n" + "-"*40)
        print("Select Demo Mode:")
        print("  1. 4th Quarter Comeback (KC vs SF)")
        print("  2. Red Zone Showdown (DAL vs PHI)")
        print("  3. Two Minute Drill (BUF vs MIA)")
        print("  4. All Scenarios (Sequential)")
        print("  5. Historical Replay (Random 2023 Game)")
        print("  6. Exit")
        print("-"*40)
        
        choice = input("Enter choice (1-6): ").strip()
        
        if choice == '1':
            run_scenario(client, DEMO_SCENARIOS[0])
        elif choice == '2':
            run_scenario(client, DEMO_SCENARIOS[1])
        elif choice == '3':
            run_scenario(client, DEMO_SCENARIOS[2])
        elif choice == '4':
            for scenario in DEMO_SCENARIOS:
                run_scenario(client, scenario)
                print("\n⏳ Next scenario in 5 seconds...")
                time.sleep(5)
        elif choice == '5':
            run_historical_replay(client)
        elif choice == '6':
            print("\n👋 Goodbye!")
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
