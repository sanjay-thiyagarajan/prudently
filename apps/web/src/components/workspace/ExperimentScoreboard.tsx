"use client";

import { Activity, PowerOff, ShieldAlert, Timer, Zap, type LucideIcon } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import type { ChaosExperiment } from "@/lib/types/dashboard";

const EXPERIMENT_META: Record<string, { label: string; icon: LucideIcon; accent: string }> = {
  hospital_whatif: { label: "What-if", icon: Activity, accent: "var(--color-hero)" },
  fleet_kill_agent: { label: "Kill-agent", icon: PowerOff, accent: "var(--color-critical)" },
  fleet_memory_poisoning: { label: "Memory poisoning", icon: ShieldAlert, accent: "var(--color-elevated)" },
  fleet_latency_injection: { label: "Latency", icon: Timer, accent: "var(--color-a2a)" },
};

/** Sits above ChaosReplay's own chronological list — this answers "has anyone actually run
 * the fault library" at a glance, which a growing replay list makes harder to see, not easier. */
export function ExperimentScoreboard({ experiments }: { experiments: ChaosExperiment[] }) {
  const counts = new Map<string, number>();
  for (const e of experiments) {
    counts.set(e.experiment_type, (counts.get(e.experiment_type) ?? 0) + 1);
  }
  const types = Object.keys(EXPERIMENT_META);

  return (
    <Panel title="Fault library coverage" icon={Zap} subtitle="Which fault types have actually been run">
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {types.map((type) => {
          const meta = EXPERIMENT_META[type];
          const Icon = meta.icon;
          const count = counts.get(type) ?? 0;
          return (
            <div
              key={type}
              className="rounded-lg border px-3 py-2.5 text-center"
              style={{
                borderColor: count > 0 ? `${meta.accent}40` : "var(--color-border-soft)",
                backgroundColor: count > 0 ? `${meta.accent}12` : "var(--color-sunk)",
              }}
            >
              <Icon size={15} style={{ color: count > 0 ? meta.accent : "var(--color-ink-muted)" }} className="mx-auto" />
              <p
                className="tnum mt-1.5 font-[family-name:var(--font-display)] text-base font-semibold"
                style={{ color: count > 0 ? meta.accent : "var(--color-ink-muted)" }}
              >
                {count}
              </p>
              <p className="mt-0.5 truncate text-[10px] text-[var(--color-ink-muted)]">{meta.label}</p>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
