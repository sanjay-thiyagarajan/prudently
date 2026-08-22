"use client";

import { motion } from "framer-motion";
import { Loader2, TriangleAlert } from "lucide-react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Header } from "@/components/layout/Header";
import { AdmissionsPanel } from "@/components/workspace/AdmissionsPanel";
import { ApprovalsFeed } from "@/components/workspace/ApprovalsFeed";
import { ArmorFeed } from "@/components/workspace/ArmorFeed";
import { ChaosReplay } from "@/components/workspace/ChaosReplay";
import { FleetOverview } from "@/components/workspace/FleetOverview";
import { GuestDoctorHoursPanel } from "@/components/workspace/GuestDoctorHoursPanel";
import { HRPanel } from "@/components/workspace/HRPanel";
import { InventoryPanel } from "@/components/workspace/InventoryPanel";
import { PayrollPanel } from "@/components/workspace/PayrollPanel";
import { PolicyEditor } from "@/components/workspace/PolicyEditor";
import { ShiftPanel } from "@/components/workspace/ShiftPanel";
import { SupplyPanel } from "@/components/workspace/SupplyPanel";
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

export default function Home() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}

function Dashboard() {
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
          Couldn&apos;t reach the Prudently API. Check that the backend is running and
          NEXT_PUBLIC_API_BASE_URL is set correctly.
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
          <FleetOverview fleet={data.fleet} />
        </motion.section>

        <section>
          <SectionLabel eyebrow="Operations" title="Staffing & supply" />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <ShiftPanel records={data.shift.records} unitSummary={data.shift.unit_summary} />
            <InventoryPanel
              records={data.inventory.records}
              categorySummary={data.inventory.category_summary}
            />
            <SupplyPanel decisions={data.supply.decisions} />
            <HRPanel records={data.hr.records} unitSummary={data.hr.unit_summary} />
          </div>
        </section>

        <section>
          <SectionLabel eyebrow="Security & resilience" title="Model Armor & Chaos experiments" />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <ArmorFeed events={data.armor_events} />
            <ChaosReplay experiments={data.chaos_experiments} />
          </div>
        </section>

        <section>
          <SectionLabel
            eyebrow="Manager in the loop"
            title="Approvals & notification policy"
          />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <ApprovalsFeed approvals={data.approvals} />
            <PolicyEditor />
          </div>
        </section>

        <section>
          <SectionLabel eyebrow="Enterprise command center" title="Admissions, coverage & payroll" />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            <AdmissionsPanel trend={data.admissions.trend} unitTotals={data.admissions.unit_totals} />
            <GuestDoctorHoursPanel hours={data.guest_doctor_hours} />
            <PayrollPanel />
          </div>
        </section>
      </div>
    </main>
  );
}
