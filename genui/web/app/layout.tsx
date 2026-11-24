// Ported from Synapse v3: frontend/app/layout.tsx (Genui monorepo, commit 835a2cefda28). Read in full and adapted: the same three self-hosted faces through
// next/font (fetched at build time, served from this origin; no runtime CDN), the same set-the-theme-before-first-paint script, and the CSS variable names
// changed to `--face-*` so the Tailwind 4 theme in globals.css can map them without referring to itself.
import type { Metadata, Viewport } from "next";
import { Fredoka, JetBrains_Mono, Nunito } from "next/font/google";
import type { ReactNode } from "react";
import { LangProvider } from "../lib/i18n";
import "./globals.css";

const display = Fredoka({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--face-display", display: "swap" });
const sans = Nunito({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--face-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--face-mono", display: "swap" });

export const metadata: Metadata = {
  title: "Synapse",
  description: "Verified, interactive science simulations.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

// A saved choice wins, else the system preference. The top-bar toggle updates both. Wrapped in try: storage can be blocked, and then the system setting stands.
// Inside the Synapse workspace (?embed=1) the host page owns the colour mode: it passes ?theme= (light unless it says dark) and
// later changes arrive by message (see TopBar). Standalone, the remembered choice or the system preference applies as before.
const themeScript = `try{var q=new URLSearchParams(location.search),t;if(q.get('embed')==='1'){t=q.get('theme')==='dark'?'dark':'light';document.documentElement.dataset.embed='1';}else{t=localStorage.getItem('synapse-theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}}document.documentElement.dataset.theme=t;}catch(e){}`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      {/* Browser extensions (Grammarly and others) add attributes to <body> before React loads; this silences only that one-level attribute mismatch. */}
      <body className="min-h-screen font-sans antialiased" suppressHydrationWarning>
        <LangProvider>{children}</LangProvider>
      </body>
    </html>
  );
}
