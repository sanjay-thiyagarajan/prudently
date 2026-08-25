"use client";

import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search, Waypoints, X } from "lucide-react";
import { useMemo, useState } from "react";

import { StatusPill } from "@/components/ui/StatusPill";
import { activityTypeLabel } from "@/lib/labels";
import { agentMetaFor } from "@/lib/agentMeta";
import type { ActivityLogEntry } from "@/lib/types/dashboard";

type SortKey = "timestamp" | "agent_name" | "activity_type" | "status";
type SortDir = "asc" | "desc";

const PAGE_SIZE = 25;

function toCsvValue(value: string | null | undefined): string {
  const s = value ?? "";
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function downloadCsv(rows: ActivityLogEntry[]) {
  const header = ["Timestamp", "Agent", "Type", "Tool/Target", "Status", "Initiated by", "Summary", "Trace ID"];
  const lines = rows.map((r) =>
    [
      r.timestamp,
      agentMetaFor(r.agent_name).label,
      activityTypeLabel(r.activity_type),
      r.tool_name ?? "",
      r.status ?? "",
      r.initiated_by ?? "manager",
      r.summary,
      r.trace_id ?? "",
    ]
      .map(toCsvValue)
      .join(","),
  );
  const csv = [header.join(","), ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `prudently-audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function relativeTime(iso: string): string {
  const deltaMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(deltaMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function SortHeader({
  label,
  sortKey,
  active,
  dir,
  onClick,
  className = "",
}: {
  label: string;
  sortKey: SortKey;
  active: boolean;
  dir: SortDir;
  onClick: (key: SortKey) => void;
  className?: string;
}) {
  const Icon = !active ? ArrowUpDown : dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <th className={`px-3 py-2 text-left font-medium ${className}`}>
      <button
        type="button"
        onClick={() => onClick(sortKey)}
        className={`inline-flex items-center gap-1 transition-colors hover:text-[var(--color-ink-primary)] ${active ? "text-[var(--color-ink-primary)]" : "text-[var(--color-ink-muted)]"}`}
      >
        {label}
        <Icon size={11} />
      </button>
    </th>
  );
}

/** A fully client-side drilldown: filters, sort, pagination, and CSV export all operate over
 * one bounded pull from GET /audit/log (services/state.py's `activity_log` — the single
 * collection every approval, Gateway routing decision, screening decision, and chaos
 * experiment already writes to, see routes/audit.py). Export always exports the *filtered*
 * set, not just the visible page — a manager exporting "everything HR did this week" should
 * get exactly that, not 25 rows. */
export function AuditTable({ entries }: { entries: ActivityLogEntry[] }) {
  const [search, setSearch] = useState("");
  const [agentFilter, setAgentFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [initiatedFilter, setInitiatedFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<ActivityLogEntry | null>(null);

  const agents = useMemo(
    () => Array.from(new Set(entries.map((e) => e.agent_name))).sort(),
    [entries],
  );
  const types = useMemo(
    () => Array.from(new Set(entries.map((e) => e.activity_type))).sort(),
    [entries],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return entries.filter((e) => {
      if (agentFilter !== "all" && e.agent_name !== agentFilter) return false;
      if (typeFilter !== "all" && e.activity_type !== typeFilter) return false;
      if (initiatedFilter !== "all" && (e.initiated_by ?? "manager") !== initiatedFilter) return false;
      if (!q) return true;
      return (
        e.summary.toLowerCase().includes(q) ||
        (e.tool_name ?? "").toLowerCase().includes(q) ||
        (e.status ?? "").toLowerCase().includes(q) ||
        agentMetaFor(e.agent_name).label.toLowerCase().includes(q)
      );
    });
  }, [entries, search, agentFilter, typeFilter, initiatedFilter]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "timestamp") cmp = a.timestamp.localeCompare(b.timestamp);
      else if (sortKey === "agent_name")
        cmp = agentMetaFor(a.agent_name).label.localeCompare(agentMetaFor(b.agent_name).label);
      else if (sortKey === "activity_type") cmp = a.activity_type.localeCompare(b.activity_type);
      else if (sortKey === "status") cmp = (a.status ?? "").localeCompare(b.status ?? "");
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [filtered, sortKey, sortDir]);

  const pageCount = Math.max(Math.ceil(sorted.length / PAGE_SIZE), 1);
  const clampedPage = Math.min(page, pageCount - 1);
  const pageRows = sorted.slice(clampedPage * PAGE_SIZE, clampedPage * PAGE_SIZE + PAGE_SIZE);

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "timestamp" ? "desc" : "asc");
    }
    setPage(0);
  }

  function updateFilter(setter: (v: string) => void) {
    return (v: string) => {
      setter(v);
      setPage(0);
    };
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[200px] flex-1">
          <Search size={13} className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-[var(--color-ink-muted)]" />
          <input
            type="text"
            value={search}
            onChange={(e) => updateFilter(setSearch)(e.target.value)}
            placeholder="Search summary, tool, status…"
            className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] py-1.5 pr-2.5 pl-7 text-xs text-[var(--color-ink-primary)] outline-none placeholder:text-[var(--color-ink-muted)] focus:border-[var(--color-hero)]"
          />
        </div>
        <select
          value={agentFilter}
          onChange={(e) => updateFilter(setAgentFilter)(e.target.value)}
          className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none"
        >
          <option value="all">Every agent</option>
          {agents.map((a) => (
            <option key={a} value={a}>
              {agentMetaFor(a).label}
            </option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => updateFilter(setTypeFilter)(e.target.value)}
          className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none"
        >
          <option value="all">Every type</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {activityTypeLabel(t)}
            </option>
          ))}
        </select>
        <select
          value={initiatedFilter}
          onChange={(e) => updateFilter(setInitiatedFilter)(e.target.value)}
          className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none"
        >
          <option value="all">Manager + autonomous</option>
          <option value="manager">Manager-initiated</option>
          <option value="autonomous_watch">Fleet-initiated</option>
        </select>
        <button
          type="button"
          onClick={() => downloadCsv(sorted)}
          disabled={sorted.length === 0}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-[var(--color-border)] px-2.5 py-1.5 text-xs font-medium text-[var(--color-ink-secondary)] transition-colors hover:border-[var(--color-hero)] hover:text-[var(--color-hero)] disabled:opacity-40"
        >
          <Download size={12} />
          Export {sorted.length} rows
        </button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
        <table className="w-full min-w-[880px] border-collapse text-xs">
          <thead>
            <tr className="border-b border-[var(--color-border)] bg-[var(--color-sunk)]">
              <SortHeader label="When" sortKey="timestamp" active={sortKey === "timestamp"} dir={sortDir} onClick={handleSort} className="w-28" />
              <SortHeader label="Agent" sortKey="agent_name" active={sortKey === "agent_name"} dir={sortDir} onClick={handleSort} className="w-36" />
              <SortHeader label="Type" sortKey="activity_type" active={sortKey === "activity_type"} dir={sortDir} onClick={handleSort} className="w-44" />
              <th className="px-3 py-2 text-left font-medium text-[var(--color-ink-muted)]">Summary</th>
              <SortHeader label="Status" sortKey="status" active={sortKey === "status"} dir={sortDir} onClick={handleSort} className="w-32" />
              <th className="w-20 px-3 py-2 text-left font-medium text-[var(--color-ink-muted)]">Initiated</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-[var(--color-ink-muted)]">
                  No entries match these filters.
                </td>
              </tr>
            ) : (
              pageRows.map((entry) => (
                <tr
                  key={entry.id}
                  onClick={() => setSelected(entry)}
                  className="cursor-pointer border-b border-[var(--color-border-soft)] last:border-0 hover:bg-[var(--color-surface-hover)]"
                >
                  <td className="px-3 py-2 whitespace-nowrap text-[var(--color-ink-muted)]" title={entry.timestamp}>
                    {relativeTime(entry.timestamp)}
                  </td>
                  <td className="px-3 py-2 font-medium text-[var(--color-ink-primary)]">
                    {agentMetaFor(entry.agent_name).label}
                  </td>
                  <td className="px-3 py-2 text-[var(--color-ink-secondary)]">{activityTypeLabel(entry.activity_type)}</td>
                  <td className="max-w-[360px] truncate px-3 py-2 text-[var(--color-ink-secondary)]" title={entry.summary}>
                    {entry.summary}
                  </td>
                  <td className="px-3 py-2">{entry.status && <StatusPill status={entry.status} />}</td>
                  <td className="px-3 py-2">
                    <span
                      className="rounded px-1.5 py-0.5 text-[10px]"
                      style={{
                        backgroundColor:
                          entry.initiated_by === "autonomous_watch" ? "var(--color-autonomous-soft)" : "var(--color-border-soft)",
                        color: entry.initiated_by === "autonomous_watch" ? "var(--color-autonomous)" : "var(--color-ink-muted)",
                      }}
                    >
                      {entry.initiated_by === "autonomous_watch" ? "fleet" : "manager"}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-[var(--color-ink-muted)]">
        <span>
          {sorted.length === 0
            ? "0 entries"
            : `${clampedPage * PAGE_SIZE + 1}–${Math.min((clampedPage + 1) * PAGE_SIZE, sorted.length)} of ${sorted.length}`}
        </span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            disabled={clampedPage === 0}
            onClick={() => setPage((p) => p - 1)}
            className="rounded-md border border-[var(--color-border)] px-2.5 py-1 disabled:opacity-30"
          >
            Prev
          </button>
          <span>
            {clampedPage + 1} / {pageCount}
          </span>
          <button
            type="button"
            disabled={clampedPage >= pageCount - 1}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-md border border-[var(--color-border)] px-2.5 py-1 disabled:opacity-30"
          >
            Next
          </button>
        </div>
      </div>

      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="w-full max-w-lg rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-raised)] p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] tracking-[0.12em] text-[var(--color-ink-muted)] uppercase">
                  {new Date(selected.timestamp).toLocaleString()}
                </p>
                <h3 className="mt-0.5 text-sm font-semibold text-[var(--color-ink-primary)]">
                  {agentMetaFor(selected.agent_name).label} · {activityTypeLabel(selected.activity_type)}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="rounded-md p-1 text-[var(--color-ink-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-ink-primary)]"
              >
                <X size={16} />
              </button>
            </div>
            <p className="rounded-lg bg-[var(--color-sunk)] p-3 text-xs leading-relaxed text-[var(--color-ink-secondary)]">
              {selected.summary}
            </p>
            <div className="mt-3 space-y-1.5 text-xs">
              {selected.tool_name && (
                <div className="flex justify-between">
                  <span className="text-[var(--color-ink-muted)]">Tool / target</span>
                  <span className="font-mono text-[var(--color-ink-secondary)]">{selected.tool_name}</span>
                </div>
              )}
              {selected.status && (
                <div className="flex items-center justify-between">
                  <span className="text-[var(--color-ink-muted)]">Status</span>
                  <StatusPill status={selected.status} />
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-[var(--color-ink-muted)]">Initiated by</span>
                <span className="text-[var(--color-ink-secondary)]">
                  {selected.initiated_by === "autonomous_watch" ? "Fleet watch (unprompted)" : "Manager"}
                </span>
              </div>
            </div>
            {selected.trace_id && (
              <div className="mt-3 flex items-center gap-1.5 border-t border-[var(--color-border-soft)] pt-3 font-mono text-[11px] text-[var(--color-ink-muted)]">
                <Waypoints size={12} />
                trace/{selected.trace_id.slice(0, 16)}…
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
