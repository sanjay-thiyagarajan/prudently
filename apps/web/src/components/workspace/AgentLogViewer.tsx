"use client";

import { Loader2, ScrollText } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import { useAgentLogs } from "@/lib/api/traces";

export function AgentLogViewer({ agentName }: { agentName: string }) {
  const { data, error, isLoading } = useAgentLogs(agentName);
  const logs = data?.logs ?? [];

  return (
    <Panel
      title="Cloud Logging"
      icon={ScrollText}
      accent="var(--color-ink-secondary)"
      subtitle="Reasoning Engine stdout/stderr — engine-scoped, not agent-scoped when reached via Coordinator"
    >
      {isLoading ? (
        <div className="flex min-h-[160px] items-center justify-center">
          <Loader2 className="animate-spin text-[var(--color-ink-muted)]" size={20} />
        </div>
      ) : error || !data ? (
        <p className="text-sm text-[var(--color-ink-secondary)]">Couldn&apos;t load logs.</p>
      ) : logs.length === 0 ? (
        <p className="text-sm text-[var(--color-ink-secondary)]">No recent log entries.</p>
      ) : (
        <ul className="max-h-[320px] space-y-1 overflow-y-auto font-mono text-[11px] leading-relaxed">
          {logs.map((log, index) => (
            <li
              key={index}
              className="truncate rounded px-2 py-1 text-[var(--color-ink-secondary)] hover:bg-[var(--color-border-soft)]"
              title={log.text}
            >
              <span className="text-[var(--color-ink-muted)]">
                {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "—"}
              </span>{" "}
              {log.text}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
