import {
  CalendarClock,
  Handshake,
  Network,
  Package,
  Scissors,
  ShieldCheck,
  Truck,
  Zap,
  type LucideIcon,
} from "lucide-react";

/**
 * How an agent sits in the topology, which is the only thing that changes how it is drawn.
 *
 * Agents deliberately do NOT get individual accent colours any more. The previous version
 * gave each one its own hue, and three of those hues were the triage green/amber/red that
 * every status pill on the site uses to mean safe/elevated/critical — so the Shift agent's
 * card was green for no reason while a green pill next to it meant something specific. Colour
 * here now carries exactly one message: where the agent sits relative to the trust boundary.
 */
export type AgentKind = "hub" | "specialist" | "external";

export interface AgentMeta {
  label: string;
  icon: LucideIcon;
  blurb: string;
  kind: AgentKind;
  /** What this agent remembers between sessions, and how that memory is partitioned. */
  memoryScope: string | null;
  /** Whether the fleet watch can wake this agent up with nobody in the room. */
  autonomous: boolean;
  /** The dedicated IAM service account this Reasoning Engine runs as — not a shared platform
   * identity. Set via .agent_engine_config.json, confirmed live via effective_identity; see
   * docs/threat-model.md's git history / AGENTS.md's Agent Identity entries for how this was
   * verified. Project-qualified so it's copy-pasteable straight into the Cloud Console. */
  serviceAccount: string;
}

const SA_DOMAIN = "prudently-hackathon.iam.gserviceaccount.com";
const GCP_PROJECT = "prudently-hackathon";
const GCP_REGION = "us-central1";

/** Cloud Console deep link for a Reasoning Engine — same URL `adk deploy` itself prints. */
export function reasoningEngineConsoleUrl(engineId: string): string {
  return `https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/${GCP_REGION}/agent-engines/${engineId}?project=${GCP_PROJECT}`;
}

export const AGENT_ACCENT: Record<AgentKind, string> = {
  hub: "var(--color-hero)",
  specialist: "var(--color-ink-secondary)",
  external: "var(--color-a2a)",
};

// Single source of truth for per-agent display metadata — shared by the fleet topology, the
// sidebar, and the agent detail page header, so a new agent needs one entry here.
export const AGENT_META: Record<string, AgentMeta> = {
  coordinator: {
    label: "Coordinator",
    icon: Network,
    blurb: "The only way in — routes every call through the Agent Gateway",
    kind: "hub",
    memoryScope: null,
    autonomous: false,
    serviceAccount: `coordinator-agent-sa@${SA_DOMAIN}`,
  },
  shift_allocation_agent: {
    label: "Shift Allocation",
    icon: CalendarClock,
    blurb: "Fatigue and overtime burndown, reallocation recommendations",
    kind: "specialist",
    memoryScope: "per unit",
    autonomous: true,
    serviceAccount: `shift-agent-sa@${SA_DOMAIN}`,
  },
  inventory_management_agent: {
    label: "Inventory",
    icon: Package,
    blurb: "Stock and par-level tracking against reorder points",
    kind: "specialist",
    memoryScope: "per SKU",
    autonomous: false,
    serviceAccount: `inventory-agent-sa@${SA_DOMAIN}`,
  },
  supply_chain_resiliency_agent: {
    label: "Supply Chain",
    icon: Truck,
    blurb: "Reorder quantities, vendor selection, stockout risk",
    kind: "specialist",
    memoryScope: "per SKU",
    autonomous: true,
    serviceAccount: `supply-agent-sa@${SA_DOMAIN}`,
  },
  hr_agent: {
    label: "HR",
    icon: ShieldCheck,
    blurb: "Credentialing, and where Shift escalates when cover runs out",
    kind: "specialist",
    memoryScope: "per unit",
    autonomous: true,
    serviceAccount: `hr-agent-sa@${SA_DOMAIN}`,
  },
  chaos_continuity_agent: {
    label: "Chaos & Continuity",
    icon: Zap,
    blurb: "Ward what-if projections and fault injection against the fleet",
    kind: "specialist",
    memoryScope: "one shared store — fault-injection tests only",
    autonomous: false,
    serviceAccount: `chaos-agent-sa@${SA_DOMAIN}`,
  },
  medical_representative_agent: {
    label: "Medical Representative",
    icon: Handshake,
    blurb: "Screens inbound vendor mail before any of it reaches a model",
    kind: "external",
    memoryScope: null,
    autonomous: false,
    serviceAccount: `medrep-agent-sa@${SA_DOMAIN}`,
  },
  surgical_scheduling_agent: {
    label: "Surgical Scheduling",
    icon: Scissors,
    blurb: "OR/surgeon double-booking detection, patient status notifications",
    kind: "specialist",
    memoryScope: "per conflict",
    autonomous: true,
    serviceAccount: `surgical-scheduling-agent-sa@${SA_DOMAIN}`,
  },
};

export function agentMetaFor(agentName: string): AgentMeta {
  return (
    AGENT_META[agentName] ?? {
      label: agentName,
      icon: Network,
      blurb: "",
      kind: "specialist",
      memoryScope: null,
      autonomous: false,
      serviceAccount: "",
    }
  );
}

export function accentFor(agentName: string): string {
  return AGENT_ACCENT[agentMetaFor(agentName).kind];
}
