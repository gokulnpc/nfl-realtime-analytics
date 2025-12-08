"""
ESPN Live Data Poller
Fetches NFL game data from ESPN API and pushes to Kinesis
"""

import requests
import json
import time
import argparse
import logging
import sys
import os
from datetime import datetime

# Add src to path to allow imports if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    from src.streaming.kinesis_producer import KinesisProducer
except ImportError:
    # Fallback for direct execution if path setup fails
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../streaming')))
        from kinesis_producer import KinesisProducer
    except ImportError:
        print("Could not import KinesisProducer. Ensure you are running from the project root.")
        sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ESPNPoller:
    def __init__(self, kinesis_stream='nfl-play-events', region='us-east-1', dry_run=False):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
        self.stream_name = kinesis_stream
        self.dry_run = dry_run
        
        if not self.dry_run:
            self.producer = KinesisProducer(stream_name=kinesis_stream, region=region)
        else:
            self.producer = None
            logger.info("Running in DRY RUN mode - no data will be sent to Kinesis")

    def get_scoreboard(self):
        """Get current NFL scoreboard with live games."""
        url = f"{self.base_url}/scoreboard"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get scoreboard: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching scoreboard: {e}")
        return None
    
    def get_game_details(self, game_id):
        """Get detailed play-by-play for a specific game."""
        url = f"{self.base_url}/summary?event={game_id}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get game details for {game_id}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching game details for {game_id}: {e}")
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
            "defteam": "", # Logic to determine defteam could be improved if available
            "play_type": play.get("type", {}).get("text", ""),
            "shotgun": 0, # Not always available in raw ESPN feed
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
        if self.dry_run:
            logger.info(f"[DRY RUN] Would send play: {play_data['game_id']} - {play_data['description'][:50]}...")
            return {"ShardId": "dry-run-shard"}
            
        try:
            response = self.producer.send_record(play_data)
            return response
        except Exception as e:
            logger.error(f"Error sending to Kinesis: {e}")
            return None
    
    def poll_live_games(self, interval=30):
        """Continuously poll for live game updates."""
        logger.info(f"Starting ESPN poller (interval: {interval}s)")
        if not self.dry_run:
            logger.info(f"Sending to Kinesis stream: {self.stream_name}")
        
        seen_plays = set()
        
        while True:
            try:
                scoreboard = self.get_scoreboard()
                if not scoreboard:
                    logger.warning("No scoreboard data received")
                    time.sleep(interval)
                    continue
                
                events = scoreboard.get("events", [])
                live_games = 0
                
                for event in events:
                    game_id = event.get("id")
                    status = event.get("status", {}).get("type", {}).get("state", "")
                    
                    # Get team names
                    competitors = event.get("competitions", [{}])[0].get("competitors", [])
                    home_team = ""
                    away_team = ""
                    for comp in competitors:
                        val = comp.get("team", {}).get("abbreviation", "")
                        if comp.get("homeAway") == "home":
                            home_team = val
                        else:
                            away_team = val
                    
                    # Log interesting statuses
                    if status == "in":
                        live_games += 1
                        logger.info(f"Processing Live Game: {away_team} @ {home_team}")
                        
                        details = self.get_game_details(game_id)
                        if details:
                            drives = details.get("drives", {}).get("previous", [])
                            # Add current drive(s) too ? Usually 'previous' has completed drives, 
                            # 'current' has the active one. Checking checks to be thorough.
                            current_drive = details.get("drives", {}).get("current", {})
                            if current_drive:
                                drives.append(current_drive)

                            new_plays_count = 0
                            for drive in drives:
                                plays = drive.get("plays", [])
                                for play in plays:
                                    play_id = play.get("id")
                                    play_key = f"{game_id}_{play_id}"
                                    
                                    if play_key not in seen_plays:
                                        seen_plays.add(play_key)
                                        # Parse and send
                                        play_data = self.parse_play(play, game_id, home_team, away_team)
                                        
                                        response = self.send_to_kinesis(play_data)
                                        if response:
                                            new_plays_count += 1
                                            if not self.dry_run:
                                                logger.info(f"Sent play: {play_data['description'][:50]}...")
                            
                            if new_plays_count > 0:
                                logger.info(f"  Processed {new_plays_count} new plays for {away_team} vs {home_team}")

                    elif status == "pre":
                        # logger.debug(f"Upcoming: {away_team} @ {home_team}")
                        pass
                
                if live_games == 0:
                    logger.info("No live games found. Waiting...")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Stopping poller...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in polling loop: {e}", exc_info=True)
                time.sleep(interval)


def test_espn_api():
    """Test ESPN API connection."""
    logger.info("Testing ESPN API connection...")
    
    poller = ESPNPoller(dry_run=True)
    
    scoreboard = poller.get_scoreboard()
    if scoreboard:
        events = scoreboard.get("events", [])
        logger.info(f"Success! Found {len(events)} games in scoreboard.")
        
        for event in events:
            date_str = event.get("date", "")
            status = event.get("status", {}).get("type", {}).get("description", "")
            name = event.get("name", "Unknown Game")
            logger.info(f"  {name} ({date_str}) - {status}")
        return True
    else:
        logger.error("Failed to connect to ESPN API")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESPN Live Data Poller")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending to Kinesis")
    parser.add_argument("--test", action="store_true", help="Test API connection and exit")
    
    args = parser.parse_args()
    
    if args.test:
        test_espn_api()
    else:
        poller = ESPNPoller(kinesis_stream='nfl-play-events', dry_run=args.dry_run)
        poller.poll_live_games(interval=args.interval)
