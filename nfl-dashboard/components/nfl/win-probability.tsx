"use client"

import type { PlayData } from "@/types/nfl"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bullet } from "@/components/ui/bullet"

interface WinProbabilityProps {
  play: PlayData
}

export function WinProbability({ play }: WinProbabilityProps) {
  const { predictor, home_team_full, away_team_full } = play

  if (!predictor) return null

  const homeWP = predictor.homeWinProbability
  const awayWP = predictor.awayWinProbability

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5">
          <Bullet />
          Win Probability
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="relative h-8 bg-accent rounded-full overflow-hidden flex">
          <div
            className="h-full transition-all duration-500 flex items-center justify-start px-3"
            style={{
              width: `${awayWP}%`,
              backgroundColor: `#${away_team_full.color}`,
            }}
          >
            {awayWP > 15 && <span className="text-xs font-bold text-white">{awayWP.toFixed(1)}%</span>}
          </div>
          <div
            className="h-full transition-all duration-500 flex items-center justify-end px-3"
            style={{
              width: `${homeWP}%`,
              backgroundColor: `#${home_team_full.color}`,
            }}
          >
            {homeWP > 15 && <span className="text-xs font-bold text-white">{homeWP.toFixed(1)}%</span>}
          </div>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <div className="size-3 rounded-full" style={{ backgroundColor: `#${away_team_full.color}` }} />
            <span className="font-display">{away_team_full.abbreviation}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-display">{home_team_full.abbreviation}</span>
            <div className="size-3 rounded-full" style={{ backgroundColor: `#${home_team_full.color}` }} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
