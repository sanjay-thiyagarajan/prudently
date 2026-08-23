"use client";

import { Loader2, TriangleAlert } from "lucide-react";

import { AdmissionsPanel } from "@/components/workspace/AdmissionsPanel";
import { GuestDoctorHoursPanel } from "@/components/workspace/GuestDoctorHoursPanel";
import { useDashboardOverview } from "@/lib/api/dashboard";

export default function AdmissionsPage() {
  const { data, error, isLoading } = useDashboardOverview();

  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
          Ward census
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Admissions & coverage
        </h1>
      </div>

      {isLoading ? (
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
      ) : error || !data ? (
        <div className="flex items-center gap-2 text-sm text-[var(--color-ink-secondary)]">
          <TriangleAlert className="text-[var(--color-critical)]" size={18} />
          Couldn&apos;t reach the Prudently API.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <AdmissionsPanel
            trend={data.admissions.trend}
            unitTotals={data.admissions.unit_totals}
          />
          <GuestDoctorHoursPanel hours={data.guest_doctor_hours} />
        </div>
      )}
    </main>
  );
}
