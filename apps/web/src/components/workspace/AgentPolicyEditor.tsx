"use client";

import { Loader2, Settings2 } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import { useApprovalPolicies } from "@/lib/api/policy";

import { PolicyRow } from "./PolicyEditor";

// Scoped to one agent's own task_type, reusing PolicyEditor's PolicyRow (same save logic,
// same fields) rather than duplicating it — this is the "permissions portion... which
// currently exists in the dashboard" moved onto the agent's own detail page.
export function AgentPolicyEditor({ taskType }: { taskType: string | null }) {
  const { policies, isLoading } = useApprovalPolicies();
  const policy = taskType ? policies.find((p) => p.task_type === taskType) : undefined;

  return (
    <Panel title="Permissions" icon={Settings2}>
      {!taskType ? (
        <div className="flex h-full min-h-[160px] flex-col items-center justify-center gap-2 text-center">
          <Settings2 size={28} className="text-[var(--color-ink-muted)]" />
          <p className="text-sm text-[var(--color-ink-secondary)]">
            This agent has no approval-gated action.
          </p>
        </div>
      ) : isLoading ? (
        <div className="flex h-full min-h-[160px] items-center justify-center">
          <Loader2 className="animate-spin text-[var(--color-ink-muted)]" size={20} />
        </div>
      ) : !policy ? (
        <p className="text-sm text-[var(--color-ink-secondary)]">No policy configured yet.</p>
      ) : (
        <ul>
          <PolicyRow policy={policy} />
        </ul>
      )}
    </Panel>
  );
}
