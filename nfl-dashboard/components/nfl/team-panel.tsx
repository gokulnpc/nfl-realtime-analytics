"use client"

import type { TeamFull } from "@/types/nfl"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bullet } from "@/components/ui/bullet"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

interface TeamPanelProps {
  team: TeamFull
  hasPossession?: boolean
}

export function TeamPanel({ team, hasPossession }: TeamPanelProps) {
  const { leaders, records } = team

  return (
    <Card>
      <CardHeader
        className="relative overflow-hidden"
        style={{
          background: `linear-gradient(135deg, #${team.color}20 0%, transparent 100%)`,
        }}
      >
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Bullet />
            {team.displayName}
            {hasPossession && <span className="text-sm">🏈</span>}
          </div>
          <div className="text-4xl font-display opacity-50">{team.score}</div>
        </CardTitle>
        {records && (
          <div className="text-xs text-muted-foreground font-medium">
            {records.overall} (H: {records.home} | A: {records.away})
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {leaders && (
          <>
            {/* Passing Leader */}
            <PlayerCard leader={leaders.passing} category="Passing" color={team.color} />

            {/* Rushing Leader */}
            <PlayerCard leader={leaders.rushing} category="Rushing" color={team.color} />

            {/* Receiving Leader */}
            <PlayerCard leader={leaders.receiving} category="Receiving" color={team.color} />
          </>
        )}
      </CardContent>
    </Card>
  )
}

interface PlayerCardProps {
  leader: any
  category: string
  color: string
}

function PlayerCard({ leader, category, color }: PlayerCardProps) {
  if (!leader) return null

  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-accent/30 hover:bg-accent/50 transition-colors">
      <Avatar className="size-12 ring-2 ring-border">
        <AvatarImage src={leader.headshot || "/placeholder.svg"} alt={leader.displayName} />
        <AvatarFallback style={{ backgroundColor: `#${color}40` }}>{leader.position}</AvatarFallback>
      </Avatar>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold truncate">{leader.shortName || leader.name}</span>
          <span className="text-xs text-muted-foreground">#{leader.jersey}</span>
        </div>
        <div className="text-xs text-muted-foreground">{category}</div>
        <div className="text-xs font-mono mt-0.5">{leader.displayValue}</div>
      </div>
    </div>
  )
}
