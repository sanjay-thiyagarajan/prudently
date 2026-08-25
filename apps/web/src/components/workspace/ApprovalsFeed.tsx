"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Clock, Loader2, MailQuestion, X, XCircle } from "lucide-react";
import { useState } from "react";

import { Panel } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/contexts/AuthContext";
import { resolveApproval } from "@/lib/api/approvals";
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

function ApprovalRow({
  approval,
  onResolved,
}: {
  approval: Approval;
  onResolved?: () => void;
}) {
  const { idToken } = useAuth();
  const [busy, setBusy] = useState<"approved" | "rejected" | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const Icon = STATUS_ICON[approval.status];

  // `id` only ever survives redaction for a signed-in caller (services/redaction.py's
  // `_redact_approval_ids`) — no id means either signed out, or the email-only path is the
  // only way to resolve this one.
  const canResolveInApp = idToken && approval.id && approval.status === "pending";

  async function handleResolve(decision: "approved" | "rejected") {
    if (!idToken || !approval.id) return;
    setBusy(decision);
    setFailed(null);
    try {
      await resolveApproval(idToken, approval.id, decision);
      onResolved?.();
    } catch (err) {
      setFailed(err instanceof Error ? err.message : "Couldn't resolve this request.");
    } finally {
      setBusy(null);
    }
  }

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
          <div className="mt-2 flex items-center justify-between gap-2">
            <p className="text-[10px] text-[var(--color-ink-muted)]">
              {relativeTime(approval.timestamp)}
            </p>
            {canResolveInApp && (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => handleResolve("approved")}
                  disabled={busy !== null}
                  className="inline-flex items-center gap-1 rounded-md bg-[var(--color-safe-soft)] px-2 py-1 text-[11px] font-semibold text-[var(--color-safe)] transition-opacity hover:opacity-80 disabled:opacity-50"
                >
                  {busy === "approved" ? (
                    <Loader2 size={11} className="animate-spin" />
                  ) : (
                    <CheckCircle2 size={11} />
                  )}
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => handleResolve("rejected")}
                  disabled={busy !== null}
                  className="inline-flex items-center gap-1 rounded-md bg-[var(--color-critical-soft)] px-2 py-1 text-[11px] font-semibold text-[var(--color-critical)] transition-opacity hover:opacity-80 disabled:opacity-50"
                >
                  {busy === "rejected" ? (
                    <Loader2 size={11} className="animate-spin" />
                  ) : (
                    <X size={11} />
                  )}
                  Reject
                </button>
              </div>
            )}
          </div>
          {failed && <p className="mt-1.5 text-[11px] text-[var(--color-critical)]">{failed}</p>}
        </div>
      </div>
    </motion.li>
  );
}

export function ApprovalsFeed({
  approvals,
  onResolved,
}: {
  approvals: Approval[];
  onResolved?: () => void;
}) {
  return (
    <Panel title="Approvals" icon={MailQuestion} live>
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
            <ApprovalRow
              key={`${approval.timestamp}-${index}`}
              approval={approval}
              onResolved={onResolved}
            />
          ))}
        </ul>
      )}
    </Panel>
  );
}
