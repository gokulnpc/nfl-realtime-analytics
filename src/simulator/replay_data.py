"""
NFL Data Replay Simulator
Replays historical play-by-play data as simulated streaming events.
"""

import pandas as pd
import json
import time
import sys
from datetime import datetime

class NFLDataSimulator:
    def __init__(self, data_path, delay=1.0):
        """
        Initialize simulator with historical data.
        
        Args:
            data_path: Path to CSV file with play-by-play data
            delay: Seconds between each play (default 1.0)
        """
        self.delay = delay
        print(f"Loading data from {data_path}...")
        self.df = pd.read_csv(data_path)
        print(f"Loaded {len(self.df)} plays")
        
    def get_play_event(self, row):
        """Convert a dataframe row to a play event dictionary."""
        return {
            "game_id": str(row.get("game_id", "")),
            "play_id": int(row.get("play_id", 0)),
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
    
    def replay_game(self, game_id):
        """Replay all plays from a specific game."""
        game_plays = self.df[self.df["game_id"] == game_id]
        print(f"Replaying {len(game_plays)} plays from game {game_id}")
        
        for idx, row in game_plays.iterrows():
            event = self.get_play_event(row)
            yield event
            time.sleep(self.delay)
    
    def replay_all(self, max_plays=None):
        """Replay all plays in the dataset."""
        count = 0
        for idx, row in self.df.iterrows():
            if max_plays and count >= max_plays:
                break
            event = self.get_play_event(row)
            yield event
            count += 1
            time.sleep(self.delay)
    
    def get_unique_games(self):
        """Return list of unique game IDs."""
        return self.df["game_id"].unique().tolist()


def main():
    # Default path to data
    data_path = "/Users/adithyahnair/nfl-project/data/raw/pbp_2023.csv"
    
    # Parse command line args
    if len(sys.argv) > 1:
        data_path = sys.argv[1]
    
    delay = 0.5  # Half second between plays
    if len(sys.argv) > 2:
        delay = float(sys.argv[2])
    
    # Create simulator
    sim = NFLDataSimulator(data_path, delay=delay)
    
    # Show available games
    games = sim.get_unique_games()
    print(f"\nFound {len(games)} unique games")
    print(f"First 5 games: {games[:5]}")
    
    # Replay first 10 plays
    print("\n--- Replaying first 10 plays ---\n")
    for i, event in enumerate(sim.replay_all(max_plays=10)):
        print(f"Play {i+1}: {event['posteam']} vs {event['defteam']} | "
              f"Q{event['quarter']} | {event['down']}&{event['ydstogo']} | "
              f"Type: {event['play_type']} | EPA: {event['epa']:.2f}")


if __name__ == "__main__":
    main()
