"use client";

import { BrainCircuit, Loader2, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { Panel, PanelEmpty } from "@/components/ui/Panel";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAgentMemory } from "@/lib/api/traces";

export interface MemorySubject {
  value: string;
  label: string;
}

/**
 * Runs the exact recall an agent's own tool runs mid-turn (agents/shift/agent.py's
 * `recall_unit_history` and inventory's equivalent) — this panel doesn't invent a second
 * mechanism, it exposes the first one. Framed around the subject, not the storage: a manager
 * checking whether Shift's coverage call was reasonable should be able to ask "what does it
 * remember about ICU" without knowing Memory Bank is the thing answering.
 */
export function AgentMemoryPanel({
  agentName,
  subjectLabel,
  subjects,
}: {
  agentName: string;
  subjectLabel: string;
  subjects: MemorySubject[];
}) {
  const { idToken } = useAuth();
  const [subject, setSubject] = useState(subjects[0]?.value ?? "");
  const [question, setQuestion] = useState("");
  const [facts, setFacts] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function recall(forSubject: string, forQuestion: string) {
    if (!idToken || !forSubject) return;
    setBusy(true);
    setFailed(false);
    try {
      const result = await fetchAgentMemory(
        idToken,
        agentName,
        forSubject,
        forQuestion.trim() || undefined,
      );
      setFacts(result.facts);
    } catch {
      setFailed(true);
      setFacts(null);
    } finally {
      setBusy(false);
    }
  }

  // Recall on first load and whenever the subject changes — the question box is for a manager
  // who wants to narrow it further, not a gate on seeing anything at all. Deferred a tick so
  // the state updates inside `recall` happen outside the effect's own synchronous pass.
  useEffect(() => {
    if (!subject) return;
    const timer = setTimeout(() => recall(subject, question), 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentName, subject, idToken]);

  if (subjects.length === 0) {
    return (
      <Panel title="What it remembers" icon={BrainCircuit} accent="var(--color-a2a)">
        <PanelEmpty>
          Nothing to recall yet — the fleet watch hasn&apos;t observed this agent&apos;s domain
          shift since the last reset.
        </PanelEmpty>
      </Panel>
    );
  }

  return (
    <Panel
      title="What it remembers"
      icon={BrainCircuit}
      accent="var(--color-a2a)"
      subtitle={`A persistent Memory Bank timeline, kept per ${subjectLabel}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-a2a)]"
        >
          {subjects.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <form
          className="flex min-w-0 flex-1 items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            recall(subject, question);
          }}
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask it something more specific…"
            className="min-w-0 flex-1 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none placeholder:text-[var(--color-ink-muted)] focus:border-[var(--color-a2a)]"
          />
          <button
            type="submit"
            disabled={busy}
            className="shrink-0 rounded-md border border-[var(--color-border)] px-2.5 py-1.5 text-xs font-medium text-[var(--color-ink-secondary)] transition-colors hover:border-[var(--color-a2a)] hover:text-[var(--color-a2a)] disabled:opacity-50"
          >
            Ask
          </button>
        </form>
      </div>

      <div className="mt-3.5 border-t border-[var(--color-border-soft)] pt-3.5">
        {busy ? (
          <div className="flex min-h-[64px] items-center justify-center">
            <Loader2 className="animate-spin text-[var(--color-ink-muted)]" size={18} />
          </div>
        ) : failed ? (
          <div className="flex items-center gap-2 text-xs text-[var(--color-ink-secondary)]">
            <TriangleAlert size={13} className="shrink-0 text-[var(--color-elevated)]" />
            Memory Bank didn&apos;t respond — try again in a moment.
          </div>
        ) : !facts || facts.length === 0 ? (
          <p className="text-xs text-[var(--color-ink-muted)]">
            Nothing recalled for this {subjectLabel} yet.
          </p>
        ) : (
          <ul className="space-y-2">
            {facts.map((fact, i) => (
              <li
                key={i}
                className="rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-sunk)] px-3 py-2 text-xs leading-relaxed text-[var(--color-ink-secondary)]"
              >
                {fact}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Panel>
  );
}
