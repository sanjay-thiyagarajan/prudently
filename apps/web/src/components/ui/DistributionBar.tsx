"use client";

import { motion } from "framer-motion";

const TONE_COLOR: Record<string, string> = {
  safe: "var(--color-safe)",
  ok: "var(--color-safe)",
  valid: "var(--color-safe)",
  elevated: "var(--color-elevated)",
  low: "var(--color-elevated)",
  expiring_soon: "var(--color-elevated)",
  critical: "var(--color-critical)",
  expired: "var(--color-critical)",
};

interface DistributionBarProps {
  label: string;
  counts: Record<string, number>;
  order: string[];
}

export function DistributionBar({ label, counts, order }: DistributionBarProps) {
  const total = order.reduce((sum, key) => sum + (counts[key] ?? 0), 0) || 1;

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="font-medium text-[var(--color-ink-secondary)]">{label}</span>
        <span className="text-[var(--color-ink-muted)]">{total} total</span>
      </div>
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-[var(--color-border-soft)]">
        {order.map((key) => {
          const count = counts[key] ?? 0;
          if (count === 0) return null;
          return (
            <motion.div
              key={key}
              initial={{ width: 0 }}
              animate={{ width: `${(count / total) * 100}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              style={{ backgroundColor: TONE_COLOR[key] ?? "var(--color-ink-muted)" }}
              title={`${key}: ${count}`}
            />
          );
        })}
      </div>
    </div>
  );
}
