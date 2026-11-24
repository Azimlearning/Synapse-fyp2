// The product header shared by every screen: the Synapse wordmark and the views. "Simulations" is the generative UI side of
// Synapse (interactive, browser-verified simulations), served by the Synapse simulation app and shown inside this shell.

import Link from "next/link";
import type { ReactNode } from "react";

import { Axi } from "./Axi";
import { ThemeSwitch } from "./ThemeSwitch";

export type ViewId = "chat" | "graph" | "notes" | "review" | "labs" | "simulations";

const VIEWS: { id: ViewId; href: string; label: string }[] = [
  { id: "chat", href: "/", label: "Chat" },
  // One tab for the knowledge graph and the notes built from it (the concept graph, each concept's page, quiz and review); the
  // full-page graph at /graph is still there for a link from the Chat.
  { id: "notes", href: "/notes", label: "Knowledge graph" },
];

const ON = "rounded-full bg-white px-3 py-1 font-medium text-stone-900 shadow-[0_1px_2px_rgba(35,33,28,0.08),0_0_0_1px_var(--color-stone-200)]";
const OFF = "rounded-full px-3 py-1 text-stone-600 hover:text-stone-900";

/** The wordmark and the view links. `extra` adds links after the views (the notes screens add Review). */
export function AppNav({ current, extra }: { current: ViewId; extra?: ReactNode }) {
  return (
    <div className="flex items-center gap-4">
      <Link href="/" className="flex items-center gap-2" aria-label="Synapse home">
        <Axi size={36} />
        <span className="font-display text-[1.65rem] font-semibold leading-none tracking-tight text-stone-900">Synapse</span>
        <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-accent" />
        <span className="hidden pt-1 font-serif text-sm italic text-stone-500 lg:inline">the graph-grounded notebook</span>
      </Link>
      <nav aria-label="Views" className="ml-2 flex gap-1 rounded-full border border-stone-200 bg-stone-50 p-0.5 text-sm">
        {VIEWS.map((v) => (
          <Link key={v.id} href={v.href} aria-current={current === v.id ? "page" : undefined} className={current === v.id ? ON : OFF}>
            {v.label}
          </Link>
        ))}
        {extra}
      </nav>
      <ThemeSwitch />
    </div>
  );
}

export function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link href={href} aria-current={active ? "page" : undefined} className={active ? ON : OFF}>
      {label}
    </Link>
  );
}
