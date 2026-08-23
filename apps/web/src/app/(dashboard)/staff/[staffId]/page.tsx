"use client";

import { CalendarClock, Loader2, ShieldCheck, TriangleAlert, UserRound, Wallet } from "lucide-react";
import { useParams } from "next/navigation";

import { StatusPill } from "@/components/ui/StatusPill";
import { useStaffProfile } from "@/lib/api/staff";

export default function StaffProfilePage() {
  const params = useParams<{ staffId: string }>();
  const staffId = decodeURIComponent(params.staffId);
  const { profile, isLoading, error } = useStaffProfile(staffId);

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
      </main>
    );
  }

  if (error || !profile) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
        <TriangleAlert className="text-[var(--color-critical)]" size={28} />
        <p className="text-sm text-[var(--color-ink-secondary)]">
          Couldn&apos;t find staff member &quot;{staffId}&quot;.
        </p>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8 flex items-center gap-4">
        <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-[var(--color-hero-soft)] text-[var(--color-hero)]">
          <UserRound size={22} strokeWidth={2} />
        </span>
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
              {profile.name}
            </h1>
            {profile.is_per_diem && (
              <span className="rounded-full bg-[var(--color-a2a-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase text-[var(--color-a2a)]">
                Per-diem
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-[var(--color-ink-secondary)]">
            {profile.role} · {profile.unit}
          </p>
        </div>
      </div>

      <div className="grid max-w-4xl grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/80 p-5">
          <div className="mb-3 flex items-center gap-2.5">
            <CalendarClock size={16} className="text-[var(--color-safe)]" />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-primary)]">
              Fatigue
            </h2>
          </div>
          {profile.fatigue ? (
            <>
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm text-[var(--color-ink-secondary)]">
                  {profile.fatigue.trailing_hours}h in the last 7 days
                </span>
                <StatusPill status={profile.fatigue.risk_level} />
              </div>
              {profile.fatigue.recommendation && (
                <p className="text-xs text-[var(--color-ink-secondary)]">
                  {profile.fatigue.recommendation}
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-[var(--color-ink-muted)]">No fatigue data available.</p>
          )}
        </div>

        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/80 p-5">
          <div className="mb-3 flex items-center gap-2.5">
            <ShieldCheck size={16} className="text-[#38bdf8]" />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-primary)]">
              Credential
            </h2>
          </div>
          {profile.credential ? (
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--color-ink-secondary)]">
                Expires {profile.credential.credential_expiry}
              </span>
              <StatusPill status={profile.credential.credential_status} />
            </div>
          ) : (
            <p className="text-sm text-[var(--color-ink-muted)]">No credential data available.</p>
          )}
        </div>

        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/80 p-5 lg:col-span-2">
          <div className="mb-3 flex items-center gap-2.5">
            <Wallet size={16} className="text-[#facc15]" />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-primary)]">
              Pay history
            </h2>
          </div>
          {profile.pay_history.length === 0 ? (
            <p className="text-sm text-[var(--color-ink-muted)]">No pay records yet.</p>
          ) : (
            <ul className="space-y-2">
              {profile.pay_history.map((record) => (
                <li
                  key={record.id}
                  className="flex items-center justify-between rounded-xl border border-[var(--color-border-soft)] p-3 text-sm"
                >
                  <span className="text-[var(--color-ink-secondary)]">
                    {record.pay_period_start} → {record.pay_period_end} · {record.hours_worked}h
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[var(--color-ink-primary)]">
                      ${record.gross_pay.toFixed(2)}
                    </span>
                    <StatusPill status={record.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </main>
  );
}
