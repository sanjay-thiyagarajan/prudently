"use client";

import { Loader2, Send, ShieldAlert, Stethoscope, TriangleAlert } from "lucide-react";
import { useState } from "react";

import { Panel, PanelEmpty } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/contexts/AuthContext";
import {
  notifyPatient,
  updateCaseStatus,
  useCaseDetail,
  useSurgicalCases,
} from "@/lib/api/surgicalSchedule";
import type { SurgicalCase, SurgicalCaseStatus } from "@/lib/types/dashboard";

const NEXT_STATUS: Partial<Record<SurgicalCaseStatus, SurgicalCaseStatus>> = {
  scheduled: "confirmed",
  confirmed: "in_progress",
  delayed: "confirmed",
  in_progress: "completed",
};

function formatWindow(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const time = (d: Date) => d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  return `${time(start)} – ${time(end)}`;
}

function CaseDetail({ caseId, onChanged }: { caseId: string; onChanged: () => void }) {
  const { idToken } = useAuth();
  const { detail, error, isLoading, refresh } = useCaseDetail(caseId);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState<"status" | "notify" | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  if (isLoading) return <Loader2 className="animate-spin text-[var(--color-hero)]" size={16} />;

  if (error) {
    const forbidden = error instanceof Error && error.message.includes("403");
    return (
      <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-sunk)] px-3 py-2.5 text-xs text-[var(--color-ink-secondary)]">
        <ShieldAlert size={14} className="shrink-0 text-[var(--color-elevated)]" />
        {forbidden
          ? "Patient identity is restricted to admin and clinician roles. You can still see the schedule and conflicts."
          : "Couldn't load case detail."}
      </div>
    );
  }

  if (!detail) return null;
  const nextStatus = NEXT_STATUS[detail.status];

  async function handleAdvanceStatus() {
    if (!idToken || !nextStatus) return;
    setBusy("status");
    setFeedback(null);
    try {
      await updateCaseStatus(idToken, caseId, nextStatus);
      await refresh();
      onChanged();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Status update failed.");
    } finally {
      setBusy(null);
    }
  }

  async function handleNotify() {
    if (!idToken || !message.trim()) return;
    setBusy("notify");
    setFeedback(null);
    try {
      const result = await notifyPatient(idToken, caseId, message.trim());
      setFeedback(
        result.status === "pending_approval"
          ? "Sent for manager approval — the patient has not been notified yet."
          : result.status === "consent_declined"
            ? (result.message ?? "This patient has not opted into email notifications.")
            : "Notification sent.",
      );
      setMessage("");
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Notify failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-sunk)] p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-[var(--color-ink-primary)]">
            {detail.patient?.name ?? "Patient identity restricted"}
          </p>
          <p className="text-xs text-[var(--color-ink-secondary)]">
            {detail.procedure_name} · {detail.operating_room}
          </p>
        </div>
        <StatusPill status={detail.status} />
      </div>

      {detail.patient && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-[var(--color-ink-secondary)]">
          <span>DOB: {detail.patient.date_of_birth}</span>
          <span>Contact: {detail.patient.contact_email}</span>
          <span className="col-span-2">
            Email notifications:{" "}
            {detail.patient.notification_consent_email ? "opted in" : "opted out"}
          </span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {nextStatus && (
          <button
            type="button"
            onClick={handleAdvanceStatus}
            disabled={busy !== null}
            className="flex items-center gap-1.5 rounded-lg bg-[var(--color-hero-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--color-hero)] disabled:opacity-50"
          >
            {busy === "status" ? <Loader2 size={12} className="animate-spin" /> : null}
            Mark {nextStatus.replace(/_/g, " ")}
          </button>
        )}
      </div>

      <div className="flex flex-col gap-2 border-t border-[var(--color-border-soft)] pt-3">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Message to the patient about this case's status…"
          rows={2}
          className="w-full resize-none rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
        />
        <button
          type="button"
          onClick={handleNotify}
          disabled={busy !== null || !message.trim()}
          className="flex w-fit items-center gap-1.5 rounded-lg bg-[var(--color-safe-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--color-safe)] disabled:opacity-50"
        >
          {busy === "notify" ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
          Notify patient
        </button>
        {feedback && <p className="text-xs text-[var(--color-ink-secondary)]">{feedback}</p>}
      </div>
    </div>
  );
}

