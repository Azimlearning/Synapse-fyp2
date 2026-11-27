// The history UI, as chat assistants lay it out. `ChatList`: a New chat button and the chats grouped by when they were last used
// (Today, Yesterday, ...), the open one marked, each with rename and delete. `StudioList`: every Studio output across the chats
// ("Previous studios"). Both open what was kept, exactly as it was, with no server call (lib/history.ts).

"use client";

import { useState } from "react";

import { groupChats, topicOf, type Conversation, type Turn } from "@/lib/history";

function when(at: number): string {
  const d = new Date(at);
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return new Date().toDateString() === d.toDateString() ? time : `${d.toLocaleDateString([], { day: "numeric", month: "short" })} ${time}`;
}

export function ChatList({
  chats,
  activeId,
  busy,
  onNew,
  onOpen,
  onRename,
  onDelete,
}: {
  chats: Conversation[];
  activeId: string | null;
  busy: boolean;
  onNew: () => void;
  onOpen: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  return (
    <section aria-label="Chats" className="space-y-2">
      <div className="flex items-baseline justify-between">
        <h2 className="nb-label">
          Chats<span className="nb-aside">kept in this browser</span>
        </h2>
      </div>
      <button
        type="button"
        onClick={onNew}
        disabled={busy}
        data-tour="newchat"
        className="flex w-full items-center gap-2 rounded-xl bg-white px-3 py-2 text-sm font-medium text-stone-900 shadow-[0_0_0_1px_var(--color-stone-300)] hover:shadow-[0_0_0_1px_var(--color-stone-500)] disabled:opacity-50"
      >
        <span aria-hidden className="text-base leading-none">+</span> New chat
      </button>
      {chats.length === 0 ? (
        <p className="px-1 font-serif text-sm italic text-stone-500">Your chats will appear here.</p>
      ) : (
        <div data-tour="chats" className="max-h-[34vh] space-y-3 overflow-y-auto pr-1">
          {groupChats(chats).map((g) => (
            <div key={g.label}>
              <p className="px-1 pb-1 text-[11px] font-semibold uppercase tracking-wide text-stone-500">{g.label}</p>
              <ul className="space-y-0.5 text-sm">
                {g.chats.map((c) => {
                  const active = c.id === activeId;
                  return (
                    <li
                      key={c.id}
                      className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 ${active ? "bg-stone-200/70" : "hover:bg-stone-100"}`}
                    >
                      {editing === c.id ? (
                        <form
                          className="min-w-0 flex-1"
                          onSubmit={(e) => {
                            e.preventDefault();
                            onRename(c.id, draft);
                            setEditing(null);
                          }}
                        >
                          <input
                            autoFocus
                            value={draft}
                            onChange={(e) => setDraft(e.target.value)}
                            onBlur={() => {
                              onRename(c.id, draft);
                              setEditing(null);
                            }}
                            onKeyDown={(e) => e.key === "Escape" && setEditing(null)}
                            aria-label="Chat name"
                            className="w-full rounded border border-stone-300 bg-white px-1.5 py-0.5 text-sm outline-none"
                          />
                        </form>
                      ) : (
                        <button
                          type="button"
                          disabled={busy}
                          aria-current={active ? "true" : undefined}
                          onClick={() => onOpen(c.id)}
                          title={`${c.title} (${c.turns.length} ${c.turns.length === 1 ? "turn" : "turns"})`}
                          className={`min-w-0 flex-1 truncate text-left disabled:opacity-50 ${active ? "font-medium text-stone-900" : "text-stone-700"}`}
                        >
                          {c.title}
                        </button>
                      )}
                      {editing !== c.id && (
                        <span className={`flex shrink-0 gap-0.5 ${active ? "" : "opacity-0 group-hover:opacity-100 focus-within:opacity-100"}`}>
                          <button
                            type="button"
                            aria-label={`Rename: ${c.title}`}
                            onClick={() => {
                              setDraft(c.title);
                              setEditing(c.id);
                            }}
                            className="rounded px-1 text-xs text-stone-500 hover:text-stone-900"
                          >
                            ✎
                          </button>
                          <button
                            type="button"
                            aria-label={`Delete: ${c.title}`}
                            onClick={() => {
                              if (window.confirm(`Delete "${c.title}"?`)) onDelete(c.id);
                            }}
                            className="rounded px-1 text-stone-500 hover:text-stone-900"
                          >
                            ×
                          </button>
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function StudioList({
  items,
  busy,
  onOpen,
  onDelete,
}: {
  items: { chatId: string; turn: Turn }[];
  busy: boolean;
  onOpen: (chatId: string, turnId: string) => void;
  onDelete: (chatId: string, turnId: string) => void;
}) {
  return (
    <section aria-label="Previous studios" data-tour="studio-history" className="flex flex-col gap-2 md:min-h-0 md:flex-1">
      <h2 className="nb-label shrink-0 border-b border-stone-200 pb-2">
        Previous studios ({items.length})<span className="nb-aside">every Studio output</span>
      </h2>
      {items.length === 0 ? (
        <p className="font-serif text-sm italic text-stone-500">Nothing yet. Every quiz, flashcard set, brief or draft the Studio makes is kept here.</p>
      ) : (
        <ul className="space-y-1.5 overflow-y-auto text-sm max-md:max-h-[40vh] md:min-h-0 md:flex-1">
          {items.map(({ chatId, turn }) => (
            <li key={turn.id} className="group flex items-start gap-2 rounded-lg bg-white px-2.5 py-2 shadow-[0_0_0_1px_var(--color-stone-200)]">
              <button
                type="button"
                disabled={busy}
                onClick={() => onOpen(chatId, turn.id)}
                className="min-w-0 flex-1 text-left disabled:opacity-50"
                title="Show it again (no new model call)"
              >
                <span className="mr-1.5 font-medium text-stone-900">{turn.tool}</span>
                <span className="text-stone-600">{topicOf(turn)}</span>
                <span className="block font-serif text-xs italic text-stone-500">{when(turn.at)}</span>
              </button>
              <button
                type="button"
                aria-label={`Remove: ${turn.question}`}
                onClick={() => onDelete(chatId, turn.id)}
                className="shrink-0 px-1 text-stone-400 opacity-0 hover:text-stone-900 group-hover:opacity-100 focus:opacity-100"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
