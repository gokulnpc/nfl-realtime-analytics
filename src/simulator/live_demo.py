"""
NFL Live Demo Simulator v2 - FULL ENHANCED DATA
Sends complete ESPN-like data with headshots, receiving leaders, enhanced odds
"""

import boto3
import json
import time
import random
from datetime import datetime

STREAM_NAME = 'nfl-play-stream'
REGION = 'us-east-1'

# Team data with full details
TEAMS = {
    'KC': {
        'id': '12', 'abbreviation': 'KC', 'name': 'Chiefs', 
        'displayName': 'Kansas City Chiefs', 'shortDisplayName': 'Chiefs',
        'color': 'E31837', 'alternateColor': 'FFB81C',
        'records': {'overall': '11-3', 'home': '6-1', 'away': '5-2'},
        'players': {
            'qb': {'id': '3139477', 'name': 'Patrick Mahomes', 'shortName': 'P. Mahomes', 'jersey': '15', 'stats': '299/474, 3398 YDS, 22 TD, 10 INT'},
            'rb': {'id': '4361529', 'name': 'Isiah Pacheco', 'shortName': 'I. Pacheco', 'jersey': '10', 'stats': '192 CAR, 824 YDS, 6 TD'},
            'wr': {'id': '15847', 'name': 'Travis Kelce', 'shortName': 'T. Kelce', 'jersey': '87', 'stats': '78 REC, 823 YDS, 4 TD', 'position': 'TE'}
        }
    },
    'SF': {
        'id': '25', 'abbreviation': 'SF', 'name': '49ers',
        'displayName': 'San Francisco 49ers', 'shortDisplayName': '49ers',
        'color': 'AA0000', 'alternateColor': 'B3995D',
        'records': {'overall': '10-4', 'home': '5-2', 'away': '5-2'},
        'players': {
            'qb': {'id': '3052587', 'name': 'Brock Purdy', 'shortName': 'B. Purdy', 'jersey': '13', 'stats': '312/456, 3758 YDS, 26 TD, 9 INT'},
            'rb': {'id': '3128720', 'name': 'Christian McCaffrey', 'shortName': 'C. McCaffrey', 'jersey': '23', 'stats': '246 CAR, 1145 YDS, 13 TD'},
            'wr': {'id': '4360438', 'name': 'Deebo Samuel', 'shortName': 'D. Samuel', 'jersey': '19', 'stats': '62 REC, 892 YDS, 7 TD'}
        }
    },
    'DAL': {
        'id': '6', 'abbreviation': 'DAL', 'name': 'Cowboys',
        'displayName': 'Dallas Cowboys', 'shortDisplayName': 'Cowboys',
        'color': '003594', 'alternateColor': '041E42',
        'records': {'overall': '9-5', 'home': '5-2', 'away': '4-3'},
        'players': {
            'qb': {'id': '2577417', 'name': 'Dak Prescott', 'shortName': 'D. Prescott', 'jersey': '4', 'stats': '345/512, 3892 YDS, 28 TD, 12 INT'},
            'rb': {'id': '4241389', 'name': 'Tony Pollard', 'shortName': 'T. Pollard', 'jersey': '20', 'stats': '178 CAR, 789 YDS, 5 TD'},
            'wr': {'id': '4241372', 'name': 'CeeDee Lamb', 'shortName': 'C. Lamb', 'jersey': '88', 'stats': '98 REC, 1256 YDS, 10 TD'}
        }
    },
    'PHI': {
        'id': '21', 'abbreviation': 'PHI', 'name': 'Eagles',
        'displayName': 'Philadelphia Eagles', 'shortDisplayName': 'Eagles',
        'color': '004C54', 'alternateColor': 'A5ACAF',
        'records': {'overall': '10-4', 'home': '6-1', 'away': '4-3'},
        'players': {
            'qb': {'id': '3918298', 'name': 'Jalen Hurts', 'shortName': 'J. Hurts', 'jersey': '1', 'stats': '278/432, 3156 YDS, 22 TD, 8 INT'},
            'rb': {'id': '4361307', 'name': "D'Andre Swift", 'shortName': 'D. Swift', 'jersey': '0', 'stats': '195 CAR, 892 YDS, 5 TD'},
            'wr': {'id': '4262921', 'name': 'A.J. Brown', 'shortName': 'A.J. Brown', 'jersey': '11', 'stats': '82 REC, 1198 YDS, 8 TD'}
        }
    },
    'BUF': {
        'id': '2', 'abbreviation': 'BUF', 'name': 'Bills',
        'displayName': 'Buffalo Bills', 'shortDisplayName': 'Bills',
        'color': '00338D', 'alternateColor': 'C60C30',
        'records': {'overall': '10-4', 'home': '5-2', 'away': '5-2'},
        'players': {
            'qb': {'id': '3918298', 'name': 'Josh Allen', 'shortName': 'J. Allen', 'jersey': '17', 'stats': '312/478, 3678 YDS, 28 TD, 14 INT'},
            'rb': {'id': '4379399', 'name': 'James Cook', 'shortName': 'J. Cook', 'jersey': '4', 'stats': '178 CAR, 892 YDS, 7 TD'},
            'wr': {'id': '3116406', 'name': 'Stefon Diggs', 'shortName': 'S. Diggs', 'jersey': '14', 'stats': '92 REC, 1156 YDS, 9 TD'}
        }
    },
    'MIA': {
        'id': '15', 'abbreviation': 'MIA', 'name': 'Dolphins',
        'displayName': 'Miami Dolphins', 'shortDisplayName': 'Dolphins',
        'color': '008E97', 'alternateColor': 'FC4C02',
        'records': {'overall': '8-6', 'home': '4-3', 'away': '4-3'},
        'players': {
            'qb': {'id': '4241479', 'name': 'Tua Tagovailoa', 'shortName': 'T. Tagovailoa', 'jersey': '1', 'stats': '298/442, 3456 YDS, 24 TD, 10 INT'},
            'rb': {'id': '4239996', 'name': 'Raheem Mostert', 'shortName': 'R. Mostert', 'jersey': '31', 'stats': '156 CAR, 678 YDS, 8 TD'},
            'wr': {'id': '4374302', 'name': 'Tyreek Hill', 'shortName': 'T. Hill', 'jersey': '10', 'stats': '102 REC, 1478 YDS, 12 TD'}
        }
    },
}

