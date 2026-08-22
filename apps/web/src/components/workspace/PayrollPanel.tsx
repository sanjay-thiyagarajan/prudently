"use client";

import { CheckCircle2, Loader2, Wallet } from "lucide-react";
import { useState } from "react";

import { Panel } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/contexts/AuthContext";
import { createPayrollRecord, markPayrollPaid, usePayrollRecords, usePayrollStaff } from "@/lib/api/payroll";

function defaultPeriod(): { start: string; end: string } {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 13);
  const toISO = (d: Date) => d.toISOString().slice(0, 10);
  return { start: toISO(start), end: toISO(end) };
}

export function PayrollPanel() {
  const { idToken } = useAuth();
  const { staff, isLoading: staffLoading } = usePayrollStaff();
  const { records, isLoading: recordsLoading, refresh } = usePayrollRecords();

  const initialPeriod = defaultPeriod();
  const [staffId, setStaffId] = useState("");
  const [periodStart, setPeriodStart] = useState(initialPeriod.start);
  const [periodEnd, setPeriodEnd] = useState(initialPeriod.end);
  const [creating, setCreating] = useState(false);
  const [markingPaidId, setMarkingPaidId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleCreate() {
    if (!idToken || !staffId) return;
    setCreating(true);
    setFormError(null);
    try {
      const result = await createPayrollRecord(idToken, {
        staff_id: staffId,
        pay_period_start: periodStart,
        pay_period_end: periodEnd,
      });
      if ("error" in result) {
        setFormError(String((result as unknown as { error: string }).error));
      } else {
        await refresh();
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create payroll record.");
    } finally {
      setCreating(false);
    }
  }

  async function handleMarkPaid(recordId: string) {
    if (!idToken) return;
    setMarkingPaidId(recordId);
    try {
      await markPayrollPaid(idToken, recordId);
      await refresh();
    } finally {
      setMarkingPaidId(null);
    }
  }

  return (
    <Panel title="Payroll" icon={Wallet} accent="#facc15">
      <div className="space-y-2.5 rounded-xl border border-[var(--color-border-soft)] p-3.5">
        <p className="text-xs font-medium text-[var(--color-ink-secondary)]">
          Create a pay-period record
        </p>
        <select
          value={staffId}
          onChange={(e) => setStaffId(e.target.value)}
          disabled={staffLoading}
          className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
        >
          <option value="">Select staff…</option>
          {staff.map((member) => (
            <option key={member.staff_id} value={member.staff_id}>
              {member.name} · {member.unit} · ${member.hourly_rate}/hr
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <input
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
            className="w-1/2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
          />
          <input
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
            className="w-1/2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
          />
        </div>
        {formError && <p className="text-xs text-[var(--color-critical)]">{formError}</p>}
        <button
          type="button"
          onClick={handleCreate}
          disabled={creating || !staffId}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-[var(--color-hero-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--color-hero)] transition-opacity disabled:opacity-50"
        >
          {creating ? <Loader2 size={12} className="animate-spin" /> : null}
          Create record
        </button>
      </div>

      <div className="mt-4 border-t border-[var(--color-border-soft)] pt-4">
        {recordsLoading ? (
          <p className="text-sm text-[var(--color-ink-muted)]">Loading records…</p>
        ) : records.length === 0 ? (
          <p className="text-sm text-[var(--color-ink-muted)]">No payroll records yet.</p>
        ) : (
          <ul className="space-y-2.5">
            {records.map((record) => (
              <li
                key={record.id}
                className="rounded-xl border border-[var(--color-border-soft)] p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-sm font-medium text-[var(--color-ink-primary)]">
                    {record.staff_name}
                  </p>
                  <StatusPill status={record.status} />
                </div>
                <p className="mt-1 text-xs text-[var(--color-ink-secondary)]">
                  {record.pay_period_start} → {record.pay_period_end} · {record.hours_worked}h @
                  ${record.hourly_rate}/hr
                </p>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-sm font-semibold text-[var(--color-ink-primary)]">
                    ${record.gross_pay.toFixed(2)}
                  </span>
                  {record.status === "pending" && (
                    <button
                      type="button"
                      onClick={() => handleMarkPaid(record.id)}
                      disabled={markingPaidId === record.id}
                      className="flex items-center gap-1 text-xs font-semibold text-[var(--color-safe)] disabled:opacity-50"
                    >
                      {markingPaidId === record.id ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <CheckCircle2 size={12} />
                      )}
                      Mark paid
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Panel>
  );
}
