"use client"

import type { PlayData } from "@/types/nfl"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bullet } from "@/components/ui/bullet"
import { Badge } from "@/components/ui/badge"

interface GameInfoProps {
  play: PlayData
}

export function GameInfo({ play }: GameInfoProps) {
  const { venue, weather, odds, lastPlay, broadcasts } = play

  return (
    <div className="space-y-6">
      {/* Venue & Weather */}
      {venue && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2.5">
              <Bullet />
              Venue
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <div className="font-semibold">{venue.name}</div>
              <div className="text-sm text-muted-foreground">
                {venue.city}, {venue.state}
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Badge variant="secondary">{venue.indoor ? "Indoor" : "Outdoor"}</Badge>
              <Badge variant="secondary">{venue.grass ? "Grass" : "Turf"}</Badge>
              <Badge variant="outline">Cap: {venue.capacity?.toLocaleString()}</Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Weather */}
      {weather && !venue?.indoor && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2.5">
              <Bullet />
              Weather
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">{weather.displayValue}</div>
                {weather.gust && <div className="text-xs text-muted-foreground">Wind: {weather.gust} mph</div>}
              </div>
              <div className="text-4xl font-display">{weather.temperature}°</div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Odds */}
      {odds && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2.5">
              <Bullet />
              Betting Odds
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-xs text-muted-foreground mb-2">{odds.provider}</div>
            <div className="grid grid-cols-2 gap-3">
              <div className="text-center p-2 rounded bg-accent">
                <div className="text-xs text-muted-foreground">Spread</div>
                <div className="font-display">{odds.details}</div>
              </div>
              <div className="text-center p-2 rounded bg-accent">
                <div className="text-xs text-muted-foreground">O/U</div>
                <div className="font-display">{odds.overUnder}</div>
              </div>
            </div>
            {odds.moneyline && (
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-2 rounded bg-accent">
                  <div className="text-xs text-muted-foreground">Away ML</div>
                  <div className="font-display">{odds.moneyline.away}</div>
                </div>
                <div className="text-center p-2 rounded bg-accent">
                  <div className="text-xs text-muted-foreground">Home ML</div>
                  <div className="font-display">{odds.moneyline.home}</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Last Play */}
      {lastPlay && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2.5">
              <Bullet />
              Last Play
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="outline" className="mb-2">
              {lastPlay.type}
            </Badge>
            <p className="text-sm leading-relaxed">{lastPlay.text}</p>
          </CardContent>
        </Card>
      )}

      {/* Broadcasts */}
      {broadcasts && broadcasts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2.5">
              <Bullet />
              Broadcasts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2 flex-wrap">
              {broadcasts.map((broadcast, i) => (
                <Badge key={i} variant="secondary">
                  {broadcast}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