# Game scenarios with full data
SCENARIOS = {
    '4th_quarter_comeback': {
        'name': '4th Quarter Comeback',
        'home_team': 'SF', 'away_team': 'KC',
        'home_score': 28, 'away_score': 21,
        'venue': {
            'id': '1234', 'name': "Levi's Stadium", 'shortName': "Levi's Stadium",
            'city': 'Santa Clara', 'state': 'CA', 'country': 'USA',
            'indoor': False, 'grass': True, 'capacity': 68500
        },
        'weather': {'temperature': 62, 'displayValue': 'Partly Cloudy', 'conditionId': '3', 'gust': 8, 'link': 'http://www.accuweather.com/'},
        'broadcasts': ['NBC', 'Peacock'],
        'geoBroadcasts': [
            {'type': 'TV', 'market': 'National', 'media': 'NBC', 'lang': 'en', 'region': 'us'},
            {'type': 'Streaming', 'market': 'National', 'media': 'Peacock', 'lang': 'en', 'region': 'us'}
        ],
        'odds': {
            'provider': 'DraftKings', 'providerId': '1002',
            'details': 'KC -3.5', 'spread': -3.5, 'overUnder': 47.5,
            'moneyline': {'home': '+145', 'away': '-170', 'homeOpen': '+150', 'awayOpen': '-175'},
            'pointSpread': {
                'home': {'line': '+3.5', 'odds': '-110'},
                'away': {'line': '-3.5', 'odds': '-110'}
            },
            'total': {
                'over': {'line': 'o47.5', 'odds': '-110'},
                'under': {'line': 'u47.5', 'odds': '-110'}
            },
            'homeFavorite': False, 'awayFavorite': True
        },
        'tickets': {'summary': 'Tickets as low as $125', 'numberAvailable': 2341, 'link': 'https://www.vividseats.com/'},
        'plays': [
            {'down': 1, 'ydstogo': 10, 'yardline_100': 75, 'qtr': 4, 'seconds': 300, 'desc': 'Chiefs down 7, 5 min left', 'last_play': 'Touchback on kickoff', 'play_type': 'Kickoff'},
            {'down': 2, 'ydstogo': 3, 'yardline_100': 68, 'qtr': 4, 'seconds': 255, 'desc': 'Quick 7 yard gain', 'last_play': 'Patrick Mahomes pass to Travis Kelce for 7 yards', 'play_type': 'Pass'},
            {'down': 1, 'ydstogo': 10, 'yardline_100': 55, 'qtr': 4, 'seconds': 220, 'desc': 'Crossing midfield', 'last_play': 'Isiah Pacheco rush for 13 yards', 'play_type': 'Rush'},
            {'down': 3, 'ydstogo': 6, 'yardline_100': 42, 'qtr': 4, 'seconds': 180, 'desc': '3rd down conversion needed', 'last_play': 'Patrick Mahomes pass incomplete', 'play_type': 'Pass'},
            {'down': 1, 'ydstogo': 10, 'yardline_100': 28, 'qtr': 4, 'seconds': 140, 'desc': 'Into the red zone!', 'last_play': 'Patrick Mahomes pass to Rashee Rice for 14 yards', 'play_type': 'Pass'},
            {'down': 2, 'ydstogo': 8, 'yardline_100': 18, 'qtr': 4, 'seconds': 95, 'desc': 'Under 2 minutes', 'last_play': 'Isiah Pacheco rush for 2 yards', 'play_type': 'Rush'},
            {'down': 1, 'ydstogo': 5, 'yardline_100': 5, 'qtr': 4, 'seconds': 45, 'desc': '1st & Goal at the 5!', 'last_play': 'Patrick Mahomes pass to Travis Kelce for 13 yards', 'play_type': 'Pass'},
            {'down': 2, 'ydstogo': 2, 'yardline_100': 2, 'qtr': 4, 'seconds': 12, 'desc': 'GAME ON THE LINE!', 'last_play': 'Isiah Pacheco rush for 3 yards', 'play_type': 'Rush'},
        ]
    },
    'red_zone_showdown': {
        'name': 'Red Zone Showdown',
        'home_team': 'PHI', 'away_team': 'DAL',
        'home_score': 17, 'away_score': 14,
        'venue': {
            'id': '5678', 'name': 'Lincoln Financial Field', 'shortName': 'Lincoln Financial Field',
            'city': 'Philadelphia', 'state': 'PA', 'country': 'USA',
            'indoor': False, 'grass': True, 'capacity': 69796
        },
        'weather': {'temperature': 38, 'displayValue': 'Clear', 'conditionId': '1', 'gust': 15, 'link': 'http://www.accuweather.com/'},
        'broadcasts': ['FOX', 'NFL Network'],
        'geoBroadcasts': [
            {'type': 'TV', 'market': 'National', 'media': 'FOX', 'lang': 'en', 'region': 'us'},
            {'type': 'TV', 'market': 'National', 'media': 'NFL Network', 'lang': 'en', 'region': 'us'}
        ],
        'odds': {
            'provider': 'DraftKings', 'providerId': '1002',
            'details': 'PHI -6.5', 'spread': -6.5, 'overUnder': 44.5,
            'moneyline': {'home': '-280', 'away': '+230', 'homeOpen': '-275', 'awayOpen': '+225'},
            'pointSpread': {
                'home': {'line': '-6.5', 'odds': '-108'},
                'away': {'line': '+6.5', 'odds': '-112'}
            },
            'total': {
                'over': {'line': 'o44.5', 'odds': '-115'},
                'under': {'line': 'u44.5', 'odds': '-105'}
            },
            'homeFavorite': True, 'awayFavorite': False
        },
        'tickets': {'summary': 'Tickets as low as $95', 'numberAvailable': 1856, 'link': 'https://www.vividseats.com/'},
        'plays': [
            {'down': 1, 'ydstogo': 10, 'yardline_100': 20, 'qtr': 2, 'seconds': 600, 'desc': 'Cowboys in the red zone', 'last_play': 'Dak Prescott pass to CeeDee Lamb for 15 yards', 'play_type': 'Pass'},
            {'down': 2, 'ydstogo': 6, 'yardline_100': 16, 'qtr': 2, 'seconds': 555, 'desc': '2nd and 6', 'last_play': 'Tony Pollard rush for 4 yards', 'play_type': 'Rush'},
            {'down': 3, 'ydstogo': 4, 'yardline_100': 14, 'qtr': 2, 'seconds': 510, 'desc': '3rd and short', 'last_play': 'Dak Prescott pass incomplete', 'play_type': 'Pass'},
            {'down': 1, 'ydstogo': 8, 'yardline_100': 8, 'qtr': 2, 'seconds': 465, 'desc': '1st & Goal at the 8!', 'last_play': 'Dak Prescott pass to Jake Ferguson for 6 yards', 'play_type': 'Pass'},
            {'down': 2, 'ydstogo': 5, 'yardline_100': 5, 'qtr': 2, 'seconds': 420, 'desc': '2nd & Goal', 'last_play': 'Tony Pollard rush for 3 yards', 'play_type': 'Rush'},
            {'down': 3, 'ydstogo': 3, 'yardline_100': 3, 'qtr': 2, 'seconds': 375, 'desc': '3rd & Goal - TD or FG?', 'last_play': 'Dak Prescott rush for 2 yards', 'play_type': 'Rush'},
        ]
    },
    'two_minute_drill': {
        'name': 'Two Minute Drill',
        'home_team': 'MIA', 'away_team': 'BUF',
        'home_score': 24, 'away_score': 21,
        'venue': {
            'id': '9012', 'name': 'Hard Rock Stadium', 'shortName': 'Hard Rock Stadium',
            'city': 'Miami Gardens', 'state': 'FL', 'country': 'USA',
            'indoor': False, 'grass': True, 'capacity': 65326
        },
        'weather': {'temperature': 78, 'displayValue': 'Sunny', 'conditionId': '1', 'gust': 5, 'link': 'http://www.accuweather.com/'},
        'broadcasts': ['CBS', 'Paramount+'],
        'geoBroadcasts': [
            {'type': 'TV', 'market': 'National', 'media': 'CBS', 'lang': 'en', 'region': 'us'},
            {'type': 'Streaming', 'market': 'National', 'media': 'Paramount+', 'lang': 'en', 'region': 'us'}
        ],
        'odds': {
            'provider': 'DraftKings', 'providerId': '1002',
            'details': 'MIA -2.5', 'spread': -2.5, 'overUnder': 51.5,
            'moneyline': {'home': '-135', 'away': '+115', 'homeOpen': '-140', 'awayOpen': '+120'},
            'pointSpread': {
                'home': {'line': '-2.5', 'odds': '-110'},
                'away': {'line': '+2.5', 'odds': '-110'}
            },
            'total': {
                'over': {'line': 'o51.5', 'odds': '-108'},
                'under': {'line': 'u51.5', 'odds': '-112'}
            },
            'homeFavorite': True, 'awayFavorite': False
        },
        'tickets': {'summary': 'Tickets as low as $78', 'numberAvailable': 3124, 'link': 'https://www.vividseats.com/'},
        'plays': [
            {'down': 1, 'ydstogo': 10, 'yardline_100': 75, 'qtr': 4, 'seconds': 120, 'desc': '2-minute warning', 'last_play': 'Kickoff touchback', 'play_type': 'Kickoff'},
            {'down': 1, 'ydstogo': 10, 'yardline_100': 60, 'qtr': 4, 'seconds': 100, 'desc': 'Quick pass', 'last_play': 'Josh Allen pass to Stefon Diggs for 15 yards', 'play_type': 'Pass'},
            {'down': 1, 'ydstogo': 10, 'yardline_100': 45, 'qtr': 4, 'seconds': 75, 'desc': 'Hurry up offense', 'last_play': 'Josh Allen pass to Dalton Kincaid for 15 yards', 'play_type': 'Pass'},
            {'down': 2, 'ydstogo': 5, 'yardline_100': 35, 'qtr': 4, 'seconds': 50, 'desc': 'Clock running', 'last_play': 'James Cook rush for 5 yards', 'play_type': 'Rush'},
            {'down': 1, 'ydstogo': 10, 'yardline_100': 25, 'qtr': 4, 'seconds': 30, 'desc': 'Field goal range', 'last_play': 'Josh Allen pass to Gabe Davis for 10 yards', 'play_type': 'Pass'},
            {'down': 1, 'ydstogo': 10, 'yardline_100': 15, 'qtr': 4, 'seconds': 8, 'desc': 'Spike it!', 'last_play': 'Josh Allen pass to Stefon Diggs for 10 yards', 'play_type': 'Pass'},
        ]
    }
}

