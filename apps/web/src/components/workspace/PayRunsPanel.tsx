"use client";

import { CheckCircle2, ClipboardCheck, Loader2, Wallet } from "lucide-react";
import { useMemo, useState } from "react";

import { Panel } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/contexts/AuthContext";
import {
  approvePayrollRun,
  createPayrollRun,
  disbursePayrollRun,
  usePayrollRecords,
  usePayrollRun,
  usePayrollRuns,
} from "@/lib/api/payroll";
import type { PayrollRecord } from "@/lib/types/dashboard";

function defaultPeriod(): { start: string; end: string } {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 13);
  const toISO = (d: Date) => d.toISOString().slice(0, 10);
  return { start: toISO(start), end: toISO(end) };
}

const money = (value: number) =>
  value.toLocaleString(undefined, { style: "currency", currency: "USD" });

function ytdByStaffId(records: PayrollRecord[], excludeRunId: string | undefined): Record<string, number> {
  const currentYear = new Date().getFullYear();
  const totals: Record<string, number> = {};
  for (const record of records) {
    if (excludeRunId && record.run_id === excludeRunId) continue;
    if (new Date(record.pay_period_start).getFullYear() !== currentYear) continue;
    totals[record.staff_id] = (totals[record.staff_id] ?? 0) + record.gross_pay;
  }
  return totals;
}

function RegisterRowGroup({
  record,
  previousUnit,
  unitSubtotal,
  ytdBeforeThisRun,
}: {
  record: PayrollRecord;
  previousUnit: string | null;
  unitSubtotal: number;
  ytdBeforeThisRun: number;
}) {
  return (
    <>
      {record.unit !== previousUnit && (
        <tr className="bg-[var(--color-border-soft)]/40">
          <td colSpan={4} className="px-3 py-1.5 font-medium text-[var(--color-ink-secondary)]">
            {record.unit}
          </td>
          <td className="px-3 py-1.5 text-right font-medium text-[var(--color-ink-secondary)]">
            {money(unitSubtotal)}
          </td>
          <td className="px-3 py-1.5" />
        </tr>
      )}
      <tr className="border-t border-[var(--color-border-soft)]">
        <td className="px-3 py-2 text-[var(--color-ink-primary)]">{record.staff_name}</td>
        <td className="px-3 py-2 text-[var(--color-ink-secondary)]">{record.role}</td>
        <td className="px-3 py-2 text-right text-[var(--color-ink-secondary)]">
          {record.hours_worked}
        </td>
        <td className="px-3 py-2 text-right text-[var(--color-ink-secondary)]">
          {money(record.hourly_rate)}
        </td>
        <td className="px-3 py-2 text-right font-medium text-[var(--color-ink-primary)]">
          {money(record.gross_pay)}
        </td>
        <td className="px-3 py-2 text-right text-[var(--color-ink-muted)]">
          {money(ytdBeforeThisRun + record.gross_pay)}
        </td>
      </tr>
    </>
  );
}

