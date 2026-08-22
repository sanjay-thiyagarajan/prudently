"use client";

import { motion } from "framer-motion";
import {
  Activity,
  ExternalLink,
  PowerOff,
  ShieldAlert,
  Timer,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import type { ChaosExperiment } from "@/lib/types/dashboard";

const EXPERIMENT_META: Record<string, { label: string; icon: LucideIcon; accent: string }> = {
  hospital_whatif: {
    label: "Hospital what-if",
    icon: Activity,
    accent: "var(--color-hero)",
  },
  fleet_kill_agent: {
    label: "Kill-agent fault",
    icon: PowerOff,
    accent: "var(--color-critical)",
  },
  fleet_memory_poisoning: {
    label: "Memory poisoning fault",
    icon: ShieldAlert,
    accent: "var(--color-elevated)",
  },
  fleet_latency_injection: {
    label: "Latency injection fault",
    icon: Timer,
    accent: "var(--color-a2a)",
  },
};

function traceConsoleUrl(traceId: string): string {
  return `https://console.cloud.google.com/traces/list?tid=${traceId}&project=prudently-hackathon`;
}

function relativeTime(iso: string): string {
  const deltaMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(deltaMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function ChaosReplay({ experiments }: { experiments: ChaosExperiment[] }) {
  return (
    <Panel title="Chaos & Continuity Replay" icon={Zap} accent="#f472b6">
      {experiments.length === 0 ? (
        <p className="text-sm text-[var(--color-ink-muted)]">
          No experiments run yet — fault-injection results are captured once, then replayed
          here rather than re-run live.
        </p>
      ) : (
        <ul className="space-y-2.5">
          {experiments.map((experiment, index) => {
            const meta = EXPERIMENT_META[experiment.experiment_type] ?? {
              label: experiment.experiment_type,
              icon: Zap,
              accent: "var(--color-hero)",
            };
            const Icon = meta.icon;
            return (
              <motion.li
                key={`${experiment.timestamp}-${index}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                className="rounded-xl border border-[var(--color-border-soft)] p-3.5"
              >
                <div className="flex items-start gap-3">
                  <span
                    className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg"
                    style={{ backgroundColor: `${meta.accent}20`, color: meta.accent }}
                  >
                    <Icon size={15} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className="text-[10px] font-semibold tracking-wide uppercase"
                        style={{ color: meta.accent }}
                      >
                        {meta.label}
                      </span>
                      <span className="text-[10px] text-[var(--color-ink-muted)]">
                        {relativeTime(experiment.timestamp)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-[var(--color-ink-primary)]">
                      {experiment.summary}
                    </p>
                    {experiment.trace_id && (
                      <a
                        href={traceConsoleUrl(experiment.trace_id)}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1.5 inline-flex items-center gap-1 font-mono text-[10px] text-[var(--color-ink-muted)] hover:text-[var(--color-a2a)]"
                      >
                        trace/{experiment.trace_id.slice(0, 12)}…
                        <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                </div>
              </motion.li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}
