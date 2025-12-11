"""
AWS Lambda: ESPN NFL Live Poller - FULL DATA CAPTURE
Captures ALL available ESPN data and sends to Kinesis
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
    """Fetch current NFL scoreboard"""
    try:
        req = urllib.request.Request(f"{ESPN_BASE_URL}/scoreboard")
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching scoreboard: {e}")
    return None

def get_game_summary(game_id):
    """Fetch detailed game summary"""
    try:
        req = urllib.request.Request(f"{ESPN_BASE_URL}/summary?event={game_id}")
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching summary {game_id}: {e}")
    return None

def extract_full_data(event_data, summary_data):
    """Extract ALL available data from ESPN"""
    
    game_id = event_data.get('id')
    competition = event_data.get('competitions', [{}])[0]
    status = event_data.get('status', {})
    status_type = status.get('type', {})
    
    # ========== TEAM DATA ==========
    competitors = competition.get('competitors', [])
    home_team = {}
    away_team = {}
    
    for comp in competitors:
        team_info = comp.get('team', {})
        team_data = {
            'id': team_info.get('id'),
            'abbreviation': team_info.get('abbreviation'),
            'name': team_info.get('name'),
            'displayName': team_info.get('displayName'),
            'shortDisplayName': team_info.get('shortDisplayName'),
            'color': team_info.get('color'),
            'alternateColor': team_info.get('alternateColor'),
            'logo': team_info.get('logo'),
            'score': int(comp.get('score', 0)),
            'winner': comp.get('winner'),
            'records': []
        }
        
        # Records (W-L)
        for record in comp.get('records', []):
            team_data['records'].append({
                'type': record.get('type'),
                'summary': record.get('summary')
            })
        
        # Leaders
        team_data['leaders'] = {}
        for leader in comp.get('leaders', []):
            leader_name = leader.get('name', '')
            if leader.get('leaders'):
                top_leader = leader['leaders'][0]
                athlete = top_leader.get('athlete', {})
                team_data['leaders'][leader_name] = {
                    'name': athlete.get('displayName'),
                    'position': athlete.get('position', {}).get('abbreviation'),
                    'value': top_leader.get('displayValue')
                }
        
        if comp.get('homeAway') == 'home':
            home_team = team_data
        else:
            away_team = team_data
    
    # ========== SITUATION DATA (Current Play) ==========
    situation = {}
    if summary_data:
        situation = summary_data.get('situation', {})
    
    down = situation.get('down', 0)
    distance = situation.get('distance', 0)
    yard_line = situation.get('yardLine', 50)
    possession = situation.get('possession', '')
    
    is_home_possession = possession == home_team.get('abbreviation')
    
    if is_home_possession:
        yardline_100 = 100 - yard_line if yard_line else 75
        score_diff = home_team.get('score', 0) - away_team.get('score', 0)
        posteam = home_team.get('abbreviation')
        defteam = away_team.get('abbreviation')
    else:
        yardline_100 = yard_line if yard_line else 75
        score_diff = away_team.get('score', 0) - home_team.get('score', 0)
        posteam = away_team.get('abbreviation')
        defteam = home_team.get('abbreviation')
    
    # Clock
    period = status.get('period', situation.get('period', 1))
    display_clock = status.get('displayClock', '15:00')
    try:
        parts = display_clock.split(':')
        minutes = int(parts[0])
        seconds = int(parts[1]) if len(parts) > 1 else 0
        half_seconds = minutes * 60 + seconds
        if period in [1, 3]:
            half_seconds += 900
    except:
        half_seconds = 900
    
    # ========== WEATHER DATA ==========
    weather = event_data.get('weather', {})
    weather_data = {
        'temperature': weather.get('temperature'),
        'displayValue': weather.get('displayValue'),
        'conditionId': weather.get('conditionId'),
        'highTemperature': weather.get('highTemperature'),
        'gust': weather.get('gust')
    }
    
    # ========== VENUE DATA ==========
    venue = competition.get('venue', {})
    venue_data = {
        'id': venue.get('id'),
        'name': venue.get('fullName'),
        'city': venue.get('address', {}).get('city'),
        'state': venue.get('address', {}).get('state'),
        'indoor': venue.get('indoor', False),
        'grass': venue.get('grass', True),
        'capacity': venue.get('capacity')
    }
    
    # ========== ODDS DATA ==========
    odds_data = {}
    odds_list = competition.get('odds', [])
    if odds_list:
        odds = odds_list[0]
        odds_data = {
            'provider': odds.get('provider', {}).get('name'),
            'spread': odds.get('spread'),
            'spreadOdds': odds.get('spreadOdds'),
            'overUnder': odds.get('overUnder'),
            'overOdds': odds.get('overOdds'),
            'underOdds': odds.get('underOdds'),
            'homeMoneyLine': odds.get('homeTeamOdds', {}).get('moneyLine'),
            'awayMoneyLine': odds.get('awayTeamOdds', {}).get('moneyLine'),
            'details': odds.get('details')
        }
    
    # ========== WIN PROBABILITY (ESPN PREDICTOR) ==========
    predictor = {}
    if summary_data and 'predictor' in summary_data:
        pred = summary_data['predictor']
        predictor = {
            'homeWinProbability': pred.get('homeTeam', {}).get('gameProjection'),
            'awayWinProbability': pred.get('awayTeam', {}).get('gameProjection')
        }
    
    # ========== WIN PROBABILITY HISTORY ==========
    win_prob_history = []
    if summary_data and 'winprobability' in summary_data:
        for wp in summary_data.get('winprobability', [])[-10:]:  # Last 10
            win_prob_history.append({
                'playId': wp.get('playId'),
                'homeWinPercentage': wp.get('homeWinPercentage'),
                'secondsLeft': wp.get('secondsLeft')
            })
    
    # ========== BROADCASTS ==========
    broadcasts = []
    for broadcast in competition.get('broadcasts', []):
        for name in broadcast.get('names', []):
            broadcasts.append(name)
    
    # ========== GAME INFO ==========
    game_info = {}
    if summary_data and 'gameInfo' in summary_data:
        gi = summary_data['gameInfo']
        game_info = {
            'attendance': gi.get('attendance'),
            'weatherCondition': gi.get('weather', {}).get('displayValue'),
            'weatherTemp': gi.get('weather', {}).get('temperature')
        }
    
    # ========== LAST PLAY ==========
    last_play = {}
    if situation.get('lastPlay'):
        lp = situation['lastPlay']
        last_play = {
            'id': lp.get('id'),
            'text': lp.get('text'),
            'type': lp.get('type', {}).get('text'),
            'scoreValue': lp.get('scoreValue', 0),
            'team': lp.get('team', {}).get('abbreviation'),
            'athletesInvolved': [a.get('displayName') for a in lp.get('athletesInvolved', [])]
        }
    
    # ========== BUILD COMPLETE RECORD ==========
    full_data = {
        # Identifiers
        'game_id': game_id,
        'event_uid': event_data.get('uid'),
        'timestamp': datetime.utcnow().isoformat(),
        'source': 'espn_lambda_full',
        
        # Game Status
        'status': {
            'state': status_type.get('state'),
            'detail': status_type.get('detail'),
            'shortDetail': status_type.get('shortDetail'),
            'description': status_type.get('description'),
            'period': period,
            'displayClock': display_clock,
            'completed': status_type.get('completed', False)
        },
        
        # Current Situation (for ML models)
        'situation': {
            'down': down,
            'distance': distance,
            'ydstogo': distance,
            'yardLine': yard_line,
            'yardline_100': yardline_100,
            'possession': possession,
            'isRedZone': situation.get('isRedZone', False),
            'downDistanceText': situation.get('downDistanceText'),
            'shortDownDistanceText': situation.get('shortDownDistanceText'),
            'possessionText': situation.get('possessionText')
        },
        
        # Derived fields for ML (flat structure)
        'down': down,
        'ydstogo': distance,
        'yardline_100': yardline_100,
        'qtr': period,
        'half_seconds_remaining': half_seconds,
        'score_differential': score_diff,
        'posteam': posteam,
        'defteam': defteam,
        'posteam_type': 'home' if is_home_possession else 'away',
        'goal_to_go': 1 if yard_line and yard_line <= distance else 0,
        
        # Defaults for ML (not available from ESPN)
        'shotgun': 1,
        'no_huddle': 0,
        'defenders_in_box': 6,
        'number_of_pass_rushers': 4,
        
        # Home Team
        'home_team': home_team.get('abbreviation'),
        'home_team_full': home_team,
        'home_score': home_team.get('score', 0),
        
        # Away Team
        'away_team': away_team.get('abbreviation'),
        'away_team_full': away_team,
        'away_score': away_team.get('score', 0),
        
        # Weather
        'weather': weather_data,
        
        # Venue
        'venue': venue_data,
        
        # Odds & Betting
        'odds': odds_data,
        
        # ESPN Win Probability
        'predictor': predictor,
        'winProbabilityHistory': win_prob_history,
        
        # Broadcasts
        'broadcasts': broadcasts,
        
        # Game Info
        'gameInfo': game_info,
        
        # Last Play
        'lastPlay': last_play,
        
        # Event metadata
        'event': {
            'name': event_data.get('name'),
            'shortName': event_data.get('shortName'),
            'date': event_data.get('date'),
            'week': event_data.get('week', {}).get('number'),
            'seasonType': event_data.get('season', {}).get('type'),
            'neutralSite': competition.get('neutralSite', False),
            'attendance': competition.get('attendance')
        }
    }
    
    return full_data

def send_to_kinesis(data):
    """Send data to Kinesis stream"""
    try:
        response = kinesis.put_record(
            StreamName=KINESIS_STREAM,
            Data=json.dumps(data).encode('utf-8'),
            PartitionKey=str(data.get('game_id', 'default'))
        )
        return response
    except Exception as e:
        print(f"Error sending to Kinesis: {e}")
        return None

def lambda_handler(event, context):
    """Main Lambda handler"""
    print(f"ESPN Full Poller triggered at {datetime.utcnow().isoformat()}")
    
    scoreboard = get_scoreboard()
    if not scoreboard:
        return {'statusCode': 500, 'body': 'Failed to fetch scoreboard'}
    
    events = scoreboard.get('events', [])
    live_games = 0
    plays_sent = 0
    
    for event_data in events:
        game_id = event_data.get('id')
        status = event_data.get('status', {}).get('type', {}).get('state', '')
        
        # Only process live games
        if status != 'in':
            continue
        
        live_games += 1
        
        # Get detailed summary
        summary_data = get_game_summary(game_id)
        
        # Extract full data
        full_data = extract_full_data(event_data, summary_data)
        
        if full_data and full_data.get('down', 0) > 0:
            response = send_to_kinesis(full_data)
            if response:
                plays_sent += 1
                print(f"Sent: {full_data['posteam']} vs {full_data['defteam']} - "
                      f"{full_data['down']}&{full_data['ydstogo']} at {full_data['yardline_100']} "
                      f"| ESPN WP: {full_data.get('predictor', {}).get('homeWinProbability', 'N/A')}%")
    
    result = {
        'statusCode': 200,
        'body': json.dumps({
            'live_games': live_games,
            'plays_sent': plays_sent,
            'timestamp': datetime.utcnow().isoformat(),
            'data_captured': 'FULL'
        })
    }
    
    print(f"Done: {live_games} live games, {plays_sent} plays sent (FULL DATA)")
    return result
