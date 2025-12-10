"""
AWS Lambda: ESPN NFL Live Poller
Triggered by EventBridge every 1 minute during game time
"""

import json
import boto3
import urllib.request
import urllib.error
from datetime import datetime

KINESIS_STREAM = 'nfl-play-stream'
ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

kinesis = boto3.client('kinesis')

def get_scoreboard():
    try:
        req = urllib.request.Request(f"{ESPN_BASE_URL}/scoreboard")
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching scoreboard: {e}")
    return None

def get_game_details(game_id):
    try:
        req = urllib.request.Request(f"{ESPN_BASE_URL}/summary?event={game_id}")
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching game {game_id}: {e}")
    return None

def parse_situation(game_data, game_id, home_team, away_team, home_score, away_score):
    try:
        situation = game_data.get('situation', {})
        if not situation:
            return None
        
        down = situation.get('down', 0)
        distance = situation.get('distance', 0)
        yard_line = situation.get('yardLine', 50)
        possession = situation.get('possession', '')
        is_home_possession = possession == home_team
        
        if is_home_possession:
            yardline_100 = 100 - yard_line if yard_line else 75
        else:
            yardline_100 = yard_line if yard_line else 75
        
        clock = situation.get('clock', {})
        period = situation.get('period', 1)
        display_clock = clock.get('displayValue', '15:00') if isinstance(clock, dict) else '15:00'
        
        try:
            parts = display_clock.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1]) if len(parts) > 1 else 0
            half_seconds = minutes * 60 + seconds
            if period in [1, 3]:
                half_seconds += 900
        except:
            half_seconds = 900
        
        if is_home_possession:
            score_diff = home_score - away_score
            posteam, defteam = home_team, away_team
        else:
            score_diff = away_score - home_score
            posteam, defteam = away_team, home_team
        
        return {
            'game_id': str(game_id),
            'down': down,
            'ydstogo': distance,
            'yardline_100': yardline_100,
            'qtr': period,
            'half_seconds_remaining': half_seconds,
            'score_differential': score_diff,
            'posteam': posteam,
            'defteam': defteam,
            'home_team': home_team,
            'away_team': away_team,
            'home_score': home_score,
            'away_score': away_score,
            'posteam_type': 'home' if is_home_possession else 'away',
            'goal_to_go': 1 if yard_line and yard_line <= distance else 0,
            'shotgun': 1,
            'no_huddle': 0,
            'defenders_in_box': 6,
            'number_of_pass_rushers': 4,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'espn_lambda'
        }
    except Exception as e:
        print(f"Error parsing situation: {e}")
        return None

def send_to_kinesis(play_data):
    try:
        response = kinesis.put_record(
            StreamName=KINESIS_STREAM,
            Data=json.dumps(play_data).encode('utf-8'),
            PartitionKey=str(play_data.get('game_id', 'default'))
        )
        return response
    except Exception as e:
        print(f"Error sending to Kinesis: {e}")
        return None

def lambda_handler(event, context):
    print(f"ESPN Poller triggered at {datetime.utcnow().isoformat()}")
    
    scoreboard = get_scoreboard()
    if not scoreboard:
        return {'statusCode': 500, 'body': 'Failed to fetch scoreboard'}
    
    events = scoreboard.get('events', [])
    live_games = 0
    plays_sent = 0
    
    for event_data in events:
        game_id = event_data.get('id')
        status = event_data.get('status', {}).get('type', {}).get('state', '')
        
        if status != 'in':
            continue
        
        live_games += 1
        competitors = event_data.get('competitions', [{}])[0].get('competitors', [])
        home_team = away_team = ''
        home_score = away_score = 0
        
        for comp in competitors:
            abbr = comp.get('team', {}).get('abbreviation', '')
            score = int(comp.get('score', 0))
            if comp.get('homeAway') == 'home':
                home_team, home_score = abbr, score
            else:
                away_team, away_score = abbr, score
        
        print(f"Live: {away_team} @ {home_team} ({away_score}-{home_score})")
        
        game_data = get_game_details(game_id)
        if not game_data:
            continue
        
        play_data = parse_situation(game_data, game_id, home_team, away_team, home_score, away_score)
        
        if play_data and play_data['down'] > 0:
            response = send_to_kinesis(play_data)
            if response:
                plays_sent += 1
                print(f"Sent: {play_data['posteam']} {play_data['down']}&{play_data['ydstogo']}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'live_games': live_games,
            'plays_sent': plays_sent,
            'timestamp': datetime.utcnow().isoformat()
        })
    }
