import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";

import { AuthProvider } from "@/contexts/AuthContext";

import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Prudently — Fortified Enterprise Fleet",
  description: "Agent-monitored hospital operations fleet, live from the deployed agent fleet.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${inter.variable}`}>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
