export type RiskLevel = "safe" | "elevated" | "critical";
export type StockStatus = "ok" | "low" | "critical";
export type CredentialStatus = "valid" | "expiring_soon" | "expired";
export type AgentStatus = "active" | "planned" | "retired";

export interface FleetAgent {
  agent_name: string;
  role: string;
  status: AgentStatus;
  reasoning_engine_id: string | null;
  firestore_collections: string[];
}

export interface BurndownRecord {
  staff_id: string;
  name: string;
  unit: string;
  trailing_hours: number;
  safe_weekly_hours: number;
  burndown_ratio: number;
  risk_level: RiskLevel;
  recommendation: string | null;
}

export interface ParLevelRecord {
  sku: string;
  name: string;
  category: string;
  unit: string;
  current_stock: number;
  reorder_point: number;
  baseline_daily_consumption: number;
  days_of_supply: number | null;
  stock_status: StockStatus;
  primary_vendor_id: string | null;
  recommendation: string | null;
}

export interface ReorderDecision {
  sku: string;
  name: string;
  category: string;
  stock_status: StockStatus;
  days_of_supply: number | null;
  reorder_quantity: number;
  vendor_id: string | null;
  vendor_name: string | null;
  vendor_lead_time_days: number | null;
  vendor_reliability: number | null;
  urgency: "routine" | "expedited";
  will_stock_out_before_delivery: boolean;
  alternate_vendor_id: string | null;
  alternate_vendor_name: string | null;
  recommendation: string;
}

export interface CredentialRecord {
  staff_id: string;
  name: string;
  role: string;
  unit: string;
  is_per_diem: boolean;
  credential_expiry: string;
  days_until_expiry: number;
  credential_status: CredentialStatus;
}

export interface ArmorEvent {
  vendor_name: string;
  message: string;
  status: "blocked" | "accepted";
  matched_filters: string[];
  reason: string | null;
  service_error: boolean;
  source: "standalone_reasoning_engine" | "cloud_run_a2a_mount";
  trace_id: string | null;
  timestamp: string;
}

export interface Approval {
  task_type: string;
  status: "pending" | "approved" | "rejected";
  recipient_label: string;
  subject: string;
  requested_by: string;
  timestamp: string;
}

export interface ApprovalPolicy {
  task_type: string;
  requires_approval: boolean;
  approver_email: string | null;
  notify_emails: string[];
  notify_on_complete: boolean;
}

export interface AdmissionsDay {
  sim_day: number;
  calendar_date: string;
  unit: string;
  admissions: number;
}

export interface UnitAdmissionsTotal {
  unit: string;
  total_admissions: number;
}

export interface GuestDoctorHours {
  staff_id: string;
  name: string;
  unit: string;
  role: string;
  hours: number;
}

export interface PayrollStaffOption {
  staff_id: string;
  name: string;
  unit: string;
  role: string;
  hourly_rate: number;
}

export interface PayrollRecord {
  id: string;
  staff_id: string;
  staff_name: string;
  unit: string;
  role: string;
  pay_period_start: string;
  pay_period_end: string;
  hours_worked: number;
  hourly_rate: number;
  gross_pay: number;
  status: "pending" | "paid";
  timestamp: string;
  paid_at: string | null;
  run_id?: string | null;
}

export interface PayrollRun {
  id: string;
  period_start: string;
  period_end: string;
  status: "draft" | "approved" | "disbursed";
  staff_count: number;
  total_gross_pay: number;
  unit_subtotals: Record<string, number>;
  created_at: string;
  approved_at?: string | null;
  disbursed_at?: string | null;
  records?: PayrollRecord[];
}

export interface StaffDirectoryEntry {
  staff_id: string;
  name: string;
  role: string;
  unit: string;
  is_per_diem: boolean;
  credential_status: CredentialStatus | null;
}

export interface StaffProfile {
  staff_id: string;
  name: string;
  role: string;
  unit: string;
  is_per_diem: boolean;
  hourly_rate: number;
  fatigue: BurndownRecord | null;
  credential: CredentialRecord | null;
  pay_history: PayrollRecord[];
}

export interface Vendor {
  vendor_id: string;
  name: string;
  lead_time_days: number;
  reliability: number;
}

export interface InventoryTransaction {
  id: string;
  sku: string;
  item_name: string;
  type: "consumption" | "receipt";
  quantity_delta: number;
  stock_before: number;
  stock_after: number;
  source: string;
  timestamp: string;
}

