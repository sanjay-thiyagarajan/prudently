"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "prudently-theme";

const OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "system", label: "System", icon: Monitor },
  { value: "dark", label: "Dark", icon: Moon },
];

/**
 * The stored preference is external state (it lives in localStorage and can change in another
 * tab), so it is read through useSyncExternalStore rather than mirrored into component state
 * in an effect. That also removes the hydration problem for free: the server snapshot is
 * always "system", which is what the un-stamped document renders as, so the first client
 * render matches and there is no flash of the wrong highlight.
 */
const listeners = new Set<() => void>();

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  // Another tab changing the preference should move this one too.
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

function getSnapshot(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    // Private modes throw on access; "system" is the correct fallback.
    return "system";
  }
}

function getServerSnapshot(): Theme {
  return "system";
}

function setTheme(next: Theme) {
  const root = document.documentElement;
  if (next === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", next);

  try {
    if (next === "system") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Preference won't survive a reload; the current page still updates.
  }
  listeners.forEach((notify) => notify());
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      className="flex items-center gap-0.5 rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-sunk)] p-0.5"
    >
      {OPTIONS.map(({ value, label, icon: Icon }) => {
        const active = theme === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={label}
            onClick={() => setTheme(value)}
            className={`rounded-md p-1.5 transition-colors ${
              active
                ? "bg-[var(--color-surface)] text-[var(--color-ink-primary)] shadow-[var(--shadow-panel)]"
                : "text-[var(--color-ink-muted)] hover:text-[var(--color-ink-secondary)]"
            }`}
          >
            <Icon size={14} strokeWidth={2.2} />
          </button>
        );
      })}
    </div>
  );
}
