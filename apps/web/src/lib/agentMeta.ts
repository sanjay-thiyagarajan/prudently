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

export interface AgentMeta {
  label: string;
  icon: LucideIcon;
  blurb: string;
  accent: string;
}

// Single source of truth for per-agent display metadata — shared by FleetOverview's cards,
// the sidebar's agent quick-links, and the agent detail page's header, so a new agent only
// needs an entry here once.
export const AGENT_META: Record<string, AgentMeta> = {
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

export function agentMetaFor(agentName: string): AgentMeta {
  return (
    AGENT_META[agentName] ?? {
      label: agentName,
      icon: Network,
      blurb: "",
      accent: "var(--color-hero)",
    }
  );
}