function RunDetail({ runId, onChanged }: { runId: string; onChanged: () => void }) {
  const { idToken } = useAuth();
  const { run, isLoading, refresh } = usePayrollRun(runId);
  const { records: allRecords } = usePayrollRecords();
  const [busy, setBusy] = useState(false);

  const ytd = useMemo(() => ytdByStaffId(allRecords, runId), [allRecords, runId]);

  if (isLoading || !run) {
    return <Loader2 className="animate-spin text-[var(--color-hero)]" size={20} />;
  }

  async function handleApprove() {
    if (!idToken) return;
    setBusy(true);
    try {
      await approvePayrollRun(idToken, runId);
      await refresh();
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function handleDisburse() {
    if (!idToken) return;
    setBusy(true);
    try {
      await disbursePayrollRun(idToken, runId);
      await refresh();
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  const rows = run.records ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[var(--color-ink-primary)]">
            {run.period_start} → {run.period_end}
          </p>
          <p className="text-xs text-[var(--color-ink-secondary)]">
            {run.staff_count} staff · {money(run.total_gross_pay)} total
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill status={run.status} />
          {run.status === "draft" && (
            <button
              type="button"
              onClick={handleApprove}
              disabled={busy}
              className="flex items-center gap-1.5 rounded-lg bg-[var(--color-hero-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--color-hero)] disabled:opacity-50"
            >
              {busy ? <Loader2 size={12} className="animate-spin" /> : <ClipboardCheck size={12} />}
              Approve run
            </button>
          )}
          {run.status === "approved" && (
            <button
              type="button"
              onClick={handleDisburse}
              disabled={busy}
              className="flex items-center gap-1.5 rounded-lg bg-[var(--color-safe-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--color-safe)] disabled:opacity-50"
            >
              {busy ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
              Disburse
            </button>
          )}
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-[var(--color-border-soft)]">
        <table className="w-full min-w-[640px] text-left text-xs">
          <thead>
            <tr className="border-b border-[var(--color-border-soft)] text-[var(--color-ink-muted)] uppercase tracking-wide">
              <th className="px-3 py-2 font-medium">Staff</th>
              <th className="px-3 py-2 font-medium">Unit</th>
              <th className="px-3 py-2 font-medium text-right">Hours</th>
              <th className="px-3 py-2 font-medium text-right">Rate</th>
              <th className="px-3 py-2 font-medium text-right">Gross pay</th>
              <th className="px-3 py-2 font-medium text-right">YTD</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((record, index) => (
              <RegisterRowGroup
                key={record.id}
                record={record}
                previousUnit={index === 0 ? null : rows[index - 1].unit}
                unitSubtotal={run.unit_subtotals[record.unit] ?? 0}
                ytdBeforeThisRun={ytd[record.staff_id] ?? 0}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function PayRunsPanel() {
  const { idToken } = useAuth();
  const { runs, isLoading: runsLoading, refresh: refreshRuns } = usePayrollRuns();
  const initial = defaultPeriod();
  const [periodStart, setPeriodStart] = useState(initial.start);
  const [periodEnd, setPeriodEnd] = useState(initial.end);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleCreateRun() {
    if (!idToken) return;
    setCreating(true);
    setFormError(null);
    try {
      const run = await createPayrollRun(idToken, {
        period_start: periodStart,
        period_end: periodEnd,
      });
      await refreshRuns();
      setSelectedRunId(run.id);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to compute pay run.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <Panel title="Payroll — Pay Runs" icon={Wallet} accent="#facc15" live>
      <div className="space-y-4">
        <div className="flex flex-wrap items-end gap-2 rounded-xl border border-[var(--color-border-soft)] p-3.5">
          <div>
            <p className="mb-1 text-xs font-medium text-[var(--color-ink-secondary)]">Period start</p>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
            />
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-[var(--color-ink-secondary)]">Period end</p>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
            />
          </div>
          <button
            type="button"
            onClick={handleCreateRun}
            disabled={creating}
            className="flex items-center gap-1.5 rounded-lg bg-[var(--color-hero-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--color-hero)] disabled:opacity-50"
          >
            {creating ? <Loader2 size={12} className="animate-spin" /> : null}
            Compute pay run
          </button>
          {formError && <p className="w-full text-xs text-[var(--color-critical)]">{formError}</p>}
        </div>

        {selectedRunId && <RunDetail runId={selectedRunId} onChanged={refreshRuns} />}

        <div className="border-t border-[var(--color-border-soft)] pt-4">
          <p className="mb-2 text-xs font-medium text-[var(--color-ink-secondary)]">Past pay runs</p>
          {runsLoading ? (
            <Loader2 className="animate-spin text-[var(--color-hero)]" size={16} />
          ) : runs.length === 0 ? (
            <p className="text-sm text-[var(--color-ink-muted)]">No pay runs yet.</p>
          ) : (
            <ul className="space-y-2">
              {runs.map((run) => (
                <li key={run.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedRunId(run.id)}
                    className={`flex w-full items-center justify-between rounded-xl border p-3 text-left text-sm transition-colors ${
                      selectedRunId === run.id
                        ? "border-[var(--color-hero)] bg-[var(--color-hero-soft)]"
                        : "border-[var(--color-border-soft)] hover:bg-[var(--color-border-soft)]"
                    }`}
                  >
                    <span className="text-[var(--color-ink-primary)]">
                      {run.period_start} → {run.period_end} · {run.staff_count} staff
                    </span>
                    <span className="flex items-center gap-2">
                      <span className="font-medium text-[var(--color-ink-secondary)]">
                        {money(run.total_gross_pay)}
                      </span>
                      <StatusPill status={run.status} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Panel>
  );
}
