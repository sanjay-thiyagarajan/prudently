"use client";

import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useMemo, useState } from "react";

export interface RecordColumn<T> {
  key: string;
  label: string;
  render: (row: T) => React.ReactNode;
  sortValue?: (row: T) => string | number;
  align?: "left" | "right";
}

/**
 * The generic "drill from a flagged-only summary to the full list" table — every LiveState
 * panel above this on an agent's page only ever shows the top handful of at-risk rows (by
 * design, so the page isn't a wall of "all fine" text). This is where the rest of the roster
 * lives: sortable, paginated, no filtering (that's what the summary panel and the audit log
 * are for), same interaction shape as AuditTable's sort so the fleet's tables feel like one
 * family.
 */
export function RecordTable<T>({
  columns,
  rows,
  rowKey,
  pageSize = 8,
  emptyMessage = "Nothing to show.",
}: {
  columns: RecordColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  pageSize?: number;
  emptyMessage?: string;
}) {
  const [sortIndex, setSortIndex] = useState<number | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    if (sortIndex === null) return rows;
    const col = columns[sortIndex];
    if (!col.sortValue) return rows;
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = col.sortValue!(a);
      const bv = col.sortValue!(b);
      const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, sortIndex, sortDir]);

  const pageCount = Math.max(Math.ceil(sorted.length / pageSize), 1);
  const clampedPage = Math.min(page, pageCount - 1);
  const pageRows = sorted.slice(clampedPage * pageSize, clampedPage * pageSize + pageSize);

  function handleSort(index: number) {
    if (!columns[index].sortValue) return;
    if (index === sortIndex) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortIndex(index);
      setSortDir("asc");
    }
    setPage(0);
  }

  if (rows.length === 0) {
    return <p className="text-xs text-[var(--color-ink-muted)]">{emptyMessage}</p>;
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] border-collapse text-xs">
          <thead>
            <tr className="border-b border-[var(--color-border-soft)]">
              {columns.map((col, i) => (
                <th
                  key={col.key}
                  className={`px-2.5 py-1.5 font-medium text-[var(--color-ink-muted)] ${col.align === "right" ? "text-right" : "text-left"}`}
                >
                  {col.sortValue ? (
                    <button
                      type="button"
                      onClick={() => handleSort(i)}
                      className={`inline-flex items-center gap-1 hover:text-[var(--color-ink-primary)] ${sortIndex === i ? "text-[var(--color-ink-primary)]" : ""}`}
                    >
                      {col.label}
                      {sortIndex === i ? (
                        sortDir === "asc" ? (
                          <ArrowUp size={10} />
                        ) : (
                          <ArrowDown size={10} />
                        )
                      ) : (
                        <ArrowUpDown size={10} className="opacity-40" />
                      )}
                    </button>
                  ) : (
                    col.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row) => (
              <tr key={rowKey(row)} className="border-b border-[var(--color-border-soft)] last:border-0">
                {columns.map((col) => (
                  <td key={col.key} className={`px-2.5 py-1.5 text-[var(--color-ink-secondary)] ${col.align === "right" ? "text-right" : "text-left"}`}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pageCount > 1 && (
        <div className="mt-2.5 flex items-center justify-between text-[11px] text-[var(--color-ink-muted)]">
          <span>
            {clampedPage * pageSize + 1}–{Math.min((clampedPage + 1) * pageSize, sorted.length)} of {sorted.length}
          </span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={clampedPage === 0}
              onClick={() => setPage((p) => p - 1)}
              className="rounded border border-[var(--color-border)] px-2 py-0.5 disabled:opacity-30"
            >
              Prev
            </button>
            <button
              type="button"
              disabled={clampedPage >= pageCount - 1}
              onClick={() => setPage((p) => p + 1)}
              className="rounded border border-[var(--color-border)] px-2 py-0.5 disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
