"use client";

import { Loader2, TriangleAlert } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { StatusPill } from "@/components/ui/StatusPill";
import { ActivityFeed } from "@/components/workspace/ActivityFeed";
import { AgentLogViewer } from "@/components/workspace/AgentLogViewer";
import { AgentPolicyEditor } from "@/components/workspace/AgentPolicyEditor";
import { ApprovalsFeed } from "@/components/workspace/ApprovalsFeed";
import { ArmorFeed } from "@/components/workspace/ArmorFeed";
import { ChaosReplay } from "@/components/workspace/ChaosReplay";
import { GuestDoctorHoursPanel } from "@/components/workspace/GuestDoctorHoursPanel";
import { HRPanel } from "@/components/workspace/HRPanel";
import { InventoryPanel } from "@/components/workspace/InventoryPanel";
import { ShiftPanel } from "@/components/workspace/ShiftPanel";
import { SupplyPanel } from "@/components/workspace/SupplyPanel";
import { TraceViewer } from "@/components/workspace/TraceViewer";
import { useAgentDetail } from "@/lib/api/agents";
import { agentMetaFor } from "@/lib/agentMeta";
import type {
  ArmorEvent,
  BurndownRecord,
  ChaosExperiment,
  CredentialRecord,
  CredentialStatus,
  GuestDoctorHours,
  ParLevelRecord,
  ReorderDecision,
  RiskLevel,
  StockStatus,
} from "@/lib/types/dashboard";

// Renders whichever slice(s) of live_state this agent actually has — see
// routes/agents.py's _AGENT_LIVE_STATE_KEYS for the source-of-truth mapping. Coordinator has
// none of its own (it delegates, it doesn't compute), so this can legitimately render nothing.
function LiveState({
  agentName,
  liveState,
}: {
  agentName: string;
  liveState: Record<string, unknown>;
}) {
  if (agentName === "shift_allocation_agent" && liveState.shift) {
    const shift = liveState.shift as {
      records: BurndownRecord[];
      unit_summary: Record<string, Record<RiskLevel, number>>;
    };
    return (
      <ShiftPanel records={shift.records} unitSummary={shift.unit_summary} />
    );
  }
  if (agentName === "inventory_management_agent" && liveState.inventory) {
    const inventory = liveState.inventory as {
      records: ParLevelRecord[];
      category_summary: Record<string, Record<StockStatus, number>>;
    };
    return (
      <InventoryPanel
        records={inventory.records}
        categorySummary={inventory.category_summary}
      />
    );
  }
  if (agentName === "supply_chain_resiliency_agent" && liveState.supply) {
    const supply = liveState.supply as { decisions: ReorderDecision[] };
    return <SupplyPanel decisions={supply.decisions} />;
  }
  if (agentName === "hr_agent" && liveState.hr) {
    const hr = liveState.hr as {
      records: CredentialRecord[];
      unit_summary: Record<string, Record<CredentialStatus, number>>;
    };
    return (
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <HRPanel records={hr.records} unitSummary={hr.unit_summary} />
        <GuestDoctorHoursPanel
          hours={liveState.guest_doctor_hours as GuestDoctorHours[]}
        />
      </div>
    );
  }
  if (agentName === "medical_representative_agent" && liveState.armor_events) {
    return <ArmorFeed events={liveState.armor_events as ArmorEvent[]} />;
  }
  if (agentName === "chaos_continuity_agent" && liveState.chaos_experiments) {
    return (
      <ChaosReplay
        experiments={liveState.chaos_experiments as ChaosExperiment[]}
      />
    );
  }
  return (
    <p className="text-sm text-[var(--color-ink-secondary)]">
      This agent delegates rather than computing its own state — see its
      activity feed instead.
    </p>
  );
}

export default function AgentDetailPage() {
  const params = useParams<{ agentName: string }>();
  const agentName = decodeURIComponent(params.agentName);
  const { data, error, isLoading } = useAgentDetail(agentName);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
        <TriangleAlert className="text-[var(--color-critical)]" size={28} />
        <p className="text-sm text-[var(--color-ink-secondary)]">
          Couldn&apos;t find agent &quot;{agentName}&quot;.
        </p>
      </main>
    );
  }

  const meta = agentMetaFor(agentName);
  const Icon = meta.icon;

  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8 flex items-center gap-4">
        <span
          className="flex size-12 shrink-0 items-center justify-center rounded-2xl"
          style={{ backgroundColor: `${meta.accent}20`, color: meta.accent }}
        >
          <Icon size={22} strokeWidth={2} />
        </span>
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
              {meta.label}
            </h1>
            <StatusPill status={data.agent.status} />
          </div>
          <p className="mt-1 text-sm text-[var(--color-ink-secondary)]">
            {meta.blurb}
          </p>
        </div>
      </div>

      <div className="space-y-8">
        <section>
          <h2 className="mb-3 text-[11px] font-medium tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
            Current responsibilities
          </h2>
          <LiveState agentName={agentName} liveState={data.live_state} />
        </section>

        <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <ActivityFeed
            entries={data.activity_log}
            onSelectTrace={setSelectedTraceId}
          />
          <ApprovalsFeed approvals={data.approvals} />
        </section>

        <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <AgentPolicyEditor taskType={data.policy?.task_type ?? null} />
          <AgentLogViewer agentName={agentName} />
        </section>
      </div>

      {selectedTraceId && (
        <TraceViewer
          traceId={selectedTraceId}
          onClose={() => setSelectedTraceId(null)}
        />
      )}
    </main>
  );
}
