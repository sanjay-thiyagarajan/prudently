"use client";

import {
  onIdTokenChanged,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { auth } from "@/lib/auth/firebase-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// docs/threat-model.md finding 5: a standard clinical-system expectation, and cheap to add —
// an unattended signed-in tab stays a live session with no forcing function to end it otherwise.
const IDLE_TIMEOUT_MS = 15 * 60 * 1000;
const ACTIVITY_EVENTS = ["mousedown", "keydown", "touchstart", "scroll"] as const;

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  idToken: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  signOutEverywhere: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // onIdTokenChanged (not onAuthStateChanged): also fires on Firebase's automatic token
    // refresh, so idToken never goes stale mid-session for the policy-editor's fetch calls.
    return onIdTokenChanged(auth, async (nextUser) => {
      setUser(nextUser);
      setIdToken(nextUser ? await nextUser.getIdToken() : null);
      setLoading(false);
    });
  }, []);

  async function signIn(email: string, password: string) {
    // Sign-in only — deliberately no self-service account creation here. This platform is
    // not meant for public use (per the user's own requirement); a create-on-failure fallback
    // would turn the login form into a public sign-up form for anyone who finds the URL.
    // Accounts (the one demo/judge account) are provisioned by hand in the Firebase Console.
    const credential = await signInWithEmailAndPassword(auth, email, password);
    // Force-refresh rather than trust the token sign-in minted: scripts/set_user_role.py
    // (apps/api) can be run against an account that's mid-session elsewhere or was just
    // created moments earlier, and Firebase only guarantees a fresh mint carries the very
    // latest custom claims when no cached token exists yet. Cheap (one extra round trip, only
    // on sign-in) and removes any doubt that require_role("admin", "clinician") 403s a judge
    // whose role claim was set correctly but whose token just hadn't picked it up yet.
    await credential.user.getIdToken(true);
  }

  async function signOut() {
    await firebaseSignOut(auth);
  }

  async function signOutEverywhere() {
    // Server-side revocation (routes/auth.py) first, then the local sign-out — the order
    // matters: revoking after the local token is already cleared would need a fresh token to
    // authenticate the revoke call, which defeats the point.
    if (idToken) {
      try {
        await fetch(`${API_BASE_URL}/auth/sign-out-everywhere`, {
          method: "POST",
          headers: { Authorization: `Bearer ${idToken}` },
        });
      } catch {
        // Best-effort — a network failure here must not block the local sign-out the user
        // asked for; they still end up signed out on this device either way.
      }
    }
    await firebaseSignOut(auth);
  }

  // Idle timeout: resets on any real user activity, fires signOut() after IDLE_TIMEOUT_MS of
  // none. Only armed while actually signed in — no timer running (and no listeners attached)
  // for an anonymous viewer of the public feeds.
  useEffect(() => {
    if (!user) return undefined;

    function resetTimer() {
      if (idleTimer.current) clearTimeout(idleTimer.current);
      idleTimer.current = setTimeout(() => {
        firebaseSignOut(auth);
      }, IDLE_TIMEOUT_MS);
    }

    resetTimer();
    ACTIVITY_EVENTS.forEach((event) => window.addEventListener(event, resetTimer));
    return () => {
      if (idleTimer.current) clearTimeout(idleTimer.current);
      ACTIVITY_EVENTS.forEach((event) => window.removeEventListener(event, resetTimer));
    };
  }, [user]);

  return (
    <AuthContext.Provider value={{ user, loading, idToken, signIn, signOut, signOutEverywhere }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