def get_team_logo(abbr):
    return f"https://a.espncdn.com/i/teamlogos/nfl/500/{abbr.lower()}.png"

def get_player_headshot(player_id):
    return f"https://a.espncdn.com/i/headshots/nfl/players/full/{player_id}.png"

def build_leader_data(team_data, position):
    """Build full leader data with headshot"""
    player = team_data['players'].get(position)
    if not player:
        return None
    
    pos_map = {'qb': 'QB', 'rb': 'RB', 'wr': 'WR'}
    if position == 'wr' and player.get('position'):
        pos_abbr = player['position']
    else:
        pos_abbr = pos_map.get(position, 'WR')
    
    return {
        'name': player['name'],
        'shortName': player['shortName'],
        'displayName': player['name'],
        'headshot': get_player_headshot(player['id']),
        'jersey': player['jersey'],
        'position': pos_abbr,
        'teamId': team_data['id'],
        'playerId': player['id'],
        'displayValue': player['stats'],
        'value': int(player['stats'].split(' ')[0].replace(',', '').split('/')[0]),
        'active': True
    }

def build_team_full(team_abbr, score, is_home):
    """Build complete team object with leaders and records"""
    team = TEAMS[team_abbr]
    
    return {
        'id': team['id'],
        'uid': f"s:20~l:28~t:{team['id']}",
        'abbreviation': team['abbreviation'],
        'name': team['name'],
        'displayName': team['displayName'],
        'shortDisplayName': team['shortDisplayName'],
        'color': team['color'],
        'alternateColor': team['alternateColor'],
        'logo': get_team_logo(team_abbr),
        'score': score,
        'homeAway': 'home' if is_home else 'away',
        'winner': None,
        
        # Enhanced records structure
        'records': {
            'overall': team['records']['overall'],
            'home': team['records']['home'],
            'away': team['records']['away']
        },
        'record': team['records']['overall'],  # Legacy
        
        # Enhanced leaders with headshots
        'leaders': {
            'passing': build_leader_data(team, 'qb'),
            'rushing': build_leader_data(team, 'rb'),
            'receiving': build_leader_data(team, 'wr')
        },
        
        # Legacy format
        'passingLeader': build_leader_data(team, 'qb'),
        'rushingLeader': build_leader_data(team, 'rb'),
        'receivingLeader': build_leader_data(team, 'wr')
    }

