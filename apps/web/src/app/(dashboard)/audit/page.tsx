"use client";

import { Loader2, RefreshCw, ScrollText, TriangleAlert } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import { AuditTable } from "@/components/workspace/AuditTable";
import { useAuditLog } from "@/lib/api/audit";

export default function AuditPage() {
  const { entries, error, isLoading, refresh } = useAuditLog();

  return (
    <main className="mx-auto min-h-screen max-w-[1180px] px-6 py-10 sm:px-8">
      <header className="mb-7 flex items-start justify-between gap-4">
        <div>
          <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.16em] text-[var(--color-ink-muted)] uppercase">
            Governance
          </p>
          <h1 className="mt-1 font-[family-name:var(--font-display)] text-[26px] font-semibold tracking-tight text-[var(--color-ink-primary)]">
            Audit log
          </h1>
          <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-[var(--color-ink-secondary)]">
            Every approval request, Gateway routing decision, Model Armor screening call, chaos
            experiment, and autonomous action the fleet has recorded — one unredacted table, not
            split per agent. Filter, sort, drill into one entry for its full detail, or export
            the filtered set for a compliance review.
          </p>
        </div>
        <button
          type="button"
          onClick={() => refresh()}
          className="mt-1 inline-flex shrink-0 items-center gap-1.5 rounded-md border border-[var(--color-border)] px-3 py-1.5 text-xs font-medium text-[var(--color-ink-secondary)] transition-colors hover:border-[var(--color-hero)] hover:text-[var(--color-hero)]"
        >
          <RefreshCw size={12} />
          Refresh
        </button>
      </header>

      {isLoading ? (
        <div className="flex min-h-[240px] items-center justify-center">
          <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
        </div>
      ) : error ? (
        <div className="flex min-h-[240px] flex-col items-center justify-center gap-3 text-center">
          <TriangleAlert className="text-[var(--color-critical)]" size={24} />
          <p className="text-[13px] text-[var(--color-ink-secondary)]">
            Sign in to review the audit log — it carries unredacted detail, so it isn&apos;t on
            the public overview.
          </p>
        </div>
      ) : (
        <Panel title="All recorded activity" icon={ScrollText} accent="var(--color-ink-secondary)">
          <AuditTable entries={entries} />
        </Panel>
      )}
    </main>
  );
}
