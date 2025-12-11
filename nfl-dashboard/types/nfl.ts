// NFL Data Types
export interface PlayData {
  game_id: string
  event_uid: string
  timestamp: string
  source: string

  // Game Status
  status: {
    state: "pre" | "in" | "post"
    detail: string
    shortDetail: string
    period: number
    displayClock: string
    completed: boolean
  }

  // Current Situation
  situation: {
    down: number
    distance: number
    yardLine: number
    yardline_100: number
    possession: string
    isRedZone: boolean
    downDistanceText: string
    shortDownDistanceText: string
    possessionText: string
  }

  // Flat fields for predictions
  down: number
  ydstogo: number
  yardline_100: number
  qtr: number
  half_seconds_remaining: number
  score_differential: number
  posteam: string
  defteam: string
  posteam_type: "home" | "away"
  goal_to_go: number

  // Team Basic Info
  home_team: string
  away_team: string
  home_score: number
  away_score: number

  // Team Full Data
  home_team_full: TeamFull
  away_team_full: TeamFull

  // Game Leaders
  gameLeaders?: {
    passing: LeaderData
    rushing: LeaderData
    receiving: LeaderData
  }

  // Weather
  weather?: {
    temperature: number
    displayValue: string
    conditionId?: string
    gust?: number
    link?: string
  }

  // Venue
  venue?: {
    id: string
    name: string
    shortName?: string
    city: string
    state: string
    indoor: boolean
    grass: boolean
    capacity: number
  }

  // Odds
  odds?: {
    provider: string
    details: string
    spread: number
    overUnder: number
    moneyline?: {
      home: string
      away: string
    }
    pointSpread?: {
      home: { line: string; odds: string }
      away: { line: string; odds: string }
    }
    total?: {
      over: { line: string; odds: string }
      under: { line: string; odds: string }
    }
    homeFavorite?: boolean
    awayFavorite?: boolean
  }

  // Win Probability
  predictor?: {
    homeWinProbability: number
    awayWinProbability: number
  }

  // Win Probability History
  winProbabilityHistory?: Array<{
    playId: string
    homeWinPercentage: number
    secondsLeft: number
  }>

  // Broadcasts
  broadcasts?: string[]
  geoBroadcasts?: Array<{
    type: string
    market: string
    media: string
  }>

  // Tickets
  tickets?: {
    summary: string
    numberAvailable: number
    link: string
  }

  // Links
  links?: {
    gamecast: string
    boxscore: string
    playbyplay: string
  }

  // Last Play
  lastPlay?: {
    id: string
    text: string
    type: string
    scoreValue: number
    team: string
    athletesInvolved: string[]
  }

  // Event Metadata
  event?: {
    name: string
    shortName: string
    date: string
    week: number
    seasonType: number
    seasonYear: number
    neutralSite: boolean
  }

  // Game Info
  gameInfo?: any

  // ML Predictions
  expected_points: number
  td_prob: number
  fg_prob: number
  no_score_prob: number
  opp_td_prob?: number
  opp_fg_prob?: number
  pass_probability: number
  run_probability: number
  predicted_play: string
  pressure_probability: number
  pressure_risk: "low" | "medium" | "high"
}

export interface TeamFull {
  id: string
  uid?: string
  abbreviation: string
  name: string
  displayName: string
  shortDisplayName?: string
  color: string
  alternateColor?: string
  logo: string
  score: number
  homeAway: "home" | "away"
  records?: {
    overall: string
    home: string
    away: string
  }
  leaders?: {
    passing: LeaderData
    rushing: LeaderData
    receiving: LeaderData
  }
}

export interface LeaderData {
  name: string
  shortName: string
  displayName: string
  headshot: string
  jersey: string
  position: string
  teamId: string
  playerId: string
  displayValue: string
  value: number
  active?: boolean
}

export interface NFLTeam {
  abbr: string
  name: string
  color: string
  logo: string
}