export interface PurchaseOrder {
  id: string;
  sku: string;
  item_name: string;
  quantity: number;
  vendor_id: string;
  vendor_name: string;
  unit_cost: number;
  total_cost: number;
  status: "ordered" | "received" | "invoiced";
  ordered_at: string;
  received_at: string | null;
  invoiced_at: string | null;
  source_approval_token?: string | null;
}

export interface ChaosExperiment {
  experiment_type:
    | "hospital_whatif"
    | "fleet_kill_agent"
    | "fleet_memory_poisoning"
    | "fleet_latency_injection";
  summary: string;
  result: Record<string, unknown>;
  trace_id: string | null;
  timestamp: string;
}

export interface ActivityLogEntry {
  id: string;
  agent_name: string;
  activity_type:
    | "action_requested"
    | "action_sent"
    | "action_resolved"
    | "routing_decision"
    | "screening"
    | "chaos_experiment"
    | "autonomous_action";
  tool_name: string | null;
  summary: string;
  status: string | null;
  trace_id: string | null;
  /** "autonomous_watch" when the fleet started this itself; "manager" when a human asked. */
  initiated_by?: "manager" | "autonomous_watch";
  timestamp: string;
}

/**
 * One thing the fleet noticed on a real-time watch cycle and acted on with nobody in the
 * room — see apps/api/services/fleet_watch.py + services/autonomy.py. `response` is the
 * agent's own account of what it did; `status` is "failed" when the turn timed out or errored,
 * which is surfaced rather than hidden so the feed never overstates what the fleet accomplished.
 */
export interface AutonomousAction {
  id: string;
  trigger_kind: "stock_breach" | "fatigue_breach" | "credential_breach";
  subject: string;
  agent_name: string;
  severity: string;
  summary: string;
  prompt: string;
  response: string;
  status: "completed" | "failed";
  tool_calls: number;
  context: Record<string, unknown>;
  trace_id: string | null;
  timestamp: string;
  /** Present when the API withheld the agent's own free text from an anonymous caller. */
  _redacted?: { fields: string[]; reason: string };
}

/** apps/api/routes/watch.py's GET /watch/status — the real-time fleet watch's own state, not
 * a scripted timeline. `last_checked_at`/`next_check_at` are null until the background loop
 * (services/watch_loop.py) has run at least once. */
export interface WatchStatus {
  last_checked_at: string | null;
  next_check_at: string | null;
  interval_seconds: number;
  checks_run: number;
  triggers_fired_total: number;
}

export interface AgentDetail {
  agent: FleetAgent;
  activity_log: ActivityLogEntry[];
  approvals: Approval[];
  policy: ApprovalPolicy | null;
  live_state: Record<string, unknown>;
}

export interface TraceSpan {
  span_id: string;
  parent_span_id: string | null;
  name: string;
  start_time: string | null;
  end_time: string | null;
  labels: Record<string, string>;
}

export interface TraceData {
  trace_id: string;
  spans: TraceSpan[];
}

export interface AgentLogEntry {
  timestamp: string | null;
  severity: string | null;
  text: string;
}

export interface AgentLogsData {
  agent_name: string;
  logs: AgentLogEntry[];
}

export interface DashboardOverview {
  as_of: string;
  fleet: FleetAgent[];
  shift: {
    records: BurndownRecord[];
    unit_summary: Record<string, Record<RiskLevel, number>>;
  };
  inventory: {
    records: ParLevelRecord[];
    category_summary: Record<string, Record<StockStatus, number>>;
  };
  supply: {
    decisions: ReorderDecision[];
    vendor_summary: Record<string, { order_count: number; total_quantity: number }>;
  };
  hr: {
    records: CredentialRecord[];
    unit_summary: Record<string, Record<CredentialStatus, number>>;
  };
  admissions: {
    trend: AdmissionsDay[];
    unit_totals: UnitAdmissionsTotal[];
  };
  guest_doctor_hours: GuestDoctorHours[];
  armor_events: ArmorEvent[];
  chaos_experiments: ChaosExperiment[];
  autonomous_actions: AutonomousAction[];
  approvals: Approval[];
  /** Set by the API when the caller was anonymous and staff-level rows were withheld. */
  _public_view?: boolean;
}
