"use client";

import { motion } from "framer-motion";
import { AlertTriangle, ShieldAlert, ShieldCheck, ShieldOff } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import type { ArmorEvent } from "@/lib/types/dashboard";

function relativeTime(iso: string): string {
  const deltaMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(deltaMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function EventRow({ event }: { event: ArmorEvent }) {
  // service_error must never render the same as a real block — a fail-closed Model Armor
  // outage is not a security win.
  const isOutage = event.service_error;
  const isBlocked = event.status === "blocked" && !isOutage;

  const Icon = isOutage ? AlertTriangle : isBlocked ? ShieldAlert : ShieldCheck;
  const color = isOutage
    ? "var(--color-elevated)"
    : isBlocked
      ? "var(--color-critical)"
      : "var(--color-safe)";
  const label = isOutage ? "Armor unavailable" : isBlocked ? "Blocked" : "Accepted";

  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className="rounded-xl border border-[var(--color-border-soft)] p-3.5"
    >
      <div className="flex items-start gap-3">
        <span
          className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg"
          style={{ backgroundColor: `${color}20`, color }}
        >
          <Icon size={15} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-sm font-medium text-[var(--color-ink-primary)]">
              {event.vendor_name}
            </p>
            <span
              className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase"
              style={{ backgroundColor: `${color}20`, color }}
            >
              {label}
            </span>
          </div>
          <p className="mt-1 line-clamp-2 text-xs text-[var(--color-ink-secondary)]">
            &ldquo;{event.message}&rdquo;
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-[var(--color-ink-muted)]">
            <span>{relativeTime(event.timestamp)}</span>
            {event.matched_filters.length > 0 && (
              <span className="font-mono">{event.matched_filters.join(", ")}</span>
            )}
            <span
              className="rounded px-1.5 py-0.5"
              style={{
                backgroundColor:
                  event.source === "cloud_run_a2a_mount"
                    ? "var(--color-a2a-soft)"
                    : "var(--color-border-soft)",
                color:
                  event.source === "cloud_run_a2a_mount"
                    ? "var(--color-a2a)"
                    : "var(--color-ink-muted)",
              }}
            >
              {event.source === "cloud_run_a2a_mount" ? "A2A demo path" : "standalone engine"}
            </span>
          </div>
        </div>
      </div>
    </motion.li>
  );
}

export function ArmorFeed({ events }: { events: ArmorEvent[] }) {
  return (
    <Panel title="Model Armor" icon={ShieldAlert} live>
      {events.length === 0 ? (
        <div className="flex h-full min-h-[220px] flex-col items-center justify-center gap-2 text-center">
          <ShieldOff size={28} className="text-[var(--color-ink-muted)]" />
          <p className="text-sm text-[var(--color-ink-secondary)]">
            No vendor communications screened yet.
          </p>
          <p className="text-xs text-[var(--color-ink-muted)]">
            Medical Representative screens every inbound message the moment one arrives.
          </p>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {events.map((event, index) => (
            <EventRow key={`${event.timestamp}-${index}`} event={event} />
          ))}
        </ul>
      )}
    </Panel>
  );
}
