"use client";

import {
  onIdTokenChanged,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { auth } from "@/lib/auth/firebase-client";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  idToken: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
    await signInWithEmailAndPassword(auth, email, password);
  }

  async function signOut() {
    await firebaseSignOut(auth);
  }

  return (
    <AuthContext.Provider value={{ user, loading, idToken, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
