"use client"

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

export type NFLMode = "simulation" | "live" | "manual"

interface ModeSelectorProps {
  mode: NFLMode
  onModeChange: (mode: NFLMode) => void
}

export function ModeSelector({ mode, onModeChange }: ModeSelectorProps) {
  return (
    <Tabs value={mode} onValueChange={(v) => onModeChange(v as NFLMode)}>
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="simulation">Simulation</TabsTrigger>
        <TabsTrigger value="live">Live</TabsTrigger>
        <TabsTrigger value="manual">Manual</TabsTrigger>
      </TabsList>
    </Tabs>
  )
}
