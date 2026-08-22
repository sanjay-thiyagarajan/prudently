"use client";

import type { ReactNode } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Sidebar } from "@/components/layout/Sidebar";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1">{children}</div>
      </div>
    </RequireAuth>
  );
}
