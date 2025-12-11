"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import DashboardPageLayout from "@/components/dashboard/layout";
import { Activity } from "lucide-react";
import type { NFLMode } from "@/components/nfl/mode-selector";
import { Scoreboard } from "@/components/nfl/scoreboard";
import { TeamPanel } from "@/components/nfl/team-panel";
import { PredictionsPanel } from "@/components/nfl/predictions-panel";
import { WinProbability } from "@/components/nfl/win-probability";
import { GameInfo } from "@/components/nfl/game-info";
import { ManualInputForm } from "@/components/nfl/manual-input-form";
import type { PlayData } from "@/types/nfl";
import { DEMO_PLAY } from "@/lib/nfl-data";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Demo plays for simulation mode
const demoPlays = [
  {
    down: 1,
    ydstogo: 10,
    yardline_100: 75,
    qtr: 1,
    half_seconds_remaining: 900,
    score_differential: 0,
    posteam: "KC",
    defteam: "SF",
    description: "Opening drive",
  },
  {
    down: 3,
    ydstogo: 2,
    yardline_100: 45,
    qtr: 2,
    half_seconds_remaining: 600,
    score_differential: -7,
    posteam: "BUF",
    defteam: "MIA",
    description: "Short yardage situation",
  },
  {
    down: 1,
    ydstogo: 10,
    yardline_100: 15,
    qtr: 3,
    half_seconds_remaining: 450,
    score_differential: 3,
    posteam: "PHI",
    defteam: "DAL",
    description: "Red zone opportunity",
  },
  {
    down: 4,
    ydstogo: 1,
    yardline_100: 35,
    qtr: 4,
    half_seconds_remaining: 180,
    score_differential: -4,
    posteam: "SF",
    defteam: "KC",
    description: "Go for it on 4th!",
  },
  {
    down: 2,
    ydstogo: 8,
    yardline_100: 98,
    qtr: 4,
    half_seconds_remaining: 45,
    score_differential: -6,
    posteam: "KC",
    defteam: "SF",
    description: "Goal line, game on the line!",
  },
  {
    down: 3,
    ydstogo: 15,
    yardline_100: 35,
    qtr: 4,
    half_seconds_remaining: 120,
    score_differential: -7,
    posteam: "DAL",
    defteam: "PHI",
    description: "3rd and long, trailing",
  },
];

