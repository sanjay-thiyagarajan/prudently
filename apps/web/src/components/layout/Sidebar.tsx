"use client";

import {
  ClipboardCheck,
  LogOut,
  Network,
  ShieldAlert,
  Stethoscope,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";

const NAV_ITEMS: { href: string; label: string; icon: LucideIcon }[] = [
  { href: "/", label: "Fleet", icon: Network },
  { href: "/payroll", label: "Payroll", icon: Wallet },
  { href: "/admissions", label: "Admissions", icon: Stethoscope },
  { href: "/security", label: "Security & Resilience", icon: ShieldAlert },
  { href: "/approvals", label: "Approvals", icon: ClipboardCheck },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, signOut } = useAuth();

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-sm">
      <div className="flex items-center gap-2 px-5 py-6">
        <span className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-[var(--color-hero)] opacity-75" />
          <span className="relative inline-flex size-2 rounded-full bg-[var(--color-hero)]" />
        </span>
        <span className="font-[family-name:var(--font-display)] text-base font-bold text-[var(--color-ink-primary)]">
          Prudently
        </span>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-[var(--color-hero-soft)] text-[var(--color-hero)]"
                  : "text-[var(--color-ink-secondary)] hover:bg-[var(--color-border-soft)] hover:text-[var(--color-ink-primary)]"
              }`}
            >
              <Icon size={17} strokeWidth={2} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {user && (
        <div className="border-t border-[var(--color-border-soft)] p-3">
          <button
            type="button"
            onClick={() => signOut()}
            title={user.email ?? "Sign out"}
            className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium text-[var(--color-ink-muted)] transition-colors hover:bg-[var(--color-border-soft)] hover:text-[var(--color-ink-primary)]"
          >
            <LogOut size={17} strokeWidth={2} />
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
