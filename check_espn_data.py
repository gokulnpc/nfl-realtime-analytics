"""
Check what ESPN API actually returns
"""

import urllib.request
import json

ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

def fetch_and_analyze():
    # Get scoreboard
    req = urllib.request.Request(f"{ESPN_BASE_URL}/scoreboard")
    req.add_header('User-Agent', 'Mozilla/5.0')
    
    with urllib.request.urlopen(req, timeout=10) as response:
        scoreboard = json.loads(response.read().decode())
    
    print("=" * 70)
    print("ESPN SCOREBOARD - TOP LEVEL KEYS")
    print("=" * 70)
    print(f"Keys: {list(scoreboard.keys())}")
    
    events = scoreboard.get('events', [])
    print(f"\nNumber of games: {len(events)}")
    
    if events:
        event = events[0]
        print("\n" + "=" * 70)
        print("SINGLE EVENT (GAME) - ALL KEYS")
        print("=" * 70)
        print(f"Keys: {list(event.keys())}")
        
        # Competition
        competition = event.get('competitions', [{}])[0]
        print("\n" + "-" * 50)
        print("COMPETITION KEYS:")
        print(f"Keys: {list(competition.keys())}")
        
        # Competitors (Teams)
        competitors = competition.get('competitors', [])
        if competitors:
            print("\n" + "-" * 50)
            print("COMPETITOR (TEAM) KEYS:")
            print(f"Keys: {list(competitors[0].keys())}")
            
            team = competitors[0].get('team', {})
            print("\n" + "-" * 50)
            print("TEAM DETAIL KEYS:")
            print(f"Keys: {list(team.keys())}")
            
            # Statistics
            stats = competitors[0].get('statistics', [])
            print("\n" + "-" * 50)
            print(f"TEAM STATISTICS ({len(stats)} stats):")
            for stat in stats[:10]:
                print(f"  - {stat.get('name')}: {stat.get('displayValue')}")
            
            # Leaders
            leaders = competitors[0].get('leaders', [])
            print("\n" + "-" * 50)
            print(f"TEAM LEADERS ({len(leaders)} categories):")
            for leader in leaders:
                print(f"  - {leader.get('name')}")
        
        # Status
        status = event.get('status', {})
        print("\n" + "-" * 50)
        print("STATUS KEYS:")
        print(f"Keys: {list(status.keys())}")
        print(f"Type keys: {list(status.get('type', {}).keys())}")
        
        # Situation (if game is live)
        situation = event.get('competitions', [{}])[0].get('situation', {})
        if situation:
            print("\n" + "-" * 50)
            print("SITUATION KEYS (LIVE GAME):")
            print(f"Keys: {list(situation.keys())}")
        
        # Get detailed summary for first game
        game_id = event.get('id')
        print(f"\n\n{'=' * 70}")
        print(f"FETCHING DETAILED SUMMARY FOR GAME {game_id}")
        print("=" * 70)
        
        req2 = urllib.request.Request(f"{ESPN_BASE_URL}/summary?event={game_id}")
        req2.add_header('User-Agent', 'Mozilla/5.0')
        
        try:
            with urllib.request.urlopen(req2, timeout=10) as response:
                summary = json.loads(response.read().decode())
            
            print(f"\nSUMMARY TOP LEVEL KEYS:")
            print(f"Keys: {list(summary.keys())}")
            
            # Boxscore
            if 'boxscore' in summary:
                boxscore = summary['boxscore']
                print("\n" + "-" * 50)
                print("BOXSCORE KEYS:")
                print(f"Keys: {list(boxscore.keys())}")
                
                # Players
                players = boxscore.get('players', [])
                if players:
                    print(f"\nPLAYERS DATA ({len(players)} teams):")
                    for team_players in players:
                        team_name = team_players.get('team', {}).get('abbreviation', 'UNK')
                        stats_categories = team_players.get('statistics', [])
                        print(f"\n  {team_name} Statistics Categories:")
                        for cat in stats_categories:
                            print(f"    - {cat.get('name')}: {len(cat.get('athletes', []))} players")
            
            # Drives
            if 'drives' in summary:
                drives = summary['drives']
                print("\n" + "-" * 50)
                print("DRIVES DATA:")
                print(f"Keys: {list(drives.keys())}")
                previous = drives.get('previous', [])
                print(f"Previous drives: {len(previous)}")
                if previous:
                    drive = previous[0]
                    print(f"Drive keys: {list(drive.keys())}")
                    plays = drive.get('plays', [])
                    if plays:
                        print(f"Plays in drive: {len(plays)}")
                        print(f"Play keys: {list(plays[0].keys())}")
            
            # Situation
            if 'situation' in summary:
                situation = summary['situation']
                print("\n" + "-" * 50)
                print("SITUATION (CURRENT PLAY) KEYS:")
                print(f"Keys: {list(situation.keys())}")
                print(f"\nFull situation data:")
                for key, value in situation.items():
                    print(f"  {key}: {value}")
            
            # Leaders
            if 'leaders' in summary:
                leaders = summary['leaders']
                print("\n" + "-" * 50)
                print(f"LEADERS ({len(leaders)} categories):")
                for leader in leaders:
                    print(f"  - {leader.get('name')}")
            
            # Scoring plays
            if 'scoringPlays' in summary:
                scoring = summary['scoringPlays']
                print("\n" + "-" * 50)
                print(f"SCORING PLAYS: {len(scoring)}")
                if scoring:
                    print(f"Scoring play keys: {list(scoring[0].keys())}")
            
            # Game info
            if 'gameInfo' in summary:
                game_info = summary['gameInfo']
                print("\n" + "-" * 50)
                print("GAME INFO KEYS:")
                print(f"Keys: {list(game_info.keys())}")
            
            # Predictor
            if 'predictor' in summary:
                predictor = summary['predictor']
                print("\n" + "-" * 50)
                print("PREDICTOR (WIN PROBABILITY):")
                print(f"Keys: {list(predictor.keys())}")
                print(f"Home win %: {predictor.get('homeTeam', {}).get('gameProjection')}")
                print(f"Away win %: {predictor.get('awayTeam', {}).get('gameProjection')}")
                
        except Exception as e:
            print(f"Error fetching summary: {e}")

if __name__ == "__main__":
    fetch_and_analyze()
