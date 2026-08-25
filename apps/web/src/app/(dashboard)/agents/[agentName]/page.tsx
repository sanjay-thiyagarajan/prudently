"use client";

import { Info, Loader2, TriangleAlert } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { InfoCard } from "@/components/ui/InfoCard";
import { Panel } from "@/components/ui/Panel";
import type { RecordColumn } from "@/components/ui/RecordTable";
import { RecordTable } from "@/components/ui/RecordTable";
import { StatStrip, type Stat } from "@/components/ui/StatCard";
import { StatusPill } from "@/components/ui/StatusPill";
import { ActivityFeed } from "@/components/workspace/ActivityFeed";
import { AgentIdentityPanel } from "@/components/workspace/AgentIdentityPanel";
import { AgentLogViewer } from "@/components/workspace/AgentLogViewer";
import { AgentMemoryPanel, type MemorySubject } from "@/components/workspace/AgentMemoryPanel";
import { AgentPolicyEditor } from "@/components/workspace/AgentPolicyEditor";
import { ApprovalsFeed } from "@/components/workspace/ApprovalsFeed";
import { ArmorFeed } from "@/components/workspace/ArmorFeed";
import { ChaosReplay } from "@/components/workspace/ChaosReplay";
import { CoordinatorRoutingPanel } from "@/components/workspace/CoordinatorRoutingPanel";
import { CredentialComplianceDonut } from "@/components/workspace/CredentialComplianceDonut";
import { ExperimentScoreboard } from "@/components/workspace/ExperimentScoreboard";
import { FatigueBurndownChart } from "@/components/workspace/FatigueBurndownChart";
import { GuestDoctorHoursPanel } from "@/components/workspace/GuestDoctorHoursPanel";
import { HRPanel } from "@/components/workspace/HRPanel";
import { InventoryPanel } from "@/components/workspace/InventoryPanel";
import { MiniActivityList } from "@/components/workspace/MiniActivityList";
import { ORTimelinePanel } from "@/components/workspace/ORTimelinePanel";
import { ScreeningScoreboard } from "@/components/workspace/ScreeningScoreboard";
import { ShiftPanel } from "@/components/workspace/ShiftPanel";
import { SupplyPanel } from "@/components/workspace/SupplyPanel";
import { SupplyRunwayChart } from "@/components/workspace/SupplyRunwayChart";
import { SurgicalSchedulePanel } from "@/components/workspace/SurgicalSchedulePanel";
import { TraceViewer } from "@/components/workspace/TraceViewer";
import { VendorReliabilityChart } from "@/components/workspace/VendorReliabilityChart";
import { useAgentDetail } from "@/lib/api/agents";
import { accentFor, agentMetaFor, AGENT_META } from "@/lib/agentMeta";
import type {
  ActivityLogEntry,
  Approval,
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
  SurgicalCase,
  SurgicalCaseConflict,
} from "@/lib/types/dashboard";

// What a manager can ask this agent to recall, and in what unit — mirrors
// routes/traces.py's `_MEMORY_SUBJECT_LABEL`. Built from data already on the page (the same
// records LiveState renders), never a second fetch: the subject list is exactly "the things
// this agent's own responsibilities panel is already showing you."
const MEMORY_SUBJECT_LABEL: Record<string, string> = {
  shift_allocation_agent: "unit",
  inventory_management_agent: "SKU",
  supply_chain_resiliency_agent: "SKU",
  hr_agent: "staff member",
  surgical_scheduling_agent: "conflict",
  chaos_continuity_agent: "experiment",
};

