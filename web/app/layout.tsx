import type { Metadata } from "next";
import { Fraunces, Inter, JetBrains_Mono, Source_Serif_4 } from "next/font/google";
import { DemoBadge } from "@/components/shell/DemoNotice";
import { THEME_SCRIPT } from "@/lib/theme";
import "./globals.css";

// The FYP1 type set (Arcana v1, web/app/layout.tsx @ 9a3d67f): Inter for text, Source Serif for asides, Fraunces for display.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const serif = Source_Serif_4({ subsets: ["latin"], variable: "--font-source-serif", display: "swap" });
const display = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains", display: "swap" });

export const metadata: Metadata = {
  title: "Synapse",
  description: "GraphRAG-powered generative UI platform for verified interactive learning",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="light"
      suppressHydrationWarning
      className={`${inter.variable} ${serif.variable} ${display.variable} ${mono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        {children}
        <DemoBadge />
      </body>
    </html>
  );
}
