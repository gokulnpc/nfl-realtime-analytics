"use client"

import type React from "react"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bullet } from "@/components/ui/bullet"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { NFL_TEAMS } from "@/lib/nfl-data"

interface ManualInputFormProps {
  onSubmit: (data: any) => void
  loading?: boolean
}

export function ManualInputForm({ onSubmit, loading }: ManualInputFormProps) {
  const [formData, setFormData] = useState({
    down: 1,
    ydstogo: 10,
    yardline_100: 75,
    qtr: 1,
    half_seconds_remaining: 900,
    score_differential: 0,
    shotgun: 1,
    no_huddle: 0,
    defenders_in_box: 6,
    number_of_pass_rushers: 4,
    posteam_type: "home",
    goal_to_go: 0,
    posteam: "KC",
    defteam: "SF",
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  const quickScenarios = [
    {
      name: "Goal Line Stand",
      data: { down: 1, ydstogo: 2, yardline_100: 2, qtr: 4, half_seconds_remaining: 120, score_differential: -4 },
    },
    {
      name: "4th Quarter Comeback",
      data: { down: 4, ydstogo: 10, yardline_100: 45, qtr: 4, half_seconds_remaining: 120, score_differential: -7 },
    },
    {
      name: "Red Zone",
      data: { down: 1, ydstogo: 10, yardline_100: 15, qtr: 2, half_seconds_remaining: 300, score_differential: 0 },
    },
    {
      name: "3rd & Long",
      data: { down: 3, ydstogo: 15, yardline_100: 75, qtr: 3, half_seconds_remaining: 450, score_differential: 3 },
    },
  ]

  const applyScenario = (data: any) => {
    setFormData({ ...formData, ...data })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5">
          <Bullet />
          Manual Input
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Quick Scenarios */}
          <div className="space-y-2">
            <Label>Quick Scenarios</Label>
            <div className="grid grid-cols-2 gap-2">
              {quickScenarios.map((scenario) => (
                <Button
                  key={scenario.name}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => applyScenario(scenario.data)}
                >
                  {scenario.name}
                </Button>
              ))}
            </div>
          </div>

          {/* Down */}
          <div className="space-y-2">
            <Label>Down</Label>
            <Select
              value={formData.down.toString()}
              onValueChange={(v) => setFormData({ ...formData, down: Number.parseInt(v) })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4].map((d) => (
                  <SelectItem key={d} value={d.toString()}>
                    {d}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Distance */}
          <div className="space-y-2">
            <Label>Distance (yards to go)</Label>
            <Input
              type="number"
              min={1}
              max={99}
              value={formData.ydstogo}
              onChange={(e) => setFormData({ ...formData, ydstogo: Number.parseInt(e.target.value) })}
            />
          </div>

          {/* Yard Line */}
          <div className="space-y-2">
            <Label>Yard Line (distance from opponent end zone)</Label>
            <Input
              type="number"
              min={1}
              max={99}
              value={formData.yardline_100}
              onChange={(e) => setFormData({ ...formData, yardline_100: Number.parseInt(e.target.value) })}
            />
          </div>

          {/* Quarter */}
          <div className="space-y-2">
            <Label>Quarter</Label>
            <Select
              value={formData.qtr.toString()}
              onValueChange={(v) => setFormData({ ...formData, qtr: Number.parseInt(v) })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4].map((q) => (
                  <SelectItem key={q} value={q.toString()}>
                    Q{q}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Time Remaining */}
          <div className="space-y-2">
            <Label>Time Remaining (seconds)</Label>
            <Input
              type="number"
              min={0}
              max={900}
              value={formData.half_seconds_remaining}
              onChange={(e) => setFormData({ ...formData, half_seconds_remaining: Number.parseInt(e.target.value) })}
            />
          </div>

          {/* Score Differential */}
          <div className="space-y-2">
            <Label>Score Differential: {formData.score_differential}</Label>
            <Slider
              value={[formData.score_differential]}
              onValueChange={(v) => setFormData({ ...formData, score_differential: v[0] })}
              min={-50}
              max={50}
              step={1}
            />
          </div>

          {/* Possession Team */}
          <div className="space-y-2">
            <Label>Possession Team</Label>
            <Select value={formData.posteam} onValueChange={(v) => setFormData({ ...formData, posteam: v })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {NFL_TEAMS.map((team) => (
                  <SelectItem key={team.abbr} value={team.abbr}>
                    {team.abbr} - {team.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Defense Team */}
          <div className="space-y-2">
            <Label>Defense Team</Label>
            <Select value={formData.defteam} onValueChange={(v) => setFormData({ ...formData, defteam: v })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {NFL_TEAMS.map((team) => (
                  <SelectItem key={team.abbr} value={team.abbr}>
                    {team.abbr} - {team.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Loading..." : "Get Predictions"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