function memorySubjectsFor(agentName: string, liveState: Record<string, unknown>): MemorySubject[] {
  if (agentName === "shift_allocation_agent" && liveState.shift) {
    const shift = liveState.shift as { unit_summary: Record<string, unknown> };
    return Object.keys(shift.unit_summary ?? {}).map((unit) => ({ value: unit, label: unit }));
  }
  if (agentName === "inventory_management_agent" && liveState.inventory) {
    const inventory = liveState.inventory as { records: ParLevelRecord[] };
    const flagged = inventory.records.filter((r) => r.stock_status !== "ok");
    return (flagged.length > 0 ? flagged : inventory.records)
      .slice(0, 25)
      .map((r) => ({ value: r.sku, label: r.name }));
  }
  if (agentName === "supply_chain_resiliency_agent" && liveState.supply) {
    const supply = liveState.supply as { decisions: ReorderDecision[] };
    return supply.decisions.map((d) => ({ value: d.sku, label: d.name }));
  }
  if (agentName === "hr_agent" && liveState.hr) {
    const hr = liveState.hr as { records: CredentialRecord[] };
    const flagged = hr.records.filter((r) => r.credential_status !== "valid");
    return (flagged.length > 0 ? flagged : hr.records)
      .slice(0, 25)
      .map((r) => ({ value: r.staff_id, label: r.name }));
  }
  if (agentName === "surgical_scheduling_agent" && liveState.surgical_schedule) {
    const schedule = liveState.surgical_schedule as {
      conflicts: { case_id_a: string; case_id_b: string }[];
    };
    return schedule.conflicts.map((c) => {
      const pair = [c.case_id_a, c.case_id_b].sort();
      return { value: `${pair[0]}::${pair[1]}`, label: `${c.case_id_a} vs ${c.case_id_b}` };
    });
  }
  if (agentName === "chaos_continuity_agent") {
    return [{ value: "chaos-poisoning-experiment", label: "Poisoning experiment" }];
  }
  return [];
}

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
  if (agentName === "surgical_scheduling_agent") {
    return <SurgicalSchedulePanel />;
  }
  return (
    <p className="text-sm text-[var(--color-ink-secondary)]">
      This agent delegates rather than computing its own state — see its
      activity feed instead.
    </p>
  );
}

// The one thing about this agent's own domain that a table can't show as well as a picture —
// deliberately not the same chart type twice in a row across the fleet (see each component's
// own docstring for why that specific shape fits that specific domain).
function AgentInsight({
  agentName,
  liveState,
  activityLog,
}: {
  agentName: string;
  liveState: Record<string, unknown>;
  activityLog: ActivityLogEntry[];
}) {
  if (agentName === "shift_allocation_agent" && liveState.shift) {
    const shift = liveState.shift as { records: BurndownRecord[] };
    return <FatigueBurndownChart records={shift.records} />;
  }
  if (agentName === "inventory_management_agent" && liveState.inventory) {
    const inventory = liveState.inventory as { records: ParLevelRecord[] };
    return <SupplyRunwayChart records={inventory.records} />;
  }
  if (agentName === "supply_chain_resiliency_agent" && liveState.supply) {
    const supply = liveState.supply as { decisions: ReorderDecision[] };
    return <VendorReliabilityChart decisions={supply.decisions} />;
  }
  if (agentName === "hr_agent" && liveState.hr) {
    const hr = liveState.hr as { unit_summary: Record<string, Record<CredentialStatus, number>> };
    return <CredentialComplianceDonut unitSummary={hr.unit_summary} />;
  }
  if (agentName === "medical_representative_agent" && liveState.armor_events) {
    return <ScreeningScoreboard events={liveState.armor_events as ArmorEvent[]} />;
  }
  if (agentName === "chaos_continuity_agent" && liveState.chaos_experiments) {
    return <ExperimentScoreboard experiments={liveState.chaos_experiments as ChaosExperiment[]} />;
  }
  if (agentName === "surgical_scheduling_agent") {
    return <ORTimelinePanel />;
  }
  if (agentName === "coordinator") {
    return <CoordinatorRoutingPanel activityLog={activityLog} />;
  }
  return null;
}

