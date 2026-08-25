"use client";

import { Loader2, TriangleAlert } from "lucide-react";

import { ApprovalsFeed } from "@/components/workspace/ApprovalsFeed";
import { useDashboardOverview } from "@/lib/api/dashboard";

export default function ApprovalsPage() {
  const { data, error, isLoading, refresh } = useDashboardOverview();

  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
          Manager in the loop
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Approvals
        </h1>
        <p className="mt-2 max-w-md text-sm text-[var(--color-ink-secondary)]">
          Fleet-wide pending, approved, and rejected requests. Each agent&apos;s
          own permissions live on its detail page.
        </p>
      </div>

      {isLoading ? (
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
      ) : error || !data ? (
        <div className="flex items-center gap-2 text-sm text-[var(--color-ink-secondary)]">
          <TriangleAlert className="text-[var(--color-critical)]" size={18} />
          Couldn&apos;t reach the Prudently API.
        </div>
      ) : (
        <div className="max-w-xl">
          <ApprovalsFeed approvals={data.approvals} onResolved={() => refresh()} />
        </div>
      )}
    </main>
  );
}