def build_full_play(scenario_key, play_index):
    """Build complete play with all ESPN-like fields"""
    scenario = SCENARIOS[scenario_key]
    play = scenario['plays'][play_index]
    
    home_abbr = scenario['home_team']
    away_abbr = scenario['away_team']
    
    # Determine possession
    is_home_possession = scenario_key != '4th_quarter_comeback'
    if scenario_key == 'red_zone_showdown':
        is_home_possession = False  # DAL (away) is driving
    
    posteam = home_abbr if is_home_possession else away_abbr
    defteam = away_abbr if is_home_possession else home_abbr
    
    home_score = scenario['home_score']
    away_score = scenario['away_score']
    score_diff = (home_score - away_score) if is_home_possession else (away_score - home_score)
    
    # Win probability estimate
    base_wp = 50 + (home_score - away_score) * 2.5
    time_factor = play['seconds'] / 900  # More certainty as time runs out
    home_wp = min(max(base_wp + (50 - base_wp) * (1 - time_factor) * 0.3, 5), 95)
    
    # Build win probability history
    wp_history = []
    for i in range(min(5, play_index + 1)):
        wp_history.append({
            'playId': f"play_{i}",
            'homeWinPercentage': round(home_wp + random.uniform(-5, 5), 1),
            'secondsLeft': play['seconds'] + (play_index - i) * 30
        })
    
    home_team_full = build_team_full(home_abbr, home_score, True)
    away_team_full = build_team_full(away_abbr, away_score, False)
    
    # Game leaders (top across both teams)
    game_leaders = {
        'passing': home_team_full['leaders']['passing'] if random.random() > 0.5 else away_team_full['leaders']['passing'],
        'rushing': home_team_full['leaders']['rushing'] if random.random() > 0.5 else away_team_full['leaders']['rushing'],
        'receiving': home_team_full['leaders']['receiving'] if random.random() > 0.5 else away_team_full['leaders']['receiving']
    }
    
    return {
        # Identifiers
        'game_id': f"demo_{scenario_key}_{datetime.now().strftime('%H%M%S')}",
        'event_uid': f"s:20~l:28~e:{random.randint(100000, 999999)}",
        'timestamp': datetime.utcnow().isoformat(),
        'source': 'demo_simulator_v2',
        
        # Game Status
        'status': {
            'state': 'in',
            'detail': f"Q{play['qtr']} - {play['seconds']//60}:{play['seconds']%60:02d}",
            'shortDetail': f"Q{play['qtr']} {play['seconds']//60}:{play['seconds']%60:02d}",
            'description': f"In Progress",
            'period': play['qtr'],
            'displayClock': f"{play['seconds']//60}:{play['seconds']%60:02d}",
            'completed': False
        },
        
        # Situation (nested)
        'situation': {
            'down': play['down'],
            'distance': play['ydstogo'],
            'ydstogo': play['ydstogo'],
            'yardLine': 100 - play['yardline_100'],
            'yardline_100': play['yardline_100'],
            'possession': posteam,
            'isRedZone': play['yardline_100'] <= 20,
            'downDistanceText': f"{play['down']}&{play['ydstogo']} at {posteam} {100-play['yardline_100']}",
            'shortDownDistanceText': f"{play['down']}&{play['ydstogo']}",
            'possessionText': f"{posteam} ball"
        },
        
        # Flat fields for ML
        'down': play['down'],
        'ydstogo': play['ydstogo'],
        'yardline_100': play['yardline_100'],
        'qtr': play['qtr'],
        'half_seconds_remaining': play['seconds'],
        'score_differential': score_diff,
        'posteam': posteam,
        'defteam': defteam,
        'posteam_type': 'home' if is_home_possession else 'away',
        'goal_to_go': 1 if play['yardline_100'] <= play['ydstogo'] else 0,
        'shotgun': random.choice([0, 1]),
        'no_huddle': 1 if play['seconds'] < 120 else 0,
        'defenders_in_box': random.randint(5, 8),
        'number_of_pass_rushers': random.randint(3, 6),
        
        # Teams - Basic
        'home_team': home_abbr,
        'away_team': away_abbr,
        'home_score': home_score,
        'away_score': away_score,
        
        # Teams - Full (with leaders, headshots, records)
        'home_team_full': home_team_full,
        'away_team_full': away_team_full,
        
        # Game-level leaders
        'gameLeaders': game_leaders,
        
        # Weather
        'weather': scenario['weather'],
        
        # Venue
        'venue': scenario['venue'],
        
        # Odds - Enhanced
        'odds': scenario['odds'],
        
        # Tickets
        'tickets': scenario['tickets'],
        
        # Win Probability
        'predictor': {
            'homeWinProbability': round(home_wp, 1),
            'awayWinProbability': round(100 - home_wp, 1)
        },
        
        # Win Probability History
        'winProbabilityHistory': wp_history,
        
        # Broadcasts
        'broadcasts': scenario['broadcasts'],
        'geoBroadcasts': scenario['geoBroadcasts'],
        
        # Links
        'links': {
            'gamecast': f"https://www.espn.com/nfl/game/_/gameId/demo_{scenario_key}",
            'boxscore': f"https://www.espn.com/nfl/boxscore/_/gameId/demo_{scenario_key}",
            'playbyplay': f"https://www.espn.com/nfl/playbyplay/_/gameId/demo_{scenario_key}"
        },
        
        # Last Play
        'lastPlay': {
            'id': f"play_{play_index}",
            'text': play['last_play'],
            'type': play.get('play_type', 'Pass'),
            'scoreValue': 0,
            'team': posteam,
            'athletesInvolved': [play['last_play'].split(' ')[0]] if play['last_play'] else []
        },
        
        # Event
        'event': {
            'name': f"{TEAMS[away_abbr]['displayName']} at {TEAMS[home_abbr]['displayName']}",
            'shortName': f"{away_abbr} @ {home_abbr}",
            'date': datetime.utcnow().isoformat(),
            'week': 15,
            'seasonType': 2,
            'seasonYear': 2024,
            'neutralSite': False,
            'conferenceCompetition': False,
            'attendance': scenario['venue']['capacity'] - random.randint(0, 5000)
        },
        
        # Game Info
        'gameInfo': {
            'attendance': scenario['venue']['capacity'] - random.randint(0, 5000),
            'weatherCondition': scenario['weather']['displayValue'],
            'weatherTemp': scenario['weather']['temperature']
        },
        
        # Description
        'description': play['desc']
    }

