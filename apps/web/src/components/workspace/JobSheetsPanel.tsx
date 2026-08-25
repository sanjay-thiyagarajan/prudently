"use client";

import { CheckCircle2, ClipboardList, Loader2, Play, Plus } from "lucide-react";
import { useState } from "react";

import { Panel, PanelEmpty } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/contexts/AuthContext";
import { useDashboardOverview } from "@/lib/api/dashboard";
import {
  completeFacilityJobSheet,
  createFacilityJobSheet,
  startFacilityJobSheet,
  useDutyJobSheet,
  useFacilityJobSheets,
} from "@/lib/api/jobSheets";
import type { FacilityJobSheetPriority } from "@/lib/types/dashboard";

const PRIORITIES: FacilityJobSheetPriority[] = ["low", "normal", "high", "urgent"];

function DutyRosterPanel() {
  const { data: overview } = useDashboardOverview();
  const units = overview ? Object.keys(overview.shift.unit_summary).sort() : [];
  const [unit, setUnit] = useState<string | null>(null);
  const activeUnit = unit ?? units[0] ?? null;
  const { sheet, isLoading } = useDutyJobSheet(activeUnit);

  return (
    <Panel title="Duty Roster" icon={ClipboardList}>
      {units.length === 0 ? (
        <PanelEmpty>No units to show yet.</PanelEmpty>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">
            {units.map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => setUnit(u)}
                className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
                  activeUnit === u
                    ? "border-[var(--color-hero)] bg-[var(--color-hero-soft)] text-[var(--color-hero)]"
                    : "border-[var(--color-border)] text-[var(--color-ink-secondary)] hover:bg-[var(--color-sunk)]"
                }`}
              >
                {u}
              </button>
            ))}
          </div>

          {isLoading ? (
            <Loader2 className="animate-spin text-[var(--color-hero)]" size={16} />
          ) : !sheet || sheet.staff.length === 0 ? (
            <PanelEmpty>No staff assigned to this unit.</PanelEmpty>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-[var(--color-border-soft)]">
              <table className="w-full min-w-[420px] text-left text-xs">
                <thead>
                  <tr className="border-b border-[var(--color-border-soft)] text-[var(--color-ink-muted)] uppercase tracking-wide">
                    <th className="px-3 py-2 font-medium">Name</th>
                    <th className="px-3 py-2 font-medium">Role</th>
                    <th className="px-3 py-2 font-medium text-right">Trailing hours</th>
                    <th className="px-3 py-2 font-medium text-right">Fatigue</th>
                  </tr>
                </thead>
                <tbody>
                  {sheet.staff.map((member) => (
                    <tr key={member.staff_id} className="border-t border-[var(--color-border-soft)]">
                      <td className="px-3 py-2 text-[var(--color-ink-primary)]">{member.name}</td>
                      <td className="px-3 py-2 text-[var(--color-ink-secondary)]">{member.role}</td>
                      <td className="px-3 py-2 text-right text-[var(--color-ink-secondary)]">
                        {member.trailing_hours.toFixed(1)}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <StatusPill status={member.risk_level} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

function FacilitiesPanel() {
  const { idToken } = useAuth();
  const { sheets, isLoading, refresh } = useFacilityJobSheets();
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState("");
  const [priority, setPriority] = useState<FacilityJobSheetPriority>("normal");
  const [creating, setCreating] = useState(false);
  const [busySheetId, setBusySheetId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleCreate() {
    if (!idToken || !title.trim()) return;
    setCreating(true);
    setFormError(null);
    try {
      await createFacilityJobSheet(idToken, {
        title: title.trim(),
        description: "",
        location,
        assigned_to: "Unassigned",
        priority,
      });
      await refresh();
      setTitle("");
      setLocation("");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create work order.");
    } finally {
      setCreating(false);
    }
  }

  async function handleStart(sheetId: string) {
    if (!idToken) return;
    setBusySheetId(sheetId);
    try {
      await startFacilityJobSheet(idToken, sheetId);
      await refresh();
    } finally {
      setBusySheetId(null);
    }
  }

  async function handleComplete(sheetId: string) {
    if (!idToken) return;
    setBusySheetId(sheetId);
    try {
      await completeFacilityJobSheet(idToken, sheetId);
      await refresh();
    } finally {
      setBusySheetId(null);
    }
  }

  return (
    <Panel title="Facilities Work Orders" icon={ClipboardList} live>
      <div className="space-y-4">
        <div className="flex flex-wrap items-end gap-2 rounded-xl border border-[var(--color-border-soft)] p-3.5">
          <div className="min-w-[160px] flex-1">
            <p className="mb-1 text-xs font-medium text-[var(--color-ink-secondary)]">Title</p>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Replace ICU bed 4's IV pump"
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
            />
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-[var(--color-ink-secondary)]">Location</p>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="ICU"
              className="w-32 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
            />
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-[var(--color-ink-secondary)]">Priority</p>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as FacilityJobSheetPriority)}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={handleCreate}
            disabled={creating || !title.trim()}
            className="flex items-center gap-1.5 rounded-lg bg-[var(--color-hero-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--color-hero)] disabled:opacity-50"
          >
            {creating ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
            Create work order
          </button>
          {formError && <p className="w-full text-xs text-[var(--color-critical)]">{formError}</p>}
        </div>

        {isLoading ? (
          <Loader2 className="animate-spin text-[var(--color-hero)]" size={16} />
        ) : sheets.length === 0 ? (
          <PanelEmpty>No open work orders.</PanelEmpty>
        ) : (
          <div className="space-y-2">
            {sheets.map((sheet) => (
              <div
                key={sheet.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--color-border-soft)] px-3.5 py-2.5"
              >
                <div>
                  <p className="text-sm font-medium text-[var(--color-ink-primary)]">{sheet.title}</p>
                  <p className="text-xs text-[var(--color-ink-secondary)]">
                    {sheet.location || "Unspecified"} · {sheet.priority} priority
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill status={sheet.status} />
                  {sheet.status === "open" && (
                    <button
                      type="button"
                      onClick={() => handleStart(sheet.id)}
                      disabled={busySheetId === sheet.id}
                      className="flex items-center gap-1.5 rounded-lg bg-[var(--color-hero-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--color-hero)] disabled:opacity-50"
                    >
                      {busySheetId === sheet.id ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Play size={12} />
                      )}
                      Start
                    </button>
                  )}
                  {sheet.status === "in_progress" && (
                    <button
                      type="button"
                      onClick={() => handleComplete(sheet.id)}
                      disabled={busySheetId === sheet.id}
                      className="flex items-center gap-1.5 rounded-lg bg-[var(--color-safe-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--color-safe)] disabled:opacity-50"
                    >
                      {busySheetId === sheet.id ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <CheckCircle2 size={12} />
                      )}
                      Complete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Panel>
  );
}

export function JobSheetsPanels() {
  return (
    <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
      <DutyRosterPanel />
      <FacilitiesPanel />
    </div>
  );
}
