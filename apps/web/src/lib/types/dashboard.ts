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
  armor_events: ArmorEvent[];
  chaos_experiments: ChaosExperiment[];
  approvals: Approval[];
}
