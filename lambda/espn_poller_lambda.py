"""
AWS Lambda: ESPN NFL Live Poller - FULL DATA CAPTURE v2
Captures ALL available ESPN data including headshots, full stats, enhanced odds
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

def extract_leader_data(leader_info):
    """Extract full leader data including headshot, jersey, full stat line"""
    if not leader_info or not leader_info.get('leaders'):
        return None
    
    top_leader = leader_info['leaders'][0]
    athlete = top_leader.get('athlete', {})
    
    return {
        'name': athlete.get('fullName') or athlete.get('displayName'),
        'shortName': athlete.get('shortName'),
        'displayName': athlete.get('displayName'),
        'headshot': athlete.get('headshot'),
        'jersey': athlete.get('jersey'),
        'position': athlete.get('position', {}).get('abbreviation'),
        'teamId': athlete.get('team', {}).get('id'),
        'playerId': athlete.get('id'),
        'displayValue': top_leader.get('displayValue'),  # Full stat line: "299/474, 3398 YDS, 22 TD"
        'value': top_leader.get('value'),  # Numeric value for sorting
        'active': athlete.get('active', True)
    }

def extract_odds_data(odds_list):
    """Extract comprehensive odds data including moneylines and spread odds"""
    if not odds_list:
        return {}
    
    odds = odds_list[0]
    
    # Extract moneyline data
    moneyline = odds.get('moneyline', {})
    home_ml = moneyline.get('home', {}).get('close', {}).get('odds')
    away_ml = moneyline.get('away', {}).get('close', {}).get('odds')
    
    # Extract point spread data
    point_spread = odds.get('pointSpread', {})
    home_spread = point_spread.get('home', {}).get('close', {})
    away_spread = point_spread.get('away', {}).get('close', {})
    
    # Extract total (over/under) data
    total = odds.get('total', {})
    over_data = total.get('over', {}).get('close', {})
    under_data = total.get('under', {}).get('close', {})
    
    return {
        'provider': odds.get('provider', {}).get('name'),
        'providerId': odds.get('provider', {}).get('id'),
        'details': odds.get('details'),  # e.g., "KC -5.5"
        'spread': odds.get('spread'),
        'overUnder': odds.get('overUnder'),
        
        # Enhanced moneyline
        'moneyline': {
            'home': home_ml,
            'away': away_ml,
            'homeOpen': moneyline.get('home', {}).get('open', {}).get('odds'),
            'awayOpen': moneyline.get('away', {}).get('open', {}).get('odds')
        },
        
        # Enhanced spread
        'pointSpread': {
            'home': {
                'line': home_spread.get('line'),
                'odds': home_spread.get('odds')
            },
            'away': {
                'line': away_spread.get('line'),
                'odds': away_spread.get('odds')
            }
        },
        
        # Enhanced total
        'total': {
            'over': {
                'line': over_data.get('line'),
                'odds': over_data.get('odds')
            },
            'under': {
                'line': under_data.get('line'),
                'odds': under_data.get('odds')
            }
        },
        
        # Favorite info
        'homeFavorite': odds.get('homeTeamOdds', {}).get('favorite', False),
        'awayFavorite': odds.get('awayTeamOdds', {}).get('favorite', False),
        
        # Legacy fields for backwards compatibility
        'homeMoneyLine': home_ml,
        'awayMoneyLine': away_ml
    }

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
            'uid': team_info.get('uid'),
            'abbreviation': team_info.get('abbreviation'),
            'name': team_info.get('name'),
            'displayName': team_info.get('displayName'),
            'shortDisplayName': team_info.get('shortDisplayName'),
            'color': team_info.get('color'),
            'alternateColor': team_info.get('alternateColor'),
            'logo': team_info.get('logo'),
            'score': int(comp.get('score', 0)),
            'winner': comp.get('winner'),
            'homeAway': comp.get('homeAway'),
            
            # Enhanced records structure
            'records': {
                'overall': None,
                'home': None,
                'away': None
            }
        }
        
        # Records (W-L) - Parse into structured format
        for record in comp.get('records', []):
            record_type = record.get('type', record.get('name', ''))
            summary = record.get('summary')
            if record_type in ['total', 'overall']:
                team_data['records']['overall'] = summary
            elif record_type == 'home':
                team_data['records']['home'] = summary
            elif record_type in ['road', 'away']:
                team_data['records']['away'] = summary
        
        # Legacy record format for compatibility
        team_data['record'] = team_data['records']['overall']
        
        # Leaders - Enhanced with full data including headshots
        team_data['leaders'] = {
            'passing': None,
            'rushing': None,
            'receiving': None
        }
        
        for leader in comp.get('leaders', []):
            leader_name = leader.get('name', '').lower()
            leader_data = extract_leader_data(leader)
            
            if 'passing' in leader_name:
                team_data['leaders']['passing'] = leader_data
            elif 'rushing' in leader_name:
                team_data['leaders']['rushing'] = leader_data
            elif 'receiving' in leader_name:
                team_data['leaders']['receiving'] = leader_data
        
        if comp.get('homeAway') == 'home':
            home_team = team_data
        else:
            away_team = team_data
    
    # ========== GAME-LEVEL LEADERS ==========
    # These are the top leaders across both teams
    game_leaders = {
        'passing': None,
        'rushing': None,
        'receiving': None
    }
    
    for leader in competition.get('leaders', []):
        leader_name = leader.get('name', '').lower()
        leader_data = extract_leader_data(leader)
        
        if 'passing' in leader_name:
            game_leaders['passing'] = leader_data
        elif 'rushing' in leader_name:
            game_leaders['rushing'] = leader_data
        elif 'receiving' in leader_name:
            game_leaders['receiving'] = leader_data
    
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
        'gust': weather.get('gust'),
        'link': weather.get('link', {}).get('href')
    }
    
    # ========== VENUE DATA ==========
    venue = competition.get('venue', {})
    venue_data = {
        'id': venue.get('id'),
        'name': venue.get('fullName'),
        'shortName': venue.get('name'),
        'city': venue.get('address', {}).get('city'),
        'state': venue.get('address', {}).get('state'),
        'country': venue.get('address', {}).get('country'),
        'indoor': venue.get('indoor', False),
        'grass': venue.get('grass', True),
        'capacity': venue.get('capacity')
    }
    
    # ========== ODDS DATA - Enhanced ==========
    odds_data = extract_odds_data(competition.get('odds', []))
    
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
    
    # Also capture geoBroadcasts for streaming info
    geo_broadcasts = []
    for gb in competition.get('geoBroadcasts', []):
        geo_broadcasts.append({
            'type': gb.get('type', {}).get('shortName'),
            'market': gb.get('market', {}).get('type'),
            'media': gb.get('media', {}).get('shortName'),
            'lang': gb.get('lang'),
            'region': gb.get('region')
        })
    
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
    
    # ========== TICKETS ==========
    tickets = {}
    tickets_list = competition.get('tickets', [])
    if tickets_list:
        t = tickets_list[0]
        tickets = {
            'summary': t.get('summary'),
            'numberAvailable': t.get('numberAvailable'),
            'link': t.get('links', [{}])[0].get('href') if t.get('links') else None
        }
    
    # ========== LINKS ==========
    links = {}
    for link in event_data.get('links', []):
        rel = link.get('rel', [])
        if 'summary' in rel:
            links['gamecast'] = link.get('href')
        elif 'boxscore' in rel:
            links['boxscore'] = link.get('href')
        elif 'pbp' in rel:
            links['playbyplay'] = link.get('href')
    
    # ========== BUILD COMPLETE RECORD ==========
    full_data = {
        # Identifiers
        'game_id': game_id,
        'event_uid': event_data.get('uid'),
        'timestamp': datetime.utcnow().isoformat(),
        'source': 'espn_lambda_full_v2',
        
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
        
        # Home Team - Full data
        'home_team': home_team.get('abbreviation'),
        'home_team_full': home_team,
        'home_score': home_team.get('score', 0),
        
        # Away Team - Full data
        'away_team': away_team.get('abbreviation'),
        'away_team_full': away_team,
        'away_score': away_team.get('score', 0),
        
        # Game-level leaders (top performers across both teams)
        'gameLeaders': game_leaders,
        
        # Weather
        'weather': weather_data,
        
        # Venue
        'venue': venue_data,
        
        # Odds & Betting - Enhanced
        'odds': odds_data,
        
        # ESPN Win Probability
        'predictor': predictor,
        'winProbabilityHistory': win_prob_history,
        
        # Broadcasts
        'broadcasts': broadcasts,
        'geoBroadcasts': geo_broadcasts,
        
        # Tickets
        'tickets': tickets,
        
        # Links
        'links': links,
        
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
            'seasonYear': event_data.get('season', {}).get('year'),
            'neutralSite': competition.get('neutralSite', False),
            'conferenceCompetition': competition.get('conferenceCompetition', False),
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
    print(f"ESPN Full Poller v2 triggered at {datetime.utcnow().isoformat()}")
    
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
                home_passing = full_data.get('home_team_full', {}).get('leaders', {}).get('passing', {})
                print(f"Sent: {full_data['posteam']} vs {full_data['defteam']} - "
                      f"{full_data['down']}&{full_data['ydstogo']} at {full_data['yardline_100']} "
                      f"| ESPN WP: {full_data.get('predictor', {}).get('homeWinProbability', 'N/A')}% "
                      f"| QB: {home_passing.get('shortName', 'N/A') if home_passing else 'N/A'}")
    
    result = {
        'statusCode': 200,
        'body': json.dumps({
            'live_games': live_games,
            'plays_sent': plays_sent,
            'timestamp': datetime.utcnow().isoformat(),
            'data_captured': 'FULL_V2',
            'features': [
                'headshots',
                'receiving_leaders',
                'full_stat_lines',
                'enhanced_odds',
                'home_away_records',
                'tickets',
                'geo_broadcasts'
            ]
        })
    }
    
    print(f"Done: {live_games} live games, {plays_sent} plays sent (FULL DATA V2)")
    return result