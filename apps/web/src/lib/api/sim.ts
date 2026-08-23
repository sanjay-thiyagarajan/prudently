"use client";

import useSWR from "swr";

import type { SimStatus } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Faster than the dashboard's 4s: the clock is the one thing on screen a viewer expects to
// respond immediately to a button press, and a stale "paused" pill after hitting Start reads
// as a broken control rather than a slow poll.
const POLL_INTERVAL_MS = 2000;

async function getStatus(url: string): Promise<SimStatus> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Sim status failed: ${response.status}`);
  return response.json();
}

export function useSimStatus() {
  const { data, error, isLoading, mutate } = useSWR<SimStatus>(
    `${API_BASE_URL}/sim/status`,
    getStatus,
    { refreshInterval: POLL_INTERVAL_MS, revalidateOnFocus: false, keepPreviousData: true },
  );
  return { status: data, error, isLoading: isLoading && !data, refresh: mutate };
}

export type SimCommand = "start" | "pause" | "reset" | "advance";

export async function sendSimCommand(command: SimCommand): Promise<SimStatus> {
  const response = await fetch(`${API_BASE_URL}/sim/${command}`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Sim ${command} failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