def send_to_kinesis(client, data):
    try:
        response = client.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(data).encode('utf-8'),
            PartitionKey=str(data.get('game_id', 'demo'))
        )
        return response['ShardId']
    except Exception as e:
        print(f"Error: {e}")
        return None

def run_scenario(client, scenario_key, delay=3):
    scenario = SCENARIOS[scenario_key]
    print(f"\n{'='*60}")
    print(f"🏈 SCENARIO: {scenario['name']}")
    print(f"   {scenario['away_team']} @ {scenario['home_team']}")
    print(f"   Score: {scenario['away_team']} {scenario['away_score']} - {scenario['home_team']} {scenario['home_score']}")
    print(f"   📍 {scenario['venue']['name']}, {scenario['venue']['city']}, {scenario['venue']['state']}")
    print(f"   🌤️  {scenario['weather']['temperature']}°F, {scenario['weather']['displayValue']}")
    print(f"   📺 {', '.join(scenario['broadcasts'])}")
    print(f"{'='*60}")
    
    for i in range(len(scenario['plays'])):
        play = scenario['plays'][i]
        full_data = build_full_play(scenario_key, i)
        
        # Get leader info for display
        posteam = full_data['posteam']
        if posteam == scenario['home_team']:
            qb = full_data['home_team_full']['leaders']['passing']
        else:
            qb = full_data['away_team_full']['leaders']['passing']
        
        print(f"\n📍 Play {i+1}/{len(scenario['plays'])}: {play['desc']}")
        print(f"   {full_data['posteam']} ball | {play['down']}&{play['ydstogo']} at {100-play['yardline_100']}")
        print(f"   Q{play['qtr']} {play['seconds']//60}:{play['seconds']%60:02d} | Win Prob: {full_data['predictor']['homeWinProbability']:.1f}%")
        print(f"   🎯 QB: {qb['shortName']} #{qb['jersey']} | {qb['displayValue'][:30]}...")
        print(f"   📝 Last: {play['last_play'][:45]}...")
        
        shard = send_to_kinesis(client, full_data)
        if shard:
            print(f"   ✅ Sent to Kinesis (enhanced data v2)")
        
        if i < len(scenario['plays']) - 1:
            print(f"   ⏳ Next in {delay}s...")
            time.sleep(delay)
    
    print(f"\n🏁 Scenario complete!")

