# NFL Real-Time Analytics - Data Schemas

## 1. Play Events Stream (nfl-play-events)

This stream receives structured play-by-play data.

| Field | Type | Description |
|-------|------|-------------|
| game_id | string | Unique game identifier |
| play_id | integer | Unique play identifier within game |
| quarter | integer | 1-4, or 5 for OT |
| down | integer | 1-4 |
| ydstogo | integer | Yards to first down |
| yardline_100 | integer | Yard line (0-100, distance from end zone) |
| posteam | string | Possession team abbreviation |
| defteam | string | Defensive team abbreviation |
| play_type | string | run, pass, punt, field_goal, etc. |
| shotgun | integer | 1 if shotgun formation, 0 otherwise |
| no_huddle | integer | 1 if no huddle, 0 otherwise |
| offense_formation | string | SHOTGUN, UNDER_CENTER, etc. |
| offense_personnel | string | Personnel grouping (e.g., "1 RB, 2 TE, 2 WR") |
| defenders_in_box | integer | Number of defenders in the box |
| number_of_pass_rushers | integer | Number of pass rushers |
| event_time | timestamp | When play occurred |

## 2. Tracking Frames Stream (nfl-tracking-frames)

This stream receives frame-level player position data.

| Field | Type | Description |
|-------|------|-------------|
| game_id | string | Unique game identifier |
| play_id | integer | Unique play identifier |
| frame_id | integer | Frame number within play |
| player_id | string | Unique player identifier |
| team | string | Team abbreviation |
| position | string | Player position (QB, WR, CB, etc.) |
| x | float | X coordinate on field (0-120) |
| y | float | Y coordinate on field (0-53.3) |
| speed | float | Player speed in yards/second |
| acceleration | float | Player acceleration |
| direction | float | Direction of movement (degrees) |
| event_time | timestamp | Frame timestamp |

## 3. Enriched Play Output (to S3)

After joining and feature engineering, output contains:

| Field | Type | Description |
|-------|------|-------------|
| game_id | string | Unique game identifier |
| play_id | integer | Unique play identifier |
| quarter | integer | Quarter number |
| down | integer | Down number |
| ydstogo | integer | Yards to go |
| play_type | string | Actual play type |
| predicted_play_type | string | ML predicted play type |
| pressure_rate | float | Calculated pressure probability (0-1) |
| time_to_throw | float | Estimated/actual time to throw |
| was_pressure | integer | 1 if pressure occurred, 0 otherwise |
| defenders_in_box | integer | Box count |
| nearest_defender_dist | float | Distance to nearest defender |
| qb_pocket_location | string | Left, Center, Right |
| chaos_score | float | Overall play chaos metric (0-100) |
| epa | float | Expected points added |
| processed_at | timestamp | When record was processed |

## 4. Feature Vector (for ML Models)

Input features for play classification:

- down (1-4)
- ydstogo (normalized)
- yardline_100 (normalized)
- shotgun (0/1)
- no_huddle (0/1)
- defenders_in_box (normalized)
- number_of_pass_rushers (normalized)
- score_differential (normalized)
- quarter (1-5)
- seconds_remaining (normalized)

Target: play_type (run, short_pass, deep_pass, screen, rpo)
