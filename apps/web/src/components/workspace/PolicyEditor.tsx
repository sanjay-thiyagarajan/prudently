"use client";

import { Loader2, Save, Settings2 } from "lucide-react";
import { useState } from "react";

import { Panel } from "@/components/ui/Panel";
import { useAuth } from "@/contexts/AuthContext";
import { saveApprovalPolicy, useApprovalPolicies } from "@/lib/api/policy";
import type { ApprovalPolicy } from "@/lib/types/dashboard";

export const TASK_LABEL: Record<string, string> = {
  contact_vendor_for_reorder: "Contact vendor for reorder",
  notify_staff_credential_escalation: "Notify staff — credential escalation",
  notify_staff_reallocation: "Notify staff — shift reallocation",
  send_vendor_reply: "Reply to vendor",
};

export function PolicyRow({ policy }: { policy: ApprovalPolicy }) {
  const { idToken } = useAuth();
  const [requiresApproval, setRequiresApproval] = useState(policy.requires_approval);
  const [approverEmail, setApproverEmail] = useState(policy.approver_email ?? "");
  const [notifyEmails, setNotifyEmails] = useState(policy.notify_emails.join(", "));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    if (!idToken) return;
    setSaving(true);
    setSaved(false);
    try {
      await saveApprovalPolicy(idToken, policy.task_type, {
        requires_approval: requiresApproval,
        approver_email: approverEmail.trim() || null,
        notify_emails: notifyEmails
          .split(",")
          .map((e) => e.trim())
          .filter(Boolean),
        notify_on_complete: policy.notify_on_complete,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className="rounded-xl border border-[var(--color-border-soft)] p-3.5">
      <p className="text-sm font-medium text-[var(--color-ink-primary)]">
        {TASK_LABEL[policy.task_type] ?? policy.task_type}
      </p>
      <div className="mt-3 flex flex-col gap-2.5">
        <label className="flex items-center gap-2 text-xs text-[var(--color-ink-secondary)]">
          <input
            type="checkbox"
            checked={requiresApproval}
            onChange={(e) => setRequiresApproval(e.target.checked)}
            className="size-3.5 accent-[var(--color-hero)]"
          />
          Requires manager approval
        </label>
        <input
          type="email"
          placeholder="Approver email (defaults to manager_email)"
          value={approverEmail}
          onChange={(e) => setApproverEmail(e.target.value)}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
        />
        <input
          type="text"
          placeholder="Also notify (comma-separated emails)"
          value={notifyEmails}
          onChange={(e) => setNotifyEmails(e.target.value)}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
        />
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="flex items-center justify-center gap-1.5 self-start rounded-lg bg-[var(--color-hero-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--color-hero)] transition-opacity disabled:opacity-50"
        >
          {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
          {saved ? "Saved" : "Save"}
        </button>
      </div>
    </li>
  );
}

export function PolicyEditor() {
  const { policies, isLoading } = useApprovalPolicies();

  return (
    <Panel title="Approval policy" icon={Settings2}>
      {isLoading ? (
        <div className="flex h-full min-h-[220px] items-center justify-center">
          <Loader2 className="animate-spin text-[var(--color-ink-muted)]" size={20} />
        </div>
      ) : policies.length === 0 ? (
        <div className="flex h-full min-h-[220px] flex-col items-center justify-center gap-2 text-center">
          <Settings2 size={28} className="text-[var(--color-ink-muted)]" />
          <p className="text-sm text-[var(--color-ink-secondary)]">No policy configured yet.</p>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {policies.map((policy) => (
            <PolicyRow key={policy.task_type} policy={policy} />
          ))}
        </ul>
      )}
    </Panel>
  );
}
