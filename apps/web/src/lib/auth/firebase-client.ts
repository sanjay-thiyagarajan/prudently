"use client";

import { getApps, initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Firebase web config values are designed to be public by Google's own model (they identify
// the project, they don't authorize anything on their own) — hardcoded defaults here follow
// this repo's established NEXT_PUBLIC_* pattern (see Dockerfile's ARG/ENV block): inlined at
// `next build` time, not read at container runtime, so a Terraform/Cloud-Run env var would be
// inert for the same reason NEXT_PUBLIC_API_BASE_URL's Terraform env{} block is (see AGENTS.md).
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY ?? "AIzaSyAv71Sf18UXwwt1BH0kWtx4VmaBNFwkI4A",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN ?? "prudently-hackathon.firebaseapp.com",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ?? "prudently-hackathon",
  appId:
    process.env.NEXT_PUBLIC_FIREBASE_APP_ID ??
    "1:439570031916:web:5b263c08f9ba2493abb889",
};

const app = getApps().length > 0 ? getApps()[0]! : initializeApp(firebaseConfig);

export const auth = getAuth(app);