// A quick-vitals strip, entirely agent-specific — the numbers a manager would ask for first
// about that one domain, not a generic "records / errors / uptime" template repeated seven
// times. `approvals` is already scoped to this agent by routes/agents.py's get_agent_detail.
function agentStats(
  agentName: string,
  liveState: Record<string, unknown>,
  activityLog: ActivityLogEntry[],
  approvals: Approval[],
): Stat[] {
  const pending = approvals.filter((a) => a.status === "pending").length;
  const autonomous = activityLog.filter((e) => e.initiated_by === "autonomous_watch").length;

  if (agentName === "shift_allocation_agent" && liveState.shift) {
    const shift = liveState.shift as { records: BurndownRecord[] };
    const atRisk = shift.records.filter((r) => r.risk_level !== "safe").length;
    return [
      { label: "Staff tracked", value: String(shift.records.length) },
      { label: "At risk", value: String(atRisk), tone: atRisk > 0 ? "var(--color-critical)" : undefined },
      { label: "Fleet-initiated checks", value: String(autonomous) },
      { label: "Pending approvals", value: String(pending) },
    ];
  }
  if (agentName === "inventory_management_agent" && liveState.inventory) {
    const inventory = liveState.inventory as {
      records: ParLevelRecord[];
      category_summary: Record<string, unknown>;
    };
    const flagged = inventory.records.filter((r) => r.stock_status !== "ok").length;
    const critical = inventory.records.filter((r) => r.stock_status === "critical").length;
    return [
      { label: "SKUs tracked", value: String(inventory.records.length) },
      { label: "Below reorder point", value: String(flagged), tone: flagged > 0 ? "var(--color-elevated)" : undefined },
      { label: "Critical", value: String(critical), tone: critical > 0 ? "var(--color-critical)" : undefined },
      { label: "Categories", value: String(Object.keys(inventory.category_summary ?? {}).length) },
    ];
  }
  if (agentName === "supply_chain_resiliency_agent" && liveState.supply) {
    const supply = liveState.supply as { decisions: ReorderDecision[] };
    const expedited = supply.decisions.filter((d) => d.urgency === "expedited").length;
    const atRisk = supply.decisions.filter((d) => d.will_stock_out_before_delivery).length;
    return [
      { label: "Open decisions", value: String(supply.decisions.length) },
      { label: "Expedited", value: String(expedited), tone: expedited > 0 ? "var(--color-critical)" : undefined },
      { label: "Will stock out first", value: String(atRisk), tone: atRisk > 0 ? "var(--color-critical)" : undefined },
      { label: "Pending approvals", value: String(pending) },
    ];
  }
  if (agentName === "hr_agent" && liveState.hr) {
    const hr = liveState.hr as { records: CredentialRecord[] };
    const nonCompliant = hr.records.filter((r) => r.credential_status !== "valid").length;
    const perDiem = hr.records.filter((r) => r.is_per_diem && r.credential_status === "valid").length;
    return [
      { label: "Staff tracked", value: String(hr.records.length) },
      { label: "Non-compliant", value: String(nonCompliant), tone: nonCompliant > 0 ? "var(--color-critical)" : undefined },
      { label: "Per-diem ready", value: String(perDiem) },
      { label: "Pending approvals", value: String(pending) },
    ];
  }
  if (agentName === "medical_representative_agent" && liveState.armor_events) {
    const events = liveState.armor_events as ArmorEvent[];
    const blocked = events.filter((e) => e.status === "blocked" && !e.service_error).length;
    const a2a = events.filter((e) => e.source === "cloud_run_a2a_mount").length;
    return [
      { label: "Screened", value: String(events.length) },
      { label: "Blocked", value: String(blocked), tone: blocked > 0 ? "var(--color-critical)" : undefined },
      { label: "Accepted", value: String(events.length - blocked) },
      { label: "Via A2A mount", value: String(a2a) },
    ];
  }
  if (agentName === "chaos_continuity_agent" && liveState.chaos_experiments) {
    const experiments = liveState.chaos_experiments as ChaosExperiment[];
    const types = new Set(experiments.map((e) => e.experiment_type)).size;
    const traced = experiments.filter((e) => e.trace_id).length;
    return [
      { label: "Experiments run", value: String(experiments.length) },
      { label: "Fault types covered", value: `${types} / 4` },
      { label: "With a trace", value: String(traced) },
      { label: "Replayed, not live", value: "always" },
    ];
  }
  if (agentName === "surgical_scheduling_agent" && liveState.surgical_schedule) {
    const schedule = liveState.surgical_schedule as {
      cases: SurgicalCase[];
      conflicts: SurgicalCaseConflict[];
    };
    const confirmed = schedule.cases.filter((c) => c.status === "confirmed").length;
    return [
      { label: "Cases scheduled", value: String(schedule.cases.length) },
      { label: "Confirmed", value: String(confirmed) },
      { label: "Conflicts", value: String(schedule.conflicts.length), tone: schedule.conflicts.length > 0 ? "var(--color-critical)" : undefined },
      { label: "Pending approvals", value: String(pending) },
    ];
  }
  if (agentName === "coordinator") {
    const routing = activityLog.filter((e) => e.activity_type === "routing_decision");
    const blocked = routing.filter((e) => e.status !== "allowed").length;
    const specialistsCalled = new Set(routing.map((e) => e.tool_name).filter(Boolean)).size;
    const specialistsTotal = Object.values(AGENT_META).filter((m) => m.kind === "specialist").length;
    return [
      { label: "Calls routed", value: String(routing.length) },
      { label: "Blocked by Gateway", value: String(blocked), tone: blocked > 0 ? "var(--color-critical)" : undefined },
      { label: "Specialists called", value: `${specialistsCalled} / ${specialistsTotal}` },
      { label: "Registry lookups", value: "every call" },
    ];
  }
  return [];
}

