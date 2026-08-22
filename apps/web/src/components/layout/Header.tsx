"use client";

import { motion } from "framer-motion";
import { Activity } from "lucide-react";

import { AnimatedNumber } from "@/components/ui/AnimatedNumber";

interface HeaderProps {
  asOf: string;
  activeAgents: number;
  totalAgents: number;
  criticalAlerts: number;
  isLive: boolean;
}

export function Header({ asOf, activeAgents, totalAgents, criticalAlerts, isLive }: HeaderProps) {
  return (
    <header className="relative overflow-hidden border-b border-[var(--color-border)] px-6 py-10 sm:px-10">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-border-soft) 1px, transparent 1px), linear-gradient(90deg, var(--color-border-soft) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse 70% 60% at 50% 0%, black, transparent)",
        }}
      />
      <div className="relative mx-auto flex max-w-7xl flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="mb-3 flex items-center gap-2 text-[11px] font-medium tracking-[0.25em] text-[var(--color-hero)] uppercase">
            <span className="relative flex size-2">
              <span
                className={`absolute inline-flex size-full rounded-full bg-[var(--color-hero)] opacity-75 ${isLive ? "animate-ping" : ""}`}
              />
              <span className="relative inline-flex size-2 rounded-full bg-[var(--color-hero)]" />
            </span>
            Fortified Enterprise Fleet
          </div>
          <h1 className="font-[family-name:var(--font-display)] text-4xl font-bold text-[var(--color-ink-primary)] sm:text-5xl">
            Prudently
          </h1>
          <p className="mt-2 max-w-md text-sm text-[var(--color-ink-secondary)]">
            Seven agents keeping one hospital ahead of the next crisis — live from the deployed
            fleet, as of {asOf}.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex gap-3"
        >
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/80 px-5 py-3.5 text-center backdrop-blur-sm">
            <p className="font-[family-name:var(--font-display)] text-2xl font-bold text-[var(--color-safe)]">
              <AnimatedNumber value={activeAgents} />
              <span className="text-base text-[var(--color-ink-muted)]">/{totalAgents}</span>
            </p>
            <p className="text-[10px] tracking-wide text-[var(--color-ink-muted)] uppercase">
              agents active
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/80 px-5 py-3.5 text-center backdrop-blur-sm">
            <p
              className="font-[family-name:var(--font-display)] text-2xl font-bold"
              style={{
                color:
                  criticalAlerts > 0 ? "var(--color-critical)" : "var(--color-ink-secondary)",
              }}
            >
              <AnimatedNumber value={criticalAlerts} />
            </p>
            <p className="flex items-center justify-center gap-1 text-[10px] tracking-wide text-[var(--color-ink-muted)] uppercase">
              <Activity size={10} /> critical alerts
            </p>
          </div>
        </motion.div>
      </div>
    </header>
  );
}
