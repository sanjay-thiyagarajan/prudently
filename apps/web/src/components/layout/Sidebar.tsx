"use client";

import {
  Activity,
  ClipboardCheck,
  ClipboardList,
  LogOut,
  Network,
  Package,
  Scissors,
  ShieldAlert,
  ShieldOff,
  Stethoscope,
  Truck,
  UserRound,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";

import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

// Grouped rather than one flat list: the previous 8-item run gave a manager no
// clue that "Fleet" and "Payroll" are different kinds of thing. The groups encode
// who each page is for — the fleet itself, the ward it runs, and the controls over
// both — which is also the order a demo walks them in.
const NAV_GROUPS: { heading: string; items: NavItem[] }[] = [
  {
    heading: "Fleet",
    items: [
      { href: "/", label: "Overview", icon: Network },
      { href: "/activity", label: "Autonomous activity", icon: Activity },
    ],
  },
  {
    heading: "Ward",
    items: [
      { href: "/staff", label: "Staff", icon: UserRound },
      { href: "/inventory", label: "Inventory", icon: Package },
      { href: "/vendors", label: "Vendors", icon: Truck },
      { href: "/admissions", label: "Admissions", icon: Stethoscope },
      { href: "/surgical-schedule", label: "Surgical scheduling", icon: Scissors },
      { href: "/job-sheets", label: "Job sheets", icon: ClipboardList },
      { href: "/payroll", label: "Payroll", icon: Wallet },
    ],
  },
  {
    heading: "Governance",
    items: [
      { href: "/approvals", label: "Approvals", icon: ClipboardCheck },
      { href: "/security", label: "Security & resilience", icon: ShieldAlert },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, signOut, signOutEverywhere } = useAuth();

  return (
    <aside className="sticky top-0 flex h-screen w-[236px] shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-bg-raised)]">
      <div className="flex items-center gap-2.5 px-5 pt-6 pb-7">
        <span
          aria-hidden
          className="flex size-7 items-center justify-center rounded-md bg-[var(--color-hero)] font-[family-name:var(--font-display)] text-sm font-bold text-[var(--color-bg-base)]"
          style={{ boxShadow: "var(--glow-hero)" }}
        >
          P
        </span>
        <div className="leading-tight">
          <p className="font-[family-name:var(--font-display)] text-[15px] font-semibold tracking-tight text-[var(--color-ink-primary)]">
            Prudently
          </p>
          <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-wide text-[var(--color-ink-muted)]">
            ward operations
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 pb-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.heading}>
            <p className="px-3 pb-2 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.16em] text-[var(--color-ink-muted)] uppercase">
              {group.heading}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const isActive =
                  item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={isActive ? "page" : undefined}
                    className={`relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors ${
                      isActive
                        ? "bg-[var(--color-hero-soft)] text-[var(--color-hero)]"
                        : "text-[var(--color-ink-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-ink-primary)]"
                    }`}
                  >
                    {isActive && (
                      <span className="absolute top-1.5 bottom-1.5 -left-3 w-[3px] rounded-r-full bg-[var(--color-hero)]" />
                    )}
                    <Icon size={16} strokeWidth={2} />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="space-y-3 border-t border-[var(--color-border-soft)] p-3">
        <ThemeToggle />
        {user && (
          <div>
            <p
              className="truncate px-1 pb-1.5 text-[11px] text-[var(--color-ink-muted)]"
              title={user.email ?? undefined}
            >
              {user.email}
            </p>
            <button
              type="button"
              onClick={() => signOut()}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium text-[var(--color-ink-secondary)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-ink-primary)]"
            >
              <LogOut size={16} strokeWidth={2} />
              Sign out
            </button>
            <button
              type="button"
              onClick={() => {
                if (window.confirm("Sign out everywhere? This ends every session for this account, on every device.")) {
                  signOutEverywhere();
                }
              }}
              title="Revoke every session for this account, not just this device"
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[12px] font-medium text-[var(--color-ink-muted)] transition-colors hover:bg-[var(--color-critical-soft)] hover:text-[var(--color-critical)]"
            >
              <ShieldOff size={15} strokeWidth={2} />
              Sign out everywhere
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