// Static, by-design facts about why this agent's one consequential action is (or isn't)
// approval-gated — not derived from live data, because the answer doesn't change call to call.
const APPROVAL_GATE_COPY: Record<string, { title: string; body: string }> = {
  shift_allocation_agent: {
    title: "notify_staff_reallocation",
    body: "Sends a shift-reassignment notice to one specific staff member. Composed by the model, but nothing is emailed until a manager approves it — same fail-closed default as every other consequential tool in the fleet.",
  },
  supply_chain_resiliency_agent: {
    title: "contact_vendor_for_reorder",
    body: "Emails a real vendor to place an order. Approval-gated with a 14-day link expiry; an expedited decision still waits for a human, it just gets flagged more urgently.",
  },
  hr_agent: {
    title: "notify_staff_credential_escalation",
    body: "Flags an expired or expiring credential to the staff member and to compliance. The detection is autonomous; the notification is not — it sits in the approvals queue until a manager acts.",
  },
  medical_representative_agent: {
    title: "send_vendor_reply",
    body: "Replies to a vendor's inbound message. The reply text is model-composed after Model Armor has already screened the inbound message once — approval is the second, independent check before anything leaves the building.",
  },
  surgical_scheduling_agent: {
    title: "notify_patient_of_status_change",
    body: "Emails a patient about a change to their case. Only sent if that patient has opted into email notifications — consent is checked before the approval gate even applies, so a decline never reaches a manager's inbox.",
  },
};
const NO_GATE_COPY: Record<string, string> = {
  inventory_management_agent:
    "Inventory only tracks stock and recommends reorder points — the tool that actually contacts a vendor belongs to Supply Chain Resiliency, so approval enforcement lives there instead.",
  chaos_continuity_agent:
    "Fault-injection results are captured once and replayed from Firestore rather than re-run live against production state, so there's no live consequential action here for a human to sign off on.",
  coordinator:
    "Coordinator only routes a call to the right specialist through the Agent Gateway — the specialist that actually performs a consequential action is the one whose approval policy governs it, not the router.",
};

function ApprovalGateInfo({ agentName }: { agentName: string }) {
  const gated = APPROVAL_GATE_COPY[agentName];
  const ungated = NO_GATE_COPY[agentName];
  if (gated) {
    return (
      <InfoCard icon={Info} title={`Approval gate — ${gated.title}`} accent="var(--color-elevated)">
        {gated.body}
      </InfoCard>
    );
  }
  if (ungated) {
    return (
      <InfoCard icon={Info} title="No approval-gated action">
        {ungated}
      </InfoCard>
    );
  }
  return null;
}

