"use client";

import { SurgicalSchedulePanel } from "@/components/workspace/SurgicalSchedulePanel";

export default function SurgicalSchedulePage() {
  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
          Operating room schedule
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Surgical Scheduling
        </h1>
        <p className="mt-2 max-w-lg text-sm text-[var(--color-ink-secondary)]">
          Every active case, OR/surgeon double-bookings the fleet has flagged, and — for admin and
          clinician roles — the patient behind each case. Notifying a patient requires manager
          approval by default and respects their email consent.
        </p>
      </div>
      <div className="max-w-4xl">
        <SurgicalSchedulePanel />
      </div>
    </main>
  );
}
