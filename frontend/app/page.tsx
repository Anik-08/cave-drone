"use client";

import { useMemo, useState } from "react";
import type { DataSource, SensorKey } from "@/types/sensor";
import { useSensorWebSocket } from "@/hooks/useSensorWebSocket";
import { analyzeGas, sensorStatus } from "@/lib/gasAnalysis";
import { SENSOR_KEYS } from "@/lib/baseline";
import DashboardHeader from "@/components/DashboardHeader";
import ConnectionStatus from "@/components/ConnectionStatus";
import GasSensorCard from "@/components/GasSensorCard";
import GasChart from "@/components/GasChart";
import GasAnalysis from "@/components/GasAnalysis";
import EnvironmentalStatus from "@/components/EnvironmentalStatus";
import SensorDetailsTable from "@/components/SensorDetailsTable";
import ConcentrationPanel from "@/components/ConcentrationPanel";
import PersonDetection from "@/components/PersonDetection";
import ImageEnhancement from "@/components/ImageEnhancement";
import CaveScan from "@/components/CaveScan";
import VideoScan from "@/components/VideoScan";

const SPARKLINE_POINTS = 48;

export default function DashboardPage() {
  const [mode, setMode] = useState<DataSource>("live");
  const feed = useSensorWebSocket({ mode });

  const analysis = feed.latest ? analyzeGas(feed.latest) : null;

  const sparklines = useMemo(() => {
    const map: Record<SensorKey, number[]> = { mq2: [], mq4: [], mq7: [] };
    const from = Math.max(0, feed.history.length - SPARKLINE_POINTS);
    for (const key of SENSOR_KEYS) {
      map[key] = feed.history.slice(from).map((d) => d[key]);
    }
    return map;
  }, [feed.history]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <DashboardHeader
        source={mode}
        status={feed.status}
        isStale={feed.isStale}
        lastMessageAt={feed.lastMessageAt}
        reconnectAttempt={feed.reconnectAttempt}
        onModeChange={setMode}
      />

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-5 md:px-6">
        <ConnectionStatus
          source={mode}
          status={feed.status}
          isStale={feed.isStale}
          lastMessageAt={feed.lastMessageAt}
          reconnectAttempt={feed.reconnectAttempt}
          now={feed.now}
        />

        <section aria-label="Gas sensor overview" className="grid gap-4 md:grid-cols-3">
          {SENSOR_KEYS.map((key) => (
            <GasSensorCard
              key={key}
              sensorKey={key}
              value={feed.latest ? feed.latest[key] : null}
              status={analysis ? sensorStatus(analysis, key) : null}
              history={sparklines[key]}
              lastUpdateAt={feed.latest?.timestamp ?? null}
              isStale={feed.isStale}
              now={feed.now}
            />
          ))}
        </section>

        <GasChart history={feed.history} />

        <section aria-label="Analysis and status" className="grid gap-4 lg:grid-cols-3">
          <EnvironmentalStatus overall={analysis?.overallStatus ?? null} isStale={feed.isStale} />
          <GasAnalysis analysis={analysis} />
          <ConcentrationPanel latest={feed.latest} />
        </section>

        <SensorDetailsTable
          latest={feed.latest}
          baseline={feed.baseline}
          baselineCollecting={feed.baselineCollecting}
          baselineProgress={feed.baselineProgress}
          analysis={analysis}
          isStale={feed.isStale}
        />

        <PersonDetection />
        <ImageEnhancement />
        <CaveScan />
        <VideoScan />

        <footer className="border-t border-edge pt-4 pb-2">
          <p className="font-mono text-[10px] uppercase tracking-wider text-faint">
            Ground station · MQ-2 / MQ-4 / MQ-7 via Arduino over USB serial · raw ADC values are
            uncalibrated · thresholds are prototype, not validated gas limits
          </p>
        </footer>
      </main>
    </div>
  );
}
