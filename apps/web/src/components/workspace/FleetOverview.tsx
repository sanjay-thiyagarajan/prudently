"use client";

import { motion } from "framer-motion";
import { Brain, Radio } from "lucide-react";
import Link from "next/link";

import { StatusPill } from "@/components/ui/StatusPill";
import { AGENT_ACCENT, agentMetaFor } from "@/lib/agentMeta";
import type { FleetAgent } from "@/lib/types/dashboard";

const GATEWAY_SPECIALISTS = [
  "shift_allocation_agent",
  "inventory_management_agent",
  "supply_chain_resiliency_agent",
  "hr_agent",
  "chaos_continuity_agent",
];

function AgentCard({ agent, prominent = false }: { agent: FleetAgent; prominent?: boolean }) {
  const meta = agentMetaFor(agent.agent_name);
  const Icon = meta.icon;
  const accent = AGENT_ACCENT[meta.kind];
  const isExternal = meta.kind === "external";

  return (
    <motion.div whileHover={{ y: -2 }} transition={{ type: "spring", stiffness: 400, damping: 26 }}>
      <Link
        href={`/agents/${encodeURIComponent(agent.agent_name)}`}
        className={`group flex h-full flex-col rounded-xl bg-[var(--color-surface)] p-4 shadow-[var(--shadow-panel)] transition-colors hover:bg-[var(--color-surface-hover)] ${
          isExternal
            ? "border border-dashed border-[var(--color-a2a)]"
            : "border border-[var(--color-border)]"
        } ${prominent ? "sm:p-5" : ""}`}
      >
        <div className="flex items-start justify-between gap-3">
          <span
            aria-hidden
            className={`flex shrink-0 items-center justify-center rounded-lg ${
              prominent ? "size-10" : "size-9"
            }`}
            style={{ backgroundColor: `${accent}1a`, color: accent }}
          >
            <Icon size={prominent ? 20 : 18} strokeWidth={2.1} />
          </span>
          <StatusPill status={agent.status} />
        </div>

        <h3
          className={`mt-3 font-[family-name:var(--font-display)] font-semibold tracking-tight text-[var(--color-ink-primary)] ${
            prominent ? "text-[16px]" : "text-[14px]"
          }`}
        >
          {meta.label}
        </h3>
        <p className="mt-1 flex-1 text-[12px] leading-relaxed text-[var(--color-ink-secondary)]">
          {meta.blurb}
        </p>

        {(meta.memoryScope || meta.autonomous) && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            {meta.memoryScope && (
              <span
                title="Has its own Memory Bank store on its own Reasoning Engine"
                className="inline-flex items-center gap-1 rounded border border-[var(--color-border)] px-1.5 py-0.5 text-[10px] text-[var(--color-ink-muted)]"
              >
                <Brain size={10} strokeWidth={2.2} />
                {meta.memoryScope}
              </span>
            )}
            {meta.autonomous && (
              <span
                title="The fleet watch can wake this agent with nobody in the room"
                className="inline-flex items-center gap-1 rounded border border-[var(--color-autonomous)]/35 bg-[var(--color-autonomous-soft)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-autonomous)]"
              >
                <Radio size={10} strokeWidth={2.2} />
                self-starting
              </span>
            )}
          </div>
        )}

        <p className="mt-3 border-t border-[var(--color-border-soft)] pt-2.5 font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-ink-muted)]">
          {agent.reasoning_engine_id
            ? `engine ${agent.reasoning_engine_id.slice(0, 10)}…`
            : "no engine"}
        </p>
      </Link>
    </motion.div>
  );
}

/** A labelled rail between tiers — the label is the mechanism, not decoration. */
function Rail({ children, dashed = false }: { children: React.ReactNode; dashed?: boolean }) {
  const line = dashed
    ? "border-t border-dashed border-[var(--color-a2a)]/50"
    : "border-t border-[var(--color-border)]";
  return (
    <div className="flex items-center gap-3 py-1">
      <div className={`h-0 flex-1 ${line}`} />
      <span
        className={`text-center font-[family-name:var(--font-mono)] text-[10px] tracking-[0.12em] uppercase ${
          dashed ? "text-[var(--color-a2a)]" : "text-[var(--color-ink-muted)]"
        }`}
      >
        {children}
      </span>
      <div className={`h-0 flex-1 ${line}`} />
    </div>
  );
}

/**
 * The fleet drawn as its actual topology rather than a flat grid of cards: one hub, a Gateway
 * every internal call passes through, and one agent on the far side of a real trust boundary
 * reached only by Agent2Agent. A grid would imply seven peers, which is not the architecture.
 */
export function FleetOverview({ fleet }: { fleet: FleetAgent[] }) {
  const byName = Object.fromEntries(fleet.map((agent) => [agent.agent_name, agent]));
  const coordinator = byName["coordinator"];
  const specialists = GATEWAY_SPECIALISTS.map((name) => byName[name]).filter(Boolean);
  const medrep = byName["medical_representative_agent"];

  return (
    <div className="space-y-4">
      {coordinator && (
        <div className="mx-auto max-w-xs">
          <AgentCard agent={coordinator} prominent />
        </div>
      )}

      <Rail>registry lookup → policy check → tool</Rail>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {specialists.map((agent) => (
          <AgentCard key={agent.agent_name} agent={agent} />
        ))}
      </div>

      {medrep && (
        <>
          <Rail dashed>external trust boundary · reached over Agent2Agent, not the Gateway</Rail>
          <div className="mx-auto max-w-xs">
            <AgentCard agent={medrep} />
          </div>
          <p className="mx-auto max-w-md text-center text-[11px] leading-relaxed text-[var(--color-ink-muted)]">
            Supply Chain reaches this agent at its public agent-card URL, the same way any
            outside client would. Everything it receives is screened before a model sees it.
          </p>
        </>
      )}
    </div>
  );
}
