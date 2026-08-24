// Manager-friendly copy for the raw vocabulary the backend writes (activity_type values,
// gateway/approval/payroll/inventory status strings). Same "raw key -> human string, fall
// back to the raw value" shape as PolicyEditor.tsx's TASK_LABEL and agentMeta.ts's
// AGENT_META — one more shared lookup module rather than scattering ad hoc maps per
// component. Raw values are never deleted from the data, just relabeled here; a detail view
// can always show the original string alongside the friendly one.

export const ACTIVITY_TYPE_LABEL: Record<string, string> = {
  action_requested: "Asked the manager to approve an action",
  action_sent: "Took action",
  action_resolved: "Manager decision recorded",
  routing_decision: "Routed the request to a specialist",
  screening: "Screened a message for safety",
  chaos_experiment: "Ran a resilience drill",
};

export function activityTypeLabel(activityType: string): string {
  return ACTIVITY_TYPE_LABEL[activityType] ?? activityType.replace(/_/g, " ");
}

// Covers every status string this app writes: approvals, Gateway routing decisions, Model
// Armor screening, payroll records/runs, purchase orders. StatusPill already maps most of
// these to a color; this adds the label text StatusPill falls back to only when none is
// passed explicitly. Kept short (StatusPill is a small chip, not a sentence) — the "why", if
// there is one, already lives in the surrounding row's own summary/reason text, e.g.
// ActivityFeed's entry.summary carries the Gateway's actual reason string.
export const STATUS_LABEL: Record<string, string> = {
  // approvals
  pending: "Awaiting approval",
  pending_approval: "Awaiting approval",
  approved: "Approved",
  rejected: "Declined",
  sent: "Sent",
  already_decided: "Already decided",
  // Gateway routing decisions
  allowed: "Allowed",
  blocked_unregistered: "Blocked",
  blocked_inactive: "Blocked",
  blocked_unauthorized: "Blocked",
  blocked_armor: "Blocked",
  // Model Armor screening
  blocked: "Blocked",
  accepted: "Passed screening",
  // payroll
  paid: "Paid",
  draft: "Draft",
  disbursed: "Disbursed",
  // purchase orders
  ordered: "Ordered",
  received: "Received",
  invoiced: "Invoiced",
  // surgical cases
  scheduled: "Scheduled",
  confirmed: "Confirmed",
  delayed: "Delayed",
  in_progress: "In progress",
  cancelled: "Cancelled",
  consent_declined: "Consent declined",
  // job sheets
  open: "Open",
};

export function statusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status.replace(/_/g, " ");
}

// One-line "what's happening right now, in plain language" summaries for the Operations home
// screen — keyed by the same live_state slices routes/dashboard.py's build_overview() and
// routes/agents.py's _AGENT_LIVE_STATE_KEYS already use, so a summary always has real counts
// behind it rather than being a static caption.
export function shiftSummary(counts: { safe: number; elevated: number; critical: number }): string {
  const atRisk = counts.elevated + counts.critical;
  if (atRisk === 0) return "Every shift is within a safe hours range.";
  return `${atRisk} staff ${atRisk === 1 ? "is" : "are"} approaching or over a safe hours limit — the Shift Allocation Assistant is proposing reassignments.`;
}

export function inventorySummary(counts: { ok: number; low: number; critical: number }): string {
  const atRisk = counts.low + counts.critical;
  if (atRisk === 0) return "Supplies are stocked above their reorder points.";
  return `${atRisk} ${atRisk === 1 ? "item is" : "items are"} running low — the Inventory Assistant is tracking them for reorder.`;
}

export function supplySummary(decisionCount: number): string {
  if (decisionCount === 0) return "No reorders are pending right now.";
  return `${decisionCount} reorder ${decisionCount === 1 ? "decision is" : "decisions are"} ready — the Supply Chain Assistant has picked vendors and quantities.`;
}

export function hrSummary(counts: { valid: number; expiring_soon: number; expired: number }): string {
  const atRisk = counts.expiring_soon + counts.expired;
  if (atRisk === 0) return "Every staff credential is current.";
  return `${atRisk} staff credential${atRisk === 1 ? " needs" : "s need"} attention — the HR Assistant is tracking expirations and coverage.`;
}
