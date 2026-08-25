"use client";

import { Loader2, TriangleAlert } from "lucide-react";

import { ArmorFeed } from "@/components/workspace/ArmorFeed";
import { ChaosReplay } from "@/components/workspace/ChaosReplay";
import { useDashboardOverview } from "@/lib/api/dashboard";

export default function SecurityPage() {
  const { data, error, isLoading } = useDashboardOverview();

  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
          Security & resilience
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Security & Resilience
        </h1>
        <p className="mt-2 max-w-lg text-sm text-[var(--color-ink-secondary)]">
          Threats the fleet has caught in incoming vendor messages (powered by Model Armor),
          and resilience drills that test how the fleet holds up under fault conditions.
        </p>
      </div>

      {isLoading ? (
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
      ) : error || !data ? (
        <div className="flex items-center gap-2 text-sm text-[var(--color-ink-secondary)]">
          <TriangleAlert className="text-[var(--color-critical)]" size={18} />
          Couldn&apos;t reach the Prudently API.
        </div>
      ) : (
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
          <ArmorFeed events={data.armor_events} />
          <ChaosReplay experiments={data.chaos_experiments} />
        </div>
      )}
    </main>
  );
}
