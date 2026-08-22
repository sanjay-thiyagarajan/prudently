"use client";

import { Loader2, Lock } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";

import { useAuth } from "@/contexts/AuthContext";

// Inline gating rather than a /login route, deliberately: this dashboard is a single scrolling
// page by design (see AGENTS.md — "scroll position is a better instrument than navigation"),
// and a second route for the login form would be the first crack in that stated philosophy for
// no real benefit. RequireAuth just swaps what page.tsx's single route renders.
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading, signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (loading) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3">
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={28} />
        <p className="text-sm text-[var(--color-ink-secondary)]">Checking session…</p>
      </main>
    );
  }

  if (user) return <>{children}</>;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await signIn(email, password);
    } catch {
      setError("Sign-in failed. Check the email and password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-6">
      <span className="flex size-12 items-center justify-center rounded-2xl bg-[var(--color-hero-soft)] text-[var(--color-hero)]">
        <Lock size={22} />
      </span>
      <div className="text-center">
        <h1 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--color-ink-primary)]">
          Prudently Command Center
        </h1>
        <p className="mt-1 text-sm text-[var(--color-ink-secondary)]">
          Sign in to view the live fleet.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="flex w-full max-w-xs flex-col gap-3">
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
        />
        <input
          type="password"
          required
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm text-[var(--color-ink-primary)] outline-none focus:border-[var(--color-hero)]"
        />
        {error && <p className="text-xs text-[var(--color-critical)]">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="mt-1 rounded-xl bg-[var(--color-hero)] px-4 py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
