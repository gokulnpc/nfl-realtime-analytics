"""
ESPN Live Data Poller
Fetches NFL game data from ESPN API and pushes to Kinesis
"""

import requests
import json
import time
import boto3
from datetime import datetime

class ESPNPoller:
    def __init__(self, kinesis_stream='nfl-play-events', region='us-east-1'):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
        self.kinesis = boto3.client('kinesis', region_name=region)
        self.stream_name = kinesis_stream
    
    def get_scoreboard(self):
        """Get current NFL scoreboard with live games."""
        url = f"{self.base_url}/scoreboard"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    
    def get_game_details(self, game_id):
        """Get detailed play-by-play for a specific game."""
        url = f"{self.base_url}/summary?event={game_id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    
    def parse_play(self, play, game_id, home_team, away_team):
        """Convert ESPN play data to our schema."""
        return {
            "game_id": str(game_id),
            "play_id": play.get("id", 0),
            "quarter": play.get("period", {}).get("number", 0),
            "down": play.get("start", {}).get("down", 0),
            "ydstogo": play.get("start", {}).get("distance", 0),
            "yardline_100": play.get("start", {}).get("yardsToEndzone", 0),
            "posteam": play.get("start", {}).get("team", {}).get("id", ""),
            "defteam": "",
            "play_type": play.get("type", {}).get("text", ""),
            "shotgun": 0,
            "no_huddle": 0,
            "offense_formation": "",
            "defenders_in_box": 0,
            "number_of_pass_rushers": 0,
            "was_pressure": 0,
            "time_to_throw": 0.0,
            "epa": 0.0,
            "home_team": home_team,
            "away_team": away_team,
            "description": play.get("text", ""),
            "event_time": datetime.now().isoformat()
        }
    
    def send_to_kinesis(self, play_data):
        """Send play data to Kinesis stream."""
        try:
            response = self.kinesis.put_record(
                StreamName=self.stream_name,
                Data=json.dumps(play_data).encode('utf-8'),
                PartitionKey=str(play_data.get('game_id', 'default'))
            )
            return response
        except Exception as e:
            print(f"Error sending to Kinesis: {e}")
            return None
    
    def poll_live_games(self, interval=30):
        """Continuously poll for live game updates."""
        print(f"Starting ESPN poller (interval: {interval}s)")
        print(f"Sending to Kinesis stream: {self.stream_name}")
        
        seen_plays = set()
        
        while True:
            try:
                scoreboard = self.get_scoreboard()
                if not scoreboard:
                    print("Failed to get scoreboard")
                    time.sleep(interval)
                    continue
                
                events = scoreboard.get("events", [])
                print(f"\nFound {len(events)} games")
                
                for event in events:
                    game_id = event.get("id")
                    status = event.get("status", {}).get("type", {}).get("state", "")
                    
                    # Get team names
                    competitors = event.get("competitions", [{}])[0].get("competitors", [])
                    home_team = ""
                    away_team = ""
                    for comp in competitors:
                        if comp.get("homeAway") == "home":
                            home_team = comp.get("team", {}).get("abbreviation", "")
                        else:
                            away_team = comp.get("team", {}).get("abbreviation", "")
                    
                    print(f"  {away_team} @ {home_team} - Status: {status}")
                    
                    # Only process live games
                    if status == "in":
                        details = self.get_game_details(game_id)
                        if details:
                            drives = details.get("drives", {}).get("previous", [])
                            for drive in drives:
                                plays = drive.get("plays", [])
                                for play in plays:
                                    play_id = play.get("id")
                                    play_key = f"{game_id}_{play_id}"
                                    
                                    if play_key not in seen_plays:
                                        seen_plays.add(play_key)
                                        play_data = self.parse_play(play, game_id, home_team, away_team)
                                        
                                        response = self.send_to_kinesis(play_data)
                                        if response:
                                            print(f"    Sent play: {play_data['description'][:50]}...")
                
                print(f"\nWaiting {interval}s for next poll...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\nStopping poller...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(interval)


def test_espn_api():
    """Test ESPN API connection without Kinesis."""
    print("Testing ESPN API connection...\n")
    
    poller = ESPNPoller.__new__(ESPNPoller)
    poller.base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    
    scoreboard = poller.get_scoreboard()
    if scoreboard:
        events = scoreboard.get("events", [])
        print(f"Found {len(events)} games:\n")
        
        for event in events:
            name = event.get("name", "Unknown")
            status = event.get("status", {}).get("type", {}).get("description", "")
            print(f"  {name}")
            print(f"    Status: {status}\n")
    else:
        print("Failed to connect to ESPN API")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_espn_api()
    else:
        poller = ESPNPoller()
        poller.poll_live_games(interval=30)
