"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface PanelProps {
  title: string;
  icon?: LucideIcon;
  accent?: string;
  live?: boolean;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * The board's basic card. Mount-triggered animation, not `whileInView` — the scroll-trigger
 * silently never fires for below-the-fold content in some capture paths, which cost this
 * project a screenshot pass once already.
 */
export function Panel({
  title,
  icon: Icon,
  accent = "var(--color-hero)",
  live = false,
  subtitle,
  action,
  children,
  className = "",
}: PanelProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={`flex h-full flex-col overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-panel)] ${className}`}
    >
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--color-border-soft)] px-4 py-3">
        <div className="flex min-w-0 items-center gap-2.5">
          {Icon && (
            <span
              aria-hidden
              className="flex size-7 shrink-0 items-center justify-center rounded-md"
              style={{ backgroundColor: `${accent}1a`, color: accent }}
            >
              <Icon size={15} strokeWidth={2.1} />
            </span>
          )}
          <div className="min-w-0">
            <h2 className="truncate font-[family-name:var(--font-display)] text-[13px] font-semibold tracking-tight text-[var(--color-ink-primary)]">
              {title}
            </h2>
            {subtitle && (
              <p className="truncate text-[11px] text-[var(--color-ink-muted)]">{subtitle}</p>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {action}
          {live && (
            <span className="flex items-center gap-1.5 font-[family-name:var(--font-mono)] text-[10px] tracking-wide text-[var(--color-ink-muted)] uppercase">
              <span
                className="size-1.5 rounded-full bg-[var(--color-safe)] [animation:var(--animate-pulse-slow)]"
                style={{ boxShadow: "var(--glow-safe)" }}
              />
              live
            </span>
          )}
        </div>
      </header>
      <div className="flex-1 p-4">{children}</div>
    </motion.section>
  );
}

/** Consistent empty state — an empty panel must say why it is empty, never just sit blank. */
export function PanelEmpty({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full min-h-[88px] items-center justify-center rounded-lg border border-dashed border-[var(--color-border)] px-4 py-6 text-center text-[12px] leading-relaxed text-[var(--color-ink-muted)]">
      {children}
    </div>
  );
}
