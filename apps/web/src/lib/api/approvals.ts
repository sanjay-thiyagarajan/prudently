"use client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** The in-app equivalent of clicking the approve/reject link in the email — POST
 * /approvals/{id}/resolve (routes/approvals.py), require_firebase_auth-gated, same
 * `resolve_approval()` underneath. Not a hook: called from a click handler, same "discrete
 * action, caller manages its own loading state" shape as surgicalSchedule.ts's
 * updateCaseStatus/notifyPatient. */
export async function resolveApproval(
  idToken: string,
  approvalId: string,
  decision: "approved" | "rejected",
): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/approvals/${encodeURIComponent(approvalId)}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${idToken}` },
    body: JSON.stringify({ decision }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Resolve failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
