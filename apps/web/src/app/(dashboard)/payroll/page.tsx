"use client";

import { PayrollPanel } from "@/components/workspace/PayrollPanel";

export default function PayrollPage() {
  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
          Enterprise command center
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Payroll
        </h1>
      </div>
      <div className="max-w-xl">
        <PayrollPanel />
      </div>
    </main>
  );
}