// The full list behind whichever LiveState panel only shows its top handful of flagged rows —
// same sortable/paginated shape as the audit log, scoped to this agent's own records.
function AgentRecordTable({
  agentName,
  liveState,
  activityLog,
}: {
  agentName: string;
  liveState: Record<string, unknown>;
  activityLog: ActivityLogEntry[];
}) {
  if (agentName === "shift_allocation_agent" && liveState.shift) {
    const shift = liveState.shift as { records: BurndownRecord[] };
    const columns: RecordColumn<BurndownRecord>[] = [
      { key: "name", label: "Name", render: (r) => r.name, sortValue: (r) => r.name },
      { key: "unit", label: "Unit", render: (r) => r.unit, sortValue: (r) => r.unit },
      { key: "hours", label: "Trailing hrs", render: (r) => r.trailing_hours, sortValue: (r) => r.trailing_hours, align: "right" },
      { key: "safe", label: "Safe hrs", render: (r) => r.safe_weekly_hours, sortValue: (r) => r.safe_weekly_hours, align: "right" },
      { key: "risk", label: "Risk", render: (r) => <StatusPill status={r.risk_level} /> },
    ];
    return (
      <Panel title="Full staff roster" subtitle={`${shift.records.length} staff members`}>
        <RecordTable columns={columns} rows={shift.records} rowKey={(r) => r.staff_id} />
      </Panel>
    );
  }
  if (agentName === "inventory_management_agent" && liveState.inventory) {
    const inventory = liveState.inventory as { records: ParLevelRecord[] };
    const columns: RecordColumn<ParLevelRecord>[] = [
      { key: "name", label: "Item", render: (r) => r.name, sortValue: (r) => r.name },
      { key: "sku", label: "SKU", render: (r) => <span className="font-mono">{r.sku}</span>, sortValue: (r) => r.sku },
      { key: "manufacturer", label: "Manufacturer", render: (r) => r.manufacturer ?? "—", sortValue: (r) => r.manufacturer ?? "" },
      { key: "category", label: "Category", render: (r) => r.category, sortValue: (r) => r.category },
      { key: "stock", label: "On hand", render: (r) => r.current_stock, sortValue: (r) => r.current_stock, align: "right" },
      { key: "days", label: "Days left", render: (r) => r.days_of_supply ?? "—", sortValue: (r) => r.days_of_supply ?? 9999, align: "right" },
      { key: "expiry", label: "Expires", render: (r) => r.expiration_date ?? "—", sortValue: (r) => r.expiration_date ?? "9999" },
      { key: "status", label: "Status", render: (r) => <StatusPill status={r.stock_status} /> },
      { key: "critical", label: "Critical", render: (r) => (r.is_critical_item ? "Yes" : "No") },
    ];
    return (
      <Panel title="Every tracked SKU" subtitle={`${inventory.records.length} items`}>
        <RecordTable columns={columns} rows={inventory.records} rowKey={(r) => r.sku} />
      </Panel>
    );
  }
  if (agentName === "supply_chain_resiliency_agent" && liveState.supply) {
    const supply = liveState.supply as { decisions: ReorderDecision[] };
    const columns: RecordColumn<ReorderDecision>[] = [
      { key: "name", label: "Item", render: (r) => r.name, sortValue: (r) => r.name },
      { key: "vendor", label: "Vendor", render: (r) => r.vendor_name ?? "—", sortValue: (r) => r.vendor_name ?? "" },
      { key: "qty", label: "Qty", render: (r) => r.reorder_quantity, sortValue: (r) => r.reorder_quantity, align: "right" },
      { key: "urgency", label: "Urgency", render: (r) => <StatusPill status={r.urgency === "expedited" ? "critical" : "elevated"} label={r.urgency} /> },
      { key: "risk", label: "Stockout risk", render: (r) => (r.will_stock_out_before_delivery ? "Yes" : "No") },
    ];
    return (
      <Panel title="Every reorder decision" subtitle={`${supply.decisions.length} decisions`}>
        <RecordTable columns={columns} rows={supply.decisions} rowKey={(r) => r.sku} />
      </Panel>
    );
  }
  if (agentName === "hr_agent" && liveState.hr) {
    const hr = liveState.hr as { records: CredentialRecord[] };
    const columns: RecordColumn<CredentialRecord>[] = [
      { key: "name", label: "Name", render: (r) => r.name, sortValue: (r) => r.name },
      { key: "unit", label: "Unit", render: (r) => r.unit, sortValue: (r) => r.unit },
      { key: "role", label: "Role", render: (r) => r.role, sortValue: (r) => r.role },
      { key: "status", label: "Status", render: (r) => <StatusPill status={r.credential_status} /> },
      { key: "expiry", label: "Days to expiry", render: (r) => r.days_until_expiry, sortValue: (r) => r.days_until_expiry, align: "right" },
    ];
    return (
      <Panel title="Full credential roster" subtitle={`${hr.records.length} staff members`}>
        <RecordTable columns={columns} rows={hr.records} rowKey={(r) => r.staff_id} />
      </Panel>
    );
  }
  if (agentName === "medical_representative_agent" && liveState.armor_events) {
    const events = liveState.armor_events as ArmorEvent[];
    const columns: RecordColumn<ArmorEvent>[] = [
      { key: "vendor", label: "Vendor", render: (r) => r.vendor_name, sortValue: (r) => r.vendor_name },
      { key: "status", label: "Result", render: (r) => <StatusPill status={r.service_error ? "elevated" : r.status} label={r.service_error ? "outage" : undefined} /> },
      { key: "filters", label: "Matched filters", render: (r) => (r.matched_filters.length > 0 ? r.matched_filters.join(", ") : "—") },
      { key: "source", label: "Source", render: (r) => (r.source === "cloud_run_a2a_mount" ? "A2A" : "standalone") },
      { key: "when", label: "When", render: (r) => new Date(r.timestamp).toLocaleString(), sortValue: (r) => r.timestamp },
    ];
    return (
      <Panel title="Every screened message" subtitle={`${events.length} messages`}>
        <RecordTable columns={columns} rows={events} rowKey={(r) => `${r.timestamp}-${r.vendor_name}`} />
      </Panel>
    );
  }
  if (agentName === "chaos_continuity_agent" && liveState.chaos_experiments) {
    const experiments = liveState.chaos_experiments as ChaosExperiment[];
    const columns: RecordColumn<ChaosExperiment>[] = [
      { key: "type", label: "Type", render: (r) => r.experiment_type.replace(/_/g, " "), sortValue: (r) => r.experiment_type },
      { key: "summary", label: "Summary", render: (r) => <span className="line-clamp-1">{r.summary}</span> },
      { key: "when", label: "When", render: (r) => new Date(r.timestamp).toLocaleString(), sortValue: (r) => r.timestamp },
      { key: "trace", label: "Trace", render: (r) => (r.trace_id ? <span className="font-mono">{r.trace_id.slice(0, 10)}…</span> : "—") },
    ];
    return (
      <Panel title="Every experiment run" subtitle={`${experiments.length} runs`}>
        <RecordTable columns={columns} rows={experiments} rowKey={(r) => `${r.timestamp}-${r.experiment_type}`} />
      </Panel>
    );
  }
  if (agentName === "surgical_scheduling_agent" && liveState.surgical_schedule) {
    const schedule = liveState.surgical_schedule as { cases: SurgicalCase[] };
    const columns: RecordColumn<SurgicalCase>[] = [
      { key: "case", label: "Case", render: (r) => <span className="font-mono">{r.case_id}</span>, sortValue: (r) => r.case_id },
      { key: "procedure", label: "Procedure", render: (r) => r.procedure_name, sortValue: (r) => r.procedure_name },
      { key: "room", label: "Room", render: (r) => r.operating_room, sortValue: (r) => r.operating_room },
      { key: "status", label: "Status", render: (r) => <StatusPill status={r.status} /> },
      { key: "start", label: "Starts", render: (r) => new Date(r.scheduled_start).toLocaleString(), sortValue: (r) => r.scheduled_start },
    ];
    return (
      <Panel title="Every scheduled case" subtitle={`${schedule.cases.length} cases`}>
        <RecordTable columns={columns} rows={schedule.cases} rowKey={(r) => r.case_id} />
      </Panel>
    );
  }
  if (agentName === "coordinator") {
    const routing = activityLog.filter((e) => e.activity_type === "routing_decision");
    const columns: RecordColumn<ActivityLogEntry>[] = [
      { key: "when", label: "When", render: (r) => new Date(r.timestamp).toLocaleString(), sortValue: (r) => r.timestamp },
      { key: "target", label: "Target", render: (r) => agentMetaFor(r.tool_name ?? "").label || r.tool_name, sortValue: (r) => r.tool_name ?? "" },
      { key: "decision", label: "Decision", render: (r) => <StatusPill status={r.status ?? "allowed"} /> },
      { key: "reason", label: "Reason", render: (r) => <span className="line-clamp-1">{r.summary}</span> },
    ];
    return (
      <Panel title="Every routing decision" subtitle={`${routing.length} calls`}>
        <RecordTable columns={columns} rows={routing} rowKey={(r) => r.id} />
      </Panel>
    );
  }
  return null;
}

