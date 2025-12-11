"use client"

import type { PlayData } from "@/types/nfl"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import Image from "next/image"

interface ScoreboardProps {
  play: PlayData
  isLive?: boolean
}

export function Scoreboard({ play, isLive }: ScoreboardProps) {
  const { away_team_full, home_team_full, status, situation } = play
  const awayWinning = away_team_full.score > home_team_full.score
  const homeWinning = home_team_full.score > away_team_full.score
  const hasPossession = (team: string) => situation?.possession === team

  return (
    <div className="bg-card ring-2 ring-border rounded-lg overflow-hidden">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-accent/50 border-b border-border">
        <div className="text-xs text-muted-foreground font-medium">
          {play.event?.shortName || `${play.away_team} @ ${play.home_team}`}
        </div>
        <div className="flex items-center gap-2">
          {isLive && (
            <Badge variant="destructive" className="animate-pulse">
              ● LIVE
            </Badge>
          )}
          {status?.state === "pre" && <Badge variant="outline">UPCOMING</Badge>}
          {status?.state === "post" && <Badge variant="secondary">FINAL</Badge>}
        </div>
      </div>

      {/* Main Scoreboard */}
      <div className="grid grid-cols-3 gap-4 p-6">
        {/* Away Team */}
        <div className="flex flex-col items-center gap-3">
          <div className="relative">
            <Image
              src={away_team_full.logo || "/placeholder.svg"}
              alt={away_team_full.displayName}
              width={64}
              height={64}
              className="object-contain"
            />
            {hasPossession(away_team_full.abbreviation) && (
              <div className="absolute -right-2 -top-2 bg-primary text-primary-foreground rounded-full p-1 text-xs">
                🏈
              </div>
            )}
          </div>
          <div className="text-center">
            <div className="font-display text-sm">{away_team_full.abbreviation}</div>
            {away_team_full.records && (
              <div className="text-xs text-muted-foreground">{away_team_full.records.overall}</div>
            )}
          </div>
          <div className={cn("text-5xl font-display", awayWinning ? "text-success" : "text-muted-foreground")}>
            {away_team_full.score}
          </div>
        </div>

        {/* Center - Game Info */}
        <div className="flex flex-col items-center justify-center gap-2">
          <div className="text-2xl font-display">{status?.displayClock || "0:00"}</div>
          <Badge variant="outline" className="text-xs">
            Q{status?.period || 1}
          </Badge>
          {situation?.isRedZone && (
            <Badge variant="destructive" className="text-xs">
              RED ZONE
            </Badge>
          )}
        </div>

        {/* Home Team */}
        <div className="flex flex-col items-center gap-3">
          <div className="relative">
            <Image
              src={home_team_full.logo || "/placeholder.svg"}
              alt={home_team_full.displayName}
              width={64}
              height={64}
              className="object-contain"
            />
            {hasPossession(home_team_full.abbreviation) && (
              <div className="absolute -right-2 -top-2 bg-primary text-primary-foreground rounded-full p-1 text-xs">
                🏈
              </div>
            )}
          </div>
          <div className="text-center">
            <div className="font-display text-sm">{home_team_full.abbreviation}</div>
            {home_team_full.records && (
              <div className="text-xs text-muted-foreground">{home_team_full.records.overall}</div>
            )}
          </div>
          <div className={cn("text-5xl font-display", homeWinning ? "text-success" : "text-muted-foreground")}>
            {home_team_full.score}
          </div>
        </div>
      </div>

      {/* Situation Bar */}
      {situation && (
        <div className="px-4 py-3 bg-accent/30 border-t border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="font-display">
                {situation.shortDownDistanceText}
              </Badge>
              <span className="text-sm text-muted-foreground">{situation.possessionText}</span>
            </div>
            <div className="text-xs text-muted-foreground">at {situation.yardLine}</div>
          </div>
        </div>
      )}
    </div>
  )
}
