"use client"

import type { PlayData } from "@/types/nfl"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bullet } from "@/components/ui/bullet"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import NumberFlow from "@number-flow/react"

interface PredictionsPanelProps {
  play: PlayData
}

export function PredictionsPanel({ play }: PredictionsPanelProps) {
  const {
    expected_points,
    td_prob,
    fg_prob,
    no_score_prob,
    pass_probability,
    run_probability,
    predicted_play,
    pressure_probability,
    pressure_risk,
  } = play

  const getRiskColor = (risk: string) => {
    if (risk === "high") return "text-destructive"
    if (risk === "medium") return "text-warning"
    return "text-success"
  }

  return (
    <div className="space-y-6">
      {/* Expected Points */}
      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="flex items-center gap-2.5">
            <Bullet variant={expected_points > 0 ? "success" : "default"} />
            Expected Points
          </CardTitle>
        </CardHeader>
        <CardContent className="bg-gradient-to-br from-primary/20 to-accent pt-6">
          <div className="text-center">
            <div className="text-6xl font-display">
              <NumberFlow value={expected_points} format={{ signDisplay: "always", minimumFractionDigits: 2 }} />
            </div>
            <div className="text-xs text-muted-foreground mt-2">EP from this position</div>
          </div>
        </CardContent>
      </Card>

      {/* Scoring Probabilities */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2.5">
            <Bullet />
            Scoring Probabilities
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ProbabilityBar label="Touchdown" value={td_prob * 100} color="success" />
          <ProbabilityBar label="Field Goal" value={fg_prob * 100} color="warning" />
          <ProbabilityBar label="No Score" value={no_score_prob * 100} color="muted" />
        </CardContent>
      </Card>

      {/* Play Type Prediction */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2.5">
            <Bullet />
            Play Prediction
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center py-4">
            <Badge variant="default" className="text-2xl font-display px-6 py-2">
              {predicted_play.toUpperCase()}
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="text-center p-3 rounded-lg bg-accent">
              <div className="text-2xl font-display">
                <NumberFlow value={pass_probability * 100} suffix="%" />
              </div>
              <div className="text-xs text-muted-foreground">Pass</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-accent">
              <div className="text-2xl font-display">
                <NumberFlow value={run_probability * 100} suffix="%" />
              </div>
              <div className="text-xs text-muted-foreground">Run</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Pressure Risk */}
      <Card
        className={cn(
          "border-l-4",
          pressure_risk === "high" && "border-l-destructive",
          pressure_risk === "medium" && "border-l-warning",
          pressure_risk === "low" && "border-l-success",
        )}
      >
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Bullet />
              Pressure Risk
            </div>
            <Badge
              variant={pressure_risk === "high" ? "destructive" : pressure_risk === "medium" ? "default" : "secondary"}
            >
              {pressure_risk.toUpperCase()}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Pressure Probability</span>
            <span className={cn("text-2xl font-display", getRiskColor(pressure_risk))}>
              <NumberFlow value={pressure_probability * 100} suffix="%" />
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

interface ProbabilityBarProps {
  label: string
  value: number
  color: "success" | "warning" | "muted"
}

function ProbabilityBar({ label, value, color }: ProbabilityBarProps) {
  const getColorClass = () => {
    if (color === "success") return "bg-success"
    if (color === "warning") return "bg-warning"
    return "bg-muted-foreground"
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-display">{value.toFixed(1)}%</span>
      </div>
      <div className="relative h-2 bg-accent rounded-full overflow-hidden">
        <div className={cn("h-full transition-all duration-500", getColorClass())} style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}
