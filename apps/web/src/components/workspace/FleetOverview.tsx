"use client";

import { motion } from "framer-motion";
import {
  CalendarClock,
  Handshake,
  Network,
  Package,
  ShieldCheck,
  Truck,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { StatusPill } from "@/components/ui/StatusPill";
import type { FleetAgent } from "@/lib/types/dashboard";

const AGENT_META: Record<
  string,
  { label: string; icon: LucideIcon; blurb: string; accent: string }
> = {
  coordinator: {
    label: "Coordinator",
    icon: Network,
    blurb: "Sole user-facing entry point — routes every call through the Agent Gateway",
    accent: "var(--color-hero)",
  },
  shift_allocation_agent: {
    label: "Shift Allocation",
    icon: CalendarClock,
    blurb: "Fatigue & overtime burndown, reallocation recommendations",
    accent: "var(--color-safe)",
  },
  inventory_management_agent: {
    label: "Inventory Management",
    icon: Package,
    blurb: "Tactical stock and par-level tracking",
    accent: "var(--color-elevated)",
  },
  supply_chain_resiliency_agent: {
    label: "Supply Chain Resiliency",
    icon: Truck,
    blurb: "Strategic reorder decisions and vendor selection",
    accent: "#f97316",
  },
  hr_agent: {
    label: "HR",
    icon: ShieldCheck,
    blurb: "Credentialing and per-diem escalation target",
    accent: "#38bdf8",
  },
  medical_representative_agent: {
    label: "Medical Representative",
    icon: Handshake,
    blurb: "External-facing vendor liaison — Model Armor ingestion boundary",
    accent: "var(--color-a2a)",
  },
  chaos_continuity_agent: {
    label: "Chaos & Continuity",
    icon: Zap,
    blurb: "Hospital what-if projections and fleet fault injection",
    accent: "#f472b6",
  },
};

function AgentCard({ agent, size = "md" }: { agent: FleetAgent; size?: "md" | "lg" }) {
  const meta = AGENT_META[agent.agent_name] ?? {
    label: agent.agent_name,
    icon: Network,
    blurb: agent.role,
    accent: "var(--color-hero)",
  };
  const Icon = meta.icon;
  const isActive = agent.status === "active";
  const isA2A = agent.agent_name === "medical_representative_agent";

  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.015 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className={`group relative overflow-hidden rounded-2xl border bg-[var(--color-surface)]/90 p-5 ${
        isA2A ? "border-dashed" : "border-solid"
      } ${size === "lg" ? "sm:p-6" : ""}`}
      style={{ borderColor: isA2A ? meta.accent : "var(--color-border)" }}
    >
      {isActive && (
        <span
          className="pointer-events-none absolute -top-16 -right-16 size-40 rounded-full opacity-20 blur-3xl"
          style={{ backgroundColor: meta.accent }}
        />
      )}
      <div className="relative flex items-start justify-between gap-3">
        <span
          className={`flex shrink-0 items-center justify-center rounded-2xl ${
            size === "lg" ? "size-14" : "size-11"
          }`}
          style={{ backgroundColor: `${meta.accent}20`, color: meta.accent }}
        >
          {isActive && (
            <span
              className="absolute size-14 animate-pulse-slow rounded-2xl"
              style={{ boxShadow: `0 0 0 1px ${meta.accent}40` }}
            />
          )}
          <Icon size={size === "lg" ? 26 : 20} strokeWidth={2} />
        </span>
        <StatusPill status={agent.status} />
      </div>

      <h3
        className={`relative mt-4 font-[family-name:var(--font-display)] font-semibold text-[var(--color-ink-primary)] ${
          size === "lg" ? "text-lg" : "text-base"
        }`}
      >
        {meta.label}
      </h3>
      <p className="relative mt-1 text-xs leading-relaxed text-[var(--color-ink-secondary)]">
        {meta.blurb}
      </p>

      <div className="relative mt-4 flex items-center justify-between border-t border-[var(--color-border-soft)] pt-3 text-[10px] text-[var(--color-ink-muted)]">
        <span className="font-mono">
          {agent.reasoning_engine_id
            ? `engine/${agent.reasoning_engine_id.slice(0, 8)}…`
            : "no engine"}
        </span>
        {isA2A && (
          <span
            className="rounded-full px-1.5 py-0.5 font-semibold tracking-wide uppercase"
            style={{ backgroundColor: `${meta.accent}20`, color: meta.accent }}
          >
            A2A
          </span>
        )}
      </div>
    </motion.div>
  );
}

export function FleetOverview({ fleet }: { fleet: FleetAgent[] }) {
  const byName = Object.fromEntries(fleet.map((agent) => [agent.agent_name, agent]));
  const coordinator = byName["coordinator"];
  const gatewaySpecialists = [
    "shift_allocation_agent",
    "inventory_management_agent",
    "supply_chain_resiliency_agent",
    "hr_agent",
    "chaos_continuity_agent",
  ]
    .map((name) => byName[name])
    .filter(Boolean);
  const medrep = byName["medical_representative_agent"];

  return (
    <div className="space-y-6">
      {coordinator && (
        <div className="mx-auto max-w-sm">
          <AgentCard agent={coordinator} size="lg" />
        </div>
      )}

      <div className="flex items-center gap-3 px-2">
        <div className="h-px flex-1 bg-[var(--color-border)]" />
        <span className="text-[10px] font-medium tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
          routed through the Agent Gateway
        </span>
        <div className="h-px flex-1 bg-[var(--color-border)]" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {gatewaySpecialists.map((agent) => (
          <AgentCard key={agent.agent_name} agent={agent} />
        ))}
      </div>

      {medrep && (
        <>
          <div className="flex items-center gap-3 px-2">
            <div className="h-px flex-1 bg-[var(--color-border)]" />
            <span
              className="text-[10px] font-medium tracking-[0.2em] uppercase"
              style={{ color: "var(--color-a2a)" }}
            >
              reached via genuine Agent2Agent — not the Gateway
            </span>
            <div className="h-px flex-1 bg-[var(--color-border)]" />
          </div>
          <div className="mx-auto max-w-sm">
            <AgentCard agent={medrep} />
          </div>
        </>
      )}
    </div>
  );
}
