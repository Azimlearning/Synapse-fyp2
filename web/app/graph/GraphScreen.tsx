"use client";

// The Knowledge graph tab: the GraphRAG layer made visible. The most linked concepts across all the documents and the links among
// them (a solid line is a relation a document states, a dashed one only says two names occur in one sentence), drawn by the same
// NotesGraph block the notes use, at full size. Search narrows it to the concepts whose names match. Choosing a concept takes it
// to the Chat and asks about it there, so the graph is a way into the documents, not only a picture.

import type { ErrorEnvelope, UIBlock } from "@arcana/schema";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { NotesNav } from "@/components/genui/notesNav";
import { renderBlock } from "@/components/genui/registry";
import { AppNav } from "@/components/shell/AppNav";
import { fetchNotes } from "@/lib/api";

type View = { state: "loading" } | { state: "error"; error: ErrorEnvelope } | { state: "ready"; graph: UIBlock | null };

export function GraphScreen() {
  const router = useRouter();
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [view, setView] = useState<View>({ state: "loading" });

  useEffect(() => {
    const abort = new AbortController();
    void fetchNotes({ query }, { signal: abort.signal }).then((result) => {
      if (abort.signal.aborted) return;
      if (!result.ok) return setView({ state: "error", error: result.error });
      setView({ state: "ready", graph: result.workspace.blocks.find((b) => b.type === "NotesGraph") ?? null });
    });
    return () => abort.abort();
  }, [query]);

  const graph = view.state === "ready" ? view.graph : null;
  const nav = useMemo(
    () => ({
      openPage: (id: string) => {
        const node = graph?.type === "NotesGraph" ? graph.data.nodes.find((n) => n.id === id) : undefined;
        if (node) router.push(`/?ask=${encodeURIComponent(`What is ${node.label}?`)}`);
      },
    }),
    [graph, router],
  );

  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      <header className="flex items-center justify-between gap-4 border-b border-stone-200 bg-stone-50 px-6 py-3">
        <AppNav current="graph" />
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setView({ state: "loading" });
            setQuery(draft.trim());
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Find a concept (e.g. GraphRAG)"
            aria-label="Find a concept"
            maxLength={120}
            className="w-64 rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-stone-500"
          />
          <button type="submit" className="rounded-lg bg-stone-900 px-3 py-1.5 text-sm text-white">
            Find
          </button>
          {query && (
            <button
              type="button"
              onClick={() => {
                setDraft("");
                setView({ state: "loading" });
                setQuery("");
              }}
              className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm text-stone-700"
            >
              Whole corpus
            </button>
          )}
        </form>
      </header>
      <main className="mx-auto max-w-6xl space-y-4 p-6">
        <div>
          <h1 className="font-display text-2xl font-semibold">
            Knowledge graph<span className="nb-aside">{query ? `concepts matching "${query}"` : "the whole corpus"}</span>
          </h1>
          <p className="mt-1 text-sm text-stone-600">
            Built from your documents when they were added: every concept and link here comes from a sentence in a paper. Choose a
            concept to ask about it in the Chat.
          </p>
        </div>
        {view.state === "loading" && (
          <p role="status" aria-busy="true" className="text-sm text-stone-500">
            Reading the graph…
          </p>
        )}
        {view.state === "error" && (
          <p role="alert" className="text-sm text-red-700">
            {view.error.message}
          </p>
        )}
        {view.state === "ready" &&
          (graph ? (
            <NotesNav.Provider value={nav}>{renderBlock(graph)}</NotesNav.Provider>
          ) : (
            <p className="font-serif text-sm italic text-stone-500">No concept matches that name.</p>
          ))}
      </main>
    </div>
  );
}
