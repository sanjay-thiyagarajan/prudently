"use client";

import { motion } from "framer-motion";
import { Loader2, TriangleAlert, Waypoints, X } from "lucide-react";
import { useState } from "react";

import { useTrace } from "@/lib/api/traces";
import type { TraceSpan } from "@/lib/types/dashboard";

function offsetAndWidth(span: TraceSpan, traceStartMs: number, traceDurationMs: number) {
  if (!span.start_time || !traceDurationMs) return { left: 0, width: 2 };
  const startMs = new Date(span.start_time).getTime() - traceStartMs;
  const endMs = span.end_time ? new Date(span.end_time).getTime() - traceStartMs : startMs;
  const left = (startMs / traceDurationMs) * 100;
  const width = Math.max(((endMs - startMs) / traceDurationMs) * 100, 0.4);
  return { left, width };
}

// Above this age, a still-missing trace isn't "still exporting" — it's gone. Cloud Trace
// export is synchronous on the writing side (services/platform/observability_vertex.py's
// SimpleSpanProcessor), so a real delay is a few seconds at most; a few minutes means the
// export never landed.
const EXPORT_LAG_GRACE_MS = 2 * 60 * 1000;

export function TraceViewer({
  traceId,
  timestamp,
  onClose,
}: {
  traceId: string;
  timestamp?: string;
  onClose: () => void;
}) {
  const { data, error, isLoading } = useTrace(traceId);
  // Captured once, at mount — a lazy initializer, not a read during render, so this stays
  // pure from React's own point of view even though Date.now() itself isn't.
  const [openedAtMs] = useState(() => Date.now());
  const ageMs = timestamp ? openedAtMs - new Date(timestamp).getTime() : 0;
  const likelyGone = ageMs > EXPORT_LAG_GRACE_MS;

  const spans = data?.spans ?? [];
  const times = spans
    .map((s) => (s.start_time ? new Date(s.start_time).getTime() : null))
    .filter((t): t is number => t !== null);
  const traceStartMs = times.length ? Math.min(...times) : 0;
  const endTimes = spans
    .map((s) => (s.end_time ? new Date(s.end_time).getTime() : null))
    .filter((t): t is number => t !== null);
  const traceEndMs = endTimes.length ? Math.max(...endTimes) : traceStartMs;
  const traceDurationMs = Math.max(traceEndMs - traceStartMs, 1);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl"
      >
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--color-border-soft)] px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-xl bg-[var(--color-hero-soft)] text-[var(--color-hero)]">
              <Waypoints size={18} />
            </span>
            <div>
              <h2 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[var(--color-ink-primary)]">
                Step-by-step trace
              </h2>
              <p className="font-mono text-xs text-[var(--color-ink-muted)]">
                Cloud Trace · {traceId}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-lg text-[var(--color-ink-muted)] hover:bg-[var(--color-border-soft)] hover:text-[var(--color-ink-primary)]"
          >
            <X size={16} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-5">
          {isLoading ? (
            <div className="flex min-h-[160px] items-center justify-center">
              <Loader2 className="animate-spin text-[var(--color-ink-muted)]" size={20} />
            </div>
          ) : error || !data ? (
            <div className="flex min-h-[160px] flex-col items-center justify-center gap-2 px-4 text-center">
              <TriangleAlert className="text-[var(--color-elevated)]" size={24} />
              {likelyGone ? (
                <>
                  <p className="text-sm text-[var(--color-ink-secondary)]">
                    This trace never reached Cloud Trace — it isn&apos;t just running late.
                  </p>
                  <p className="max-w-sm text-xs text-[var(--color-ink-muted)]">
                    Spans generated when an agent runs on its own deployed Reasoning Engine
                    (rather than the fleet watch&apos;s in-process path) aren&apos;t always
                    exported successfully. The action itself still happened and is recorded
                    above — only this step-by-step replay is missing.
                  </p>
                </>
              ) : (
                <p className="text-sm text-[var(--color-ink-secondary)]">
                  Trace not found yet — Cloud Trace export can lag a few seconds behind the call.
                </p>
              )}
            </div>
          ) : spans.length === 0 ? (
            <p className="text-sm text-[var(--color-ink-secondary)]">No spans in this trace.</p>
          ) : (
            <>
              <p className="mb-3 text-xs text-[var(--color-ink-secondary)]">
                Every internal step this request passed through, in order, with real timing —
                the underlying proof this action actually ran through the fleet.
              </p>
              <ul className="space-y-1.5">
              {spans.map((span) => {
                const { left, width } = offsetAndWidth(span, traceStartMs, traceDurationMs);
                return (
                  <li key={span.span_id} className="text-xs">
                    <div className="mb-0.5 flex items-baseline justify-between gap-2">
                      <span className="truncate font-medium text-[var(--color-ink-primary)]">
                        {span.name}
                      </span>
                    </div>
                    <div className="relative h-2 rounded-full bg-[var(--color-border-soft)]">
                      <div
                        className="absolute top-0 h-2 rounded-full bg-[var(--color-hero)]"
                        style={{ left: `${left}%`, width: `${width}%` }}
                      />
                    </div>
                  </li>
                );
              })}
              </ul>
            </>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