function CaseRow({
  surgicalCase,
  hasConflict,
  selected,
  onSelect,
}: {
  surgicalCase: SurgicalCase;
  hasConflict: boolean;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr
      onClick={onSelect}
      className={`cursor-pointer border-t border-[var(--color-border-soft)] transition-colors ${
        selected ? "bg-[var(--color-hero-soft)]" : "hover:bg-[var(--color-sunk)]"
      }`}
    >
      <td className="px-3 py-2 text-[var(--color-ink-primary)]">
        {surgicalCase.procedure_name}
        {hasConflict && (
          <TriangleAlert
            size={12}
            className="ml-1.5 inline text-[var(--color-critical)]"
            aria-label="Scheduling conflict"
          />
        )}
      </td>
      <td className="px-3 py-2 text-[var(--color-ink-secondary)]">{surgicalCase.operating_room}</td>
      <td className="px-3 py-2 text-[var(--color-ink-secondary)]">
        {surgicalCase.surgeon_staff_id ?? "Unassigned"}
      </td>
      <td className="px-3 py-2 text-[var(--color-ink-secondary)]">
        {formatWindow(surgicalCase.scheduled_start, surgicalCase.scheduled_end)}
      </td>
      <td className="px-3 py-2 text-right">
        <StatusPill status={surgicalCase.status} />
      </td>
    </tr>
  );
}

export function SurgicalSchedulePanel() {
  const { cases, conflicts, isLoading, error, refresh } = useSurgicalCases();
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  const conflictedCaseIds = new Set(conflicts.flatMap((c) => [c.case_id_a, c.case_id_b]));

  return (
    <Panel title="Surgical Scheduling" icon={Stethoscope} live>
      {isLoading ? (
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={16} />
      ) : error ? (
        <PanelEmpty>Sign in to view the surgical schedule.</PanelEmpty>
      ) : cases.length === 0 ? (
        <PanelEmpty>No surgical cases scheduled.</PanelEmpty>
      ) : (
        <div className="space-y-3">
          {conflicts.length > 0 && (
            <div className="flex items-start gap-2 rounded-lg border border-[var(--color-critical)]/35 bg-[var(--color-critical-soft)] px-3 py-2.5 text-xs text-[var(--color-critical)]">
              <TriangleAlert size={14} className="mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold">
                  {conflicts.length} scheduling {conflicts.length === 1 ? "conflict" : "conflicts"}{" "}
                  detected
                </p>
                {conflicts.map((c) => (
                  <p key={`${c.case_id_a}-${c.case_id_b}`} className="mt-0.5 opacity-90">
                    {c.case_id_a} / {c.case_id_b} — {c.reason}
                  </p>
                ))}
              </div>
            </div>
          )}

          <div className="overflow-x-auto rounded-xl border border-[var(--color-border-soft)]">
            <table className="w-full min-w-[560px] text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--color-border-soft)] text-[var(--color-ink-muted)] uppercase tracking-wide">
                  <th className="px-3 py-2 font-medium">Procedure</th>
                  <th className="px-3 py-2 font-medium">OR</th>
                  <th className="px-3 py-2 font-medium">Surgeon</th>
                  <th className="px-3 py-2 font-medium">Window</th>
                  <th className="px-3 py-2 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((surgicalCase) => (
                  <CaseRow
                    key={surgicalCase.case_id}
                    surgicalCase={surgicalCase}
                    hasConflict={conflictedCaseIds.has(surgicalCase.case_id)}
                    selected={selectedCaseId === surgicalCase.case_id}
                    onSelect={() =>
                      setSelectedCaseId(
                        selectedCaseId === surgicalCase.case_id ? null : surgicalCase.case_id,
                      )
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>

          {selectedCaseId && (
            <CaseDetail caseId={selectedCaseId} onChanged={() => refresh()} />
          )}
        </div>
      )}
    </Panel>
  );
}
