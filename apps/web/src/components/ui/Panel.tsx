"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface PanelProps {
  title: string;
  icon: LucideIcon;
  accent?: string;
  live?: boolean;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}

export function Panel({
  title,
  icon: Icon,
  accent = "var(--color-hero)",
  live = false,
  subtitle,
  children,
  className = "",
}: PanelProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={`relative flex h-full flex-col overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/80 backdrop-blur-sm ${className}`}
    >
      <div
        className="absolute inset-x-0 top-0 h-px opacity-60"
        style={{ background: `linear-gradient(90deg, transparent, ${accent}, transparent)` }}
      />
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--color-border-soft)] px-5 py-4">
        <div className="flex items-center gap-3">
          <span
            className="flex size-9 shrink-0 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${accent}1f`, color: accent }}
          >
            <Icon size={18} strokeWidth={2} />
          </span>
          <div>
            <h2 className="font-[family-name:var(--font-display)] text-sm font-semibold tracking-wide text-[var(--color-ink-primary)] uppercase">
              {title}
            </h2>
            {subtitle && <p className="text-xs text-[var(--color-ink-muted)]">{subtitle}</p>}
          </div>
        </div>
        {live && (
          <span className="flex items-center gap-1.5 text-[10px] font-medium tracking-wider text-[var(--color-safe)] uppercase">
            <span className="relative flex size-1.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-[var(--color-safe)] opacity-75" />
              <span className="relative inline-flex size-1.5 rounded-full bg-[var(--color-safe)]" />
            </span>
            live
          </span>
        )}
      </header>
      <div className="flex-1 p-5">{children}</div>
    </motion.section>
  );
}
