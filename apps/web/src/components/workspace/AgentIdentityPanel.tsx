"use client";

import { ExternalLink } from "lucide-react";

import { reasoningEngineConsoleUrl } from "@/lib/agentMeta";
import type { FleetAgent } from "@/lib/types/dashboard";

/** A field/value row, monospaced value — matches AgentLogViewer's own mono treatment next to
 * it in the same accordion. */
function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-b border-[var(--color-border-soft)] py-2 last:border-0 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4">
      <span className="text-xs text-[var(--color-ink-muted)]">{label}</span>
      <span className="font-[family-name:var(--font-mono)] text-xs break-all text-[var(--color-ink-secondary)] sm:text-right">
        {children}
      </span>
    </div>
  );
}

/**
 * Deployment detail — the same drill-down tier as the log viewer it sits beside, not a
 * headline claim. Every agent here runs under its own IAM identity rather than a shared one;
 * that fact is worth being able to check, but a manager opening an agent's page to see whether
 * a nurse is overworked shouldn't be greeted with a service-account email above the fold.
 */
export function AgentIdentityPanel({
  agent,
  memoryScope,
  serviceAccount,
}: {
  agent: FleetAgent;
  memoryScope: string | null;
  serviceAccount: string;
}) {
  return (
    <div className="mt-4 border-t border-[var(--color-border-soft)] pt-4">
      <p className="mb-1 text-[10px] tracking-[0.14em] text-[var(--color-ink-muted)] uppercase">
        Deployment
      </p>
      <div className="flex flex-col">
        <Row label="Runs as">{serviceAccount}</Row>
        <Row label="Reasoning Engine">
          {agent.reasoning_engine_id ? (
            <a
              href={reasoningEngineConsoleUrl(agent.reasoning_engine_id)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 hover:text-[var(--color-hero)] hover:underline"
            >
              {agent.reasoning_engine_id}
              <ExternalLink size={11} className="shrink-0" />
            </a>
          ) : (
            <span className="text-[var(--color-ink-muted)]">not deployed as a standalone engine</span>
          )}
        </Row>
        <Row label="Remembers">
          {memoryScope ?? <span className="text-[var(--color-ink-muted)]">nothing — delegates only</span>}
        </Row>
        <Row label="Reads/writes">
          {agent.firestore_collections.length > 0 ? (
            <span className="inline-flex flex-wrap justify-end gap-1.5">
              {agent.firestore_collections.map((c) => (
                <span
                  key={c}
                  className="rounded border border-[var(--color-border)] bg-[var(--color-sunk)] px-1.5 py-0.5"
                >
                  {c}
                </span>
              ))}
            </span>
          ) : (
            <span className="text-[var(--color-ink-muted)]">none</span>
          )}
        </Row>
      </div>
    </div>
  );
}