def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║       🏈 NFL LIVE DEMO SIMULATOR v2 (ENHANCED DATA)        ║
    ╠════════════════════════════════════════════════════════════╣
    ║  Now includes ALL ESPN fields:                             ║
    ║  ✅ Player headshots & jersey numbers                      ║
    ║  ✅ Receiving leaders (was missing!)                       ║
    ║  ✅ Full stat lines (299/474, 3398 YDS, 22 TD)            ║
    ║  ✅ Enhanced odds (moneylines, spread odds)                ║
    ║  ✅ Home/Away record splits                                ║
    ║  ✅ Win probability history                                ║
    ║  ✅ Geo broadcasts (streaming options)                     ║
    ║  ✅ Tickets, links, game info                              ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    try:
        client = boto3.client('kinesis', region_name=REGION)
        client.describe_stream(StreamName=STREAM_NAME)
        print(f"✅ Connected to Kinesis: {STREAM_NAME}\n")
    except Exception as e:
        print(f"❌ Kinesis error: {e}")
        return
    
    while True:
        print("-" * 40)
        print("Select Demo:")
        print("  1. 4th Quarter Comeback (KC @ SF)")
        print("  2. Red Zone Showdown (DAL @ PHI)")
        print("  3. Two Minute Drill (BUF @ MIA)")
        print("  4. All Scenarios")
        print("  5. Exit")
        print("-" * 40)
        
        choice = input("Choice (1-5): ").strip()
        
        if choice == '1':
            run_scenario(client, '4th_quarter_comeback')
        elif choice == '2':
            run_scenario(client, 'red_zone_showdown')
        elif choice == '3':
            run_scenario(client, 'two_minute_drill')
        elif choice == '4':
            for key in SCENARIOS:
                run_scenario(client, key)
                time.sleep(3)
        elif choice == '5':
            print("👋 Bye!")
            break

if __name__ == "__main__":
    main()