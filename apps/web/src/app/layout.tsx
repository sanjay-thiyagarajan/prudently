import type { Metadata } from "next";
import { Instrument_Sans, JetBrains_Mono } from "next/font/google";

import { AuthProvider } from "@/contexts/AuthContext";

import "./globals.css";

// Instrument Sans for everything the manager reads, JetBrains Mono for everything
// they compare: hours, stock counts, SKUs, trace IDs, timestamps. See globals.css
// for the reasoning behind the wider design language.
const instrument = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-instrument",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Prudently — Fortified Enterprise Fleet",
  description: "Agent-monitored hospital operations, live from the deployed agent fleet.",
};

// Runs before first paint so a manager who chose dark never sees a white flash on
// navigation. Deliberately inline and dependency-free: anything imported would run
// after hydration, which is exactly too late to prevent the flash. Wrapped in
// try/catch because localStorage throws outright in some privacy modes, and a
// theme preference is never worth breaking the page over.
const THEME_SCRIPT = `
try {
  var t = localStorage.getItem('prudently-theme');
  if (t === 'dark' || t === 'light') document.documentElement.setAttribute('data-theme', t);
} catch (e) {}
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${instrument.variable} ${jetbrains.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
