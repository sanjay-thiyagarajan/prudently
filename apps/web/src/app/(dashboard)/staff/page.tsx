"use client";

import { Loader2, Search, TriangleAlert, UserRound } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { StatusPill } from "@/components/ui/StatusPill";
import { useStaffDirectory } from "@/lib/api/staff";

const UNIT_ALL = "all";

export default function StaffDirectoryPage() {
  const { staff, isLoading, error } = useStaffDirectory();
  const [search, setSearch] = useState("");
  const [unit, setUnit] = useState(UNIT_ALL);

  const units = useMemo(() => Array.from(new Set(staff.map((s) => s.unit))).sort(), [staff]);

  const filtered = useMemo(() => {
    return staff.filter((member) => {
      if (unit !== UNIT_ALL && member.unit !== unit) return false;
      if (search && !member.name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [staff, unit, search]);

  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
          Shift Allocation & HR Agents
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Staff Directory
        </h1>
        <p className="mt-2 max-w-lg text-sm text-[var(--color-ink-secondary)]">
          Every staff member on the roster, including the per-diem pool. Click anyone to see
          their fatigue trend, credential status, and pay history.
        </p>
      </div>

      {isLoading ? (
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
      ) : error ? (
        <div className="flex items-center gap-2 text-sm text-[var(--color-ink-secondary)]">
          <TriangleAlert className="text-[var(--color-critical)]" size={18} />
          Couldn&apos;t reach the Prudently API.
        </div>
      ) : (
        <div className="max-w-4xl space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5">
              <Search size={14} className="text-[var(--color-ink-muted)]" />
              <input
                type="text"
                placeholder="Search staff…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-transparent text-xs text-[var(--color-ink-primary)] outline-none placeholder:text-[var(--color-ink-muted)]"
              />
            </div>
            <select
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none"
            >
              <option value={UNIT_ALL}>All units</option>
              {units.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </select>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-panel)]">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border-soft)] text-[11px] uppercase tracking-wide text-[var(--color-ink-muted)]">
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Role</th>
                  <th className="px-4 py-3 font-medium">Unit</th>
                  <th className="px-4 py-3 font-medium">Credential</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((member) => (
                  <tr
                    key={member.staff_id}
                    className="border-t border-[var(--color-border-soft)] transition-colors hover:bg-[var(--color-border-soft)]"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/staff/${encodeURIComponent(member.staff_id)}`}
                        className="flex items-center gap-2.5 font-medium text-[var(--color-ink-primary)] hover:text-[var(--color-hero)]"
                      >
                        <UserRound size={14} className="text-[var(--color-ink-muted)]" />
                        {member.name}
                        {member.is_per_diem && (
                          <span className="rounded-full bg-[var(--color-a2a-soft)] px-1.5 py-0.5 text-[10px] font-semibold uppercase text-[var(--color-a2a)]">
                            Per-diem
                          </span>
                        )}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-[var(--color-ink-secondary)]">{member.role}</td>
                    <td className="px-4 py-3 text-[var(--color-ink-secondary)]">{member.unit}</td>
                    <td className="px-4 py-3">
                      {member.credential_status && <StatusPill status={member.credential_status} />}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-center text-sm text-[var(--color-ink-muted)]">
                      No staff match this search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
}