export default function AgentDetailPage() {
  const params = useParams<{ agentName: string }>();
  const agentName = decodeURIComponent(params.agentName);
  const { data, error, isLoading, refresh } = useAgentDetail(agentName);
  const [selectedTrace, setSelectedTrace] = useState<{ id: string; timestamp: string } | null>(
    null,
  );

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
  const accent = accentFor(agentName);
  const subjectLabel = MEMORY_SUBJECT_LABEL[agentName];
  const memorySubjects = subjectLabel ? memorySubjectsFor(agentName, data.live_state) : [];
  const stats = agentStats(agentName, data.live_state, data.activity_log, data.approvals);
  const insight = AgentInsight({ agentName, liveState: data.live_state, activityLog: data.activity_log });
  const recordTable = AgentRecordTable({ agentName, liveState: data.live_state, activityLog: data.activity_log });
  const gateInfo = ApprovalGateInfo({ agentName });

  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8 flex items-center gap-4">
        <span
          className="flex size-11 shrink-0 items-center justify-center rounded-lg"
          style={{ backgroundColor: `${accent}1a`, color: accent }}
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
        {stats.length > 0 && <StatStrip stats={stats} />}

        {subjectLabel && (
          <section className="max-w-2xl">
            <AgentMemoryPanel agentName={agentName} subjectLabel={subjectLabel} subjects={memorySubjects} />
          </section>
        )}

        <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <MiniActivityList entries={data.activity_log} />
          {insight}
        </section>

        <section>
          <h2 className="mb-3 text-[11px] font-medium tracking-[0.2em] text-[var(--color-ink-muted)] uppercase">
            Current responsibilities
          </h2>
          <LiveState agentName={agentName} liveState={data.live_state} />
        </section>

        {recordTable && <section>{recordTable}</section>}

        <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <ActivityFeed
            entries={data.activity_log}
            onSelectTrace={(id, timestamp) => setSelectedTrace({ id, timestamp })}
          />
          <ApprovalsFeed approvals={data.approvals} onResolved={() => refresh()} />
        </section>

        <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {gateInfo}
          <AgentPolicyEditor taskType={data.policy?.task_type ?? null} />
        </section>

        <details className="group rounded-2xl border border-[var(--color-border-soft)] open:border-[var(--color-border)]">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-5 py-4 text-sm font-medium text-[var(--color-ink-secondary)] hover:text-[var(--color-ink-primary)]">
            <span>System health (technical detail)</span>
            <span className="text-xs text-[var(--color-ink-muted)] group-open:hidden">Show</span>
            <span className="hidden text-xs text-[var(--color-ink-muted)] group-open:inline">Hide</span>
          </summary>
          <div className="px-5 pb-5">
            <AgentLogViewer agentName={agentName} />
            <AgentIdentityPanel
              agent={data.agent}
              memoryScope={meta.memoryScope}
              serviceAccount={meta.serviceAccount}
            />
          </div>
        </details>
      </div>

      {selectedTrace && (
        <TraceViewer
          traceId={selectedTrace.id}
          timestamp={selectedTrace.timestamp}
          onClose={() => setSelectedTrace(null)}
        />
      )}
    </main>
  );
}
