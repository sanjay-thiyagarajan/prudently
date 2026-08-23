"use client";

import { Loader2, Lock, Radio, TriangleAlert } from "lucide-react";

import { BoardStrip } from "@/components/layout/BoardStrip";
import { Panel } from "@/components/ui/Panel";
import { AutonomousFeed } from "@/components/workspace/AutonomousFeed";
import { FleetOverview } from "@/components/workspace/FleetOverview";
import { HRPanel } from "@/components/workspace/HRPanel";
import { InventoryPanel } from "@/components/workspace/InventoryPanel";
import { ShiftPanel } from "@/components/workspace/ShiftPanel";
import { SupplyPanel } from "@/components/workspace/SupplyPanel";
import { useDashboardOverview } from "@/lib/api/dashboard";
import { hrSummary, inventorySummary, shiftSummary, supplySummary } from "@/lib/labels";

function Section({
  eyebrow,
  title,
  lede,
  children,
}: {
  eyebrow: string;
  title: string;
  lede?: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-4">
        <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.16em] text-[var(--color-ink-muted)] uppercase">
          {eyebrow}
        </p>
        <h2 className="mt-1 font-[family-name:var(--font-display)] text-[19px] font-semibold tracking-tight text-[var(--color-ink-primary)]">
          {title}
        </h2>
        {lede && (
          <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-[var(--color-ink-secondary)]">
            {lede}
          </p>
        )}
      </div>
      {children}
    </section>
  );
}

function sumCounts<K extends string>(
  byGroup: Record<string, Record<K, number>>,
  keys: K[],
): Record<K, number> {
  const totals = Object.fromEntries(keys.map((key) => [key, 0])) as Record<K, number>;
  for (const counts of Object.values(byGroup ?? {})) {
    for (const key of keys) {
      totals[key] += counts[key] ?? 0;
    }
  }
  return totals;
}

function Reading({ text }: { text: string }) {
  return (
    <p className="rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-surface)] p-3 text-[12px] leading-relaxed text-[var(--color-ink-secondary)]">
      {text}
    </p>
  );
}

export default function FleetPage() {
  const { data, error, isLoading, isPublicView } = useDashboardOverview();

  if (isLoading) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3">
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
        <p className="text-[13px] text-[var(--color-ink-secondary)]">Reading the ward board…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
        <TriangleAlert className="text-[var(--color-critical)]" size={24} />
        <p className="max-w-md text-[13px] leading-relaxed text-[var(--color-ink-secondary)]">
          Couldn&apos;t reach the Prudently API. Check that the backend is running and that
          NEXT_PUBLIC_API_BASE_URL points at it.
        </p>
      </main>
    );
  }

  const activeAgents = data.fleet.filter((a) => a.status === "active").length;
  // Counted from the aggregates, not the record lists: the lists are withheld from anonymous
  // callers, so counting them showed a reassuring "0 critical signals" directly above panels
  // full of red. The aggregates are identical in both postures.
  const criticalAlerts =
    sumCounts(data.shift.unit_summary, ["critical"]).critical +
    sumCounts(data.inventory.category_summary, ["critical"]).critical +
    sumCounts(data.hr.unit_summary, ["expired"]).expired;
  const autonomous = data.autonomous_actions ?? [];

  return (
    <main className="min-h-screen pb-16">
      <BoardStrip
        activeAgents={activeAgents}
        totalAgents={data.fleet.length}
        criticalAlerts={criticalAlerts}
        autonomousToday={autonomous.length}
      />

      <div className="mx-auto max-w-[1240px] space-y-12 px-6 py-9 sm:px-8">
        {isPublicView && (
          <div className="flex items-start gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-sunk)] p-3.5">
            <Lock size={15} className="mt-0.5 shrink-0 text-[var(--color-ink-muted)]" />
            <p className="text-[12px] leading-relaxed text-[var(--color-ink-secondary)]">
              <strong className="font-semibold text-[var(--color-ink-primary)]">
                Public view.
              </strong>{" "}
              Unit and category totals are shown, but individual staff fatigue and
              credentialing records are withheld. Sign in as a manager to see them.
            </p>
          </div>
        )}

        <Section
          eyebrow="Topology"
          title="The fleet"
          lede="Seven agents, one way in, and one trust boundary that is a real network hop rather than a diagram convention. Open any agent to see what it has done and what it is allowed to do."
        >
          <FleetOverview fleet={data.fleet} />
        </Section>

        <Section
          eyebrow="Unprompted"
          title="What the fleet did on its own"
          lede="Nobody asked for any of this. The fleet watch runs continuously, comparing the ward to how it left it, and wakes the responsible agent the moment something crosses a line. Consequential actions still route to you for approval."
        >
          <Panel title="Autonomous activity" icon={Radio} accent="var(--color-autonomous)" live>
            <AutonomousFeed actions={autonomous} limit={4} />
          </Panel>
        </Section>

        <Section
          eyebrow="Right now"
          title="Today's operations"
          lede="The state of the ward, and which agent is responsible for each part of it."
        >
          <div className="mb-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
            <Reading
              text={shiftSummary(
                sumCounts(data.shift.unit_summary, ["safe", "elevated", "critical"]),
              )}
            />
            <Reading
              text={inventorySummary(
                sumCounts(data.inventory.category_summary, ["ok", "low", "critical"]),
              )}
            />
            <Reading text={supplySummary(data.supply.decisions.length)} />
            <Reading
              text={hrSummary(
                sumCounts(data.hr.unit_summary, ["valid", "expiring_soon", "expired"]),
              )}
            />
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ShiftPanel records={data.shift.records} unitSummary={data.shift.unit_summary} />
            <InventoryPanel
              records={data.inventory.records}
              categorySummary={data.inventory.category_summary}
            />
            <SupplyPanel decisions={data.supply.decisions} />
            <HRPanel records={data.hr.records} unitSummary={data.hr.unit_summary} />
          </div>
        </Section>
      </div>
    </main>
  );
}
