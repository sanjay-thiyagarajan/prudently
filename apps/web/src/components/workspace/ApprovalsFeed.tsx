"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Clock, MailQuestion, XCircle } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import type { Approval } from "@/lib/types/dashboard";

function relativeTime(iso: string): string {
  const deltaMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(deltaMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

const STATUS_ICON = { pending: Clock, approved: CheckCircle2, rejected: XCircle };

function ApprovalRow({ approval }: { approval: Approval }) {
  const Icon = STATUS_ICON[approval.status];
  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className="rounded-xl border border-[var(--color-border-soft)] p-3.5"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-[var(--color-border-soft)] text-[var(--color-ink-secondary)]">
          <Icon size={15} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-sm font-medium text-[var(--color-ink-primary)]">
              {approval.subject}
            </p>
            <StatusPill status={approval.status} />
          </div>
          <p className="mt-1 text-xs text-[var(--color-ink-secondary)]">
            To: <span className="font-medium">{approval.recipient_label}</span> — requested by{" "}
            {approval.requested_by}
          </p>
          <p className="mt-2 text-[10px] text-[var(--color-ink-muted)]">
            {relativeTime(approval.timestamp)}
          </p>
        </div>
      </div>
    </motion.li>
  );
}

export function ApprovalsFeed({ approvals }: { approvals: Approval[] }) {
  return (
    <Panel title="Approvals" icon={MailQuestion} accent="var(--color-hero)" live>
      {approvals.length === 0 ? (
        <div className="flex h-full min-h-[220px] flex-col items-center justify-center gap-2 text-center">
          <MailQuestion size={28} className="text-[var(--color-ink-muted)]" />
          <p className="text-sm text-[var(--color-ink-secondary)]">
            No approval requests yet.
          </p>
          <p className="text-xs text-[var(--color-ink-muted)]">
            Vendor and staff contact actions land here when an agent requests one.
          </p>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {approvals.map((approval, index) => (
            <ApprovalRow key={`${approval.timestamp}-${index}`} approval={approval} />
          ))}
        </ul>
      )}
    </Panel>
  );
}
