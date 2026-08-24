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
  },
  shift_allocation_agent: {
    label: "Shift Allocation",
    icon: CalendarClock,
    blurb: "Fatigue and overtime burndown, reallocation recommendations",
    kind: "specialist",
    memoryScope: "per unit",
    autonomous: true,
  },
  inventory_management_agent: {
    label: "Inventory",
    icon: Package,
    blurb: "Stock and par-level tracking against reorder points",
    kind: "specialist",
    memoryScope: "per SKU",
    autonomous: false,
  },
  supply_chain_resiliency_agent: {
    label: "Supply Chain",
    icon: Truck,
    blurb: "Reorder quantities, vendor selection, stockout risk",
    kind: "specialist",
    memoryScope: "per vendor",
    autonomous: true,
  },
  hr_agent: {
    label: "HR",
    icon: ShieldCheck,
    blurb: "Credentialing, and where Shift escalates when cover runs out",
    kind: "specialist",
    memoryScope: "per unit",
    autonomous: true,
  },
  chaos_continuity_agent: {
    label: "Chaos & Continuity",
    icon: Zap,
    blurb: "Ward what-if projections and fault injection against the fleet",
    kind: "specialist",
    memoryScope: "per scenario",
    autonomous: false,
  },
  medical_representative_agent: {
    label: "Medical Representative",
    icon: Handshake,
    blurb: "Screens inbound vendor mail before any of it reaches a model",
    kind: "external",
    memoryScope: null,
    autonomous: false,
  },
  surgical_scheduling_agent: {
    label: "Surgical Scheduling",
    icon: Scissors,
    blurb: "OR/surgeon double-booking detection, patient status notifications",
    kind: "specialist",
    memoryScope: null,
    autonomous: true,
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
    }
  );
}

export function accentFor(agentName: string): string {
  return AGENT_ACCENT[agentMetaFor(agentName).kind];
}
