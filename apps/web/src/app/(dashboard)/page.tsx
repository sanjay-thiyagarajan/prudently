"use client";

import { motion } from "framer-motion";
import { Loader2, TriangleAlert } from "lucide-react";

import { Header } from "@/components/layout/Header";
import { FleetOverview } from "@/components/workspace/FleetOverview";
import { useDashboardOverview } from "@/lib/api/dashboard";

function SectionLabel({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="mb-5">
      <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
        {eyebrow}
      </p>
      <h2 className="mt-1 font-[family-name:var(--font-display)] text-xl font-semibold text-[var(--color-ink-primary)]">
        {title}
      </h2>
    </div>
  );
}

export default function FleetPage() {
  const { data, error, isLoading } = useDashboardOverview();

  if (isLoading) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3">
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={28} />
        <p className="text-sm text-[var(--color-ink-secondary)]">
          Connecting to the deployed fleet…
        </p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
        <TriangleAlert className="text-[var(--color-critical)]" size={28} />
        <p className="text-sm text-[var(--color-ink-secondary)]">
          Couldn&apos;t reach the Prudently API. Check that the backend is
          running and NEXT_PUBLIC_API_BASE_URL is set correctly.
        </p>
      </main>
    );
  }

  const activeAgents = data.fleet.filter((a) => a.status === "active").length;
  const criticalAlerts =
    data.shift.records.filter((r) => r.risk_level === "critical").length +
    data.inventory.records.filter((r) => r.stock_status === "critical").length +
    data.hr.records.filter((r) => r.credential_status === "expired").length;

  return (
    <main className="min-h-screen pb-20">
      <Header
        asOf={data.as_of}
        activeAgents={activeAgents}
        totalAgents={data.fleet.length}
        criticalAlerts={criticalAlerts}
        isLive
      />

      <div className="mx-auto max-w-7xl space-y-14 px-6 py-12 sm:px-10">
        <motion.section
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
        >
          <SectionLabel eyebrow="The heroes" title="Live agent fleet" />
          <p className="-mt-3 mb-6 text-sm text-[var(--color-ink-secondary)]">
            Click any agent to see its activities, approvals, pending
            responsibilities, and permissions.
          </p>
          <FleetOverview fleet={data.fleet} />
        </motion.section>
      </div>
    </main>
  );
}
