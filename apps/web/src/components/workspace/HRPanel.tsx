"use client";

import { ShieldCheck } from "lucide-react";

import { DistributionBar } from "@/components/ui/DistributionBar";
import { Panel } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import type { CredentialRecord, CredentialStatus } from "@/lib/types/dashboard";

const CREDENTIAL_ORDER: CredentialStatus[] = ["expired", "expiring_soon", "valid"];

export function HRPanel({
  records,
  unitSummary,
}: {
  records: CredentialRecord[];
  unitSummary: Record<string, Record<CredentialStatus, number>>;
}) {
  const flagged = records.filter((r) => r.credential_status !== "valid").slice(0, 6);
  const perDiemEligible = records.filter((r) => r.is_per_diem && r.credential_status === "valid");

  return (
    <Panel title="HR" icon={ShieldCheck} accent="#38bdf8" live>
      <div className="space-y-3">
        {Object.entries(unitSummary).map(([unit, counts]) => (
          <DistributionBar key={unit} label={unit} counts={counts} order={CREDENTIAL_ORDER} />
        ))}
      </div>

      <div className="mt-5 flex items-center justify-between rounded-xl bg-[var(--color-border-soft)] px-3.5 py-2.5 text-xs">
        <span className="text-[var(--color-ink-secondary)]">Per-diem pool ready to activate</span>
        <span className="font-semibold text-[var(--color-ink-primary)]">
          {perDiemEligible.length}
        </span>
      </div>

      <div className="mt-4 border-t border-[var(--color-border-soft)] pt-4">
        {flagged.length === 0 ? (
          <p className="text-sm text-[var(--color-ink-muted)]">
            No credential compliance issues.
          </p>
        ) : (
          <ul className="space-y-2.5">
            {flagged.map((record) => (
              <li
                key={record.staff_id}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-[var(--color-ink-primary)]">
                    {record.name}{" "}
                    <span className="text-[var(--color-ink-muted)]">· {record.unit}</span>
                  </p>
                  <p className="truncate text-xs text-[var(--color-ink-secondary)]">
                    {record.days_until_expiry < 0
                      ? `Expired ${Math.abs(record.days_until_expiry)}d ago`
                      : `Expires in ${record.days_until_expiry}d`}
                  </p>
                </div>
                <StatusPill status={record.credential_status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </Panel>
  );
}