function NFLDashboardContent() {
  const searchParams = useSearchParams();
  const mode = (searchParams.get("mode") || "simulation") as NFLMode;
  const [currentPlay, setCurrentPlay] = useState<PlayData>(DEMO_PLAY);
  const [loading, setLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [apiStatus, setApiStatus] = useState<"connected" | "disconnected">(
    "disconnected"
  );
  const [demoIndex, setDemoIndex] = useState(0);

  // Check API health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_URL}/health`);
        if (response.ok) {
          setApiStatus("connected");
        } else {
          setApiStatus("disconnected");
        }
      } catch {
        setApiStatus("disconnected");
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Get predictions for a play
  const getPredictions = useCallback(async (play: (typeof demoPlays)[0]) => {
    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...play,
          shotgun: 1,
          no_huddle: 0,
          defenders_in_box: 6,
          number_of_pass_rushers: 4,
          posteam_type: "home",
          goal_to_go: play.yardline_100 <= play.ydstogo ? 1 : 0,
        }),
      });
      const data = await response.json();

      // Create a play object from the prediction
      const playData: PlayData = {
        ...DEMO_PLAY,
        ...play,
        ...data.predictions,
        source: "simulation",
        timestamp: new Date().toISOString(),
        // Update basic team info
        posteam: play.posteam,
        defteam: play.defteam,
        home_team: play.posteam === "KC" ? "KC" : play.defteam,
        away_team: play.posteam === "KC" ? "SF" : play.posteam,
        home_score: play.score_differential > 0 ? 7 : 0,
        away_score:
          play.score_differential < 0 ? Math.abs(play.score_differential) : 0,
        // Update situation
        situation: {
          ...DEMO_PLAY.situation,
          down: play.down,
          distance: play.ydstogo,
          ydstogo: play.ydstogo,
          yardLine: 100 - play.yardline_100,
          yardline_100: play.yardline_100,
          possession: play.posteam,
          downDistanceText: `${play.down} & ${play.ydstogo} at ${
            100 - play.yardline_100
          }`,
          shortDownDistanceText: `${play.down} & ${play.ydstogo}`,
          possessionText: `${play.posteam} has possession`,
        },
        // Update status
        status: {
          ...DEMO_PLAY.status,
          period: play.qtr,
          displayClock: `${Math.floor(
            play.half_seconds_remaining / 60
          )}:${String(play.half_seconds_remaining % 60).padStart(2, "0")}`,
          detail: `Q${play.qtr} - ${Math.floor(
            play.half_seconds_remaining / 60
          )}:${String(play.half_seconds_remaining % 60).padStart(2, "0")}`,
          shortDetail: `Q${play.qtr} ${Math.floor(
            play.half_seconds_remaining / 60
          )}:${String(play.half_seconds_remaining % 60).padStart(2, "0")}`,
        },
      };

      setCurrentPlay(playData);
    } catch (error) {
      console.error("[NFL] Error getting prediction:", error);
    }
  }, []);

  // Simulation mode - cycle through demo plays
  useEffect(() => {
    if (mode !== "simulation") {
      return;
    }

    // Start with first play immediately
    getPredictions(demoPlays[0]);
    setDemoIndex(0);

    // Cycle through plays every 4 seconds
    const interval = setInterval(() => {
      setDemoIndex((prev) => {
        const next = (prev + 1) % demoPlays.length;
        getPredictions(demoPlays[next]);
        return next;
      });
    }, 4000);

    return () => clearInterval(interval);
  }, [mode, getPredictions]);

  // Polling for live mode
  useEffect(() => {
    if (mode === "live" && isPolling) {
      const poll = async () => {
        try {
          const response = await fetch(`${API_URL}/kinesis/fetch`);
          const data = await response.json();
          if (data.plays && data.plays.length > 0) {
            setCurrentPlay(data.plays[data.plays.length - 1]);
          }
        } catch (error) {
          console.error("[v0] Error polling:", error);
        }
      };
      const interval = setInterval(poll, 3000);
      poll();
      return () => clearInterval(interval);
    }
  }, [mode, isPolling]);

  // Handle manual prediction
  const handleManualSubmit = useCallback(async (formData: any) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const data = await response.json();

      // Create a play object from the prediction
      const play: PlayData = {
        ...DEMO_PLAY,
        ...data.input,
        ...data.predictions,
        source: "manual",
        timestamp: new Date().toISOString(),
      };

      setCurrentPlay(play);
    } catch (error) {
      console.error("[v0] Error getting prediction:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const hasPossession = (team: string) =>
    currentPlay.situation?.possession === team;

  return (
    <DashboardPageLayout
      header={{
        title: "NFL Analytics",
        description:
          mode === "simulation"
            ? "SIMULATION MODE"
            : mode === "live"
            ? "● LIVE"
            : "MANUAL INPUT",
        icon: Activity,
      }}
    >
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge
            variant={apiStatus === "connected" ? "default" : "destructive"}
          >
            {apiStatus === "connected" ? "API Connected" : "API Disconnected"}
          </Badge>
          {mode === "simulation" && <Badge variant="outline">Demo Data</Badge>}
        </div>

        {mode === "live" && (
          <Button
            variant={isPolling ? "destructive" : "default"}
            size="sm"
            onClick={() => setIsPolling(!isPolling)}
          >
            {isPolling ? "Stop Polling" : "Start Polling"}
          </Button>
        )}
      </div>

      {/* Manual Input Form */}
      {mode === "manual" && (
        <ManualInputForm onSubmit={handleManualSubmit} loading={loading} />
      )}

      {/* Main Dashboard */}
      {mode !== "manual" && (
        <>
          {/* Scoreboard */}
          <Scoreboard
            play={currentPlay}
            isLive={mode === "live" && isPolling}
          />

          {/* Three Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Away Team */}
            <TeamPanel
              team={currentPlay.away_team_full}
              hasPossession={hasPossession(
                currentPlay.away_team_full.abbreviation
              )}
            />

            {/* Center: Predictions & Win Probability */}
            <div className="space-y-6">
              <WinProbability play={currentPlay} />
              <PredictionsPanel play={currentPlay} />
            </div>

            {/* Right: Home Team */}
            <TeamPanel
              team={currentPlay.home_team_full}
              hasPossession={hasPossession(
                currentPlay.home_team_full.abbreviation
              )}
            />
          </div>

          {/* Bottom: Game Info */}
          <GameInfo play={currentPlay} />
        </>
      )}

      {/* Manual Mode Results */}
      {mode === "manual" && currentPlay.source === "manual" && (
        <div className="space-y-6">
          <PredictionsPanel play={currentPlay} />
          <WinProbability play={currentPlay} />
        </div>
      )}
    </DashboardPageLayout>
  );
}

export default function NFLDashboard() {
  return (
    <Suspense
      fallback={
        <DashboardPageLayout
          header={{
            title: "NFL Analytics",
            description: "Loading...",
            icon: Activity,
          }}
        >
          <div className="flex items-center justify-center h-64">
            <p className="text-muted-foreground">Loading...</p>
          </div>
        </DashboardPageLayout>
      }
    >
      <NFLDashboardContent />
    </Suspense>
  );
}
