"use client";

// The workspace. It opens on the prebuilt Basic layout with the list of the user's sources (fetched from `/workspace`;
// a fixed fallback layout stands in until then, or if that fails), and an adaptive layout composed for the answer is
// layered on top of it (D-28). The frame, the panels and the switch are in `components/shell`; what each panel holds
// is decided by the layout (`placeBlocks`). Every block goes through the registry: this component never inspects a
// block's content.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ErrorEnvelope, PanelId, RegionId, UIBlock } from "@arcana/schema";

import { renderBlock } from "@/components/genui/registry";
import { AppNav } from "@/components/shell/AppNav";
import { LayoutSwitch } from "@/components/shell/LayoutSwitch";
import { SaveView, type SaveOutcome } from "@/components/shell/SaveView";
import { SavedViews, refusalWords } from "@/components/shell/SavedViews";
import { PaneSeparator, Panes } from "@/components/shell/Panes";
import { Shell } from "@/components/shell/Shell";
import { STARTERS, Studio } from "@/components/shell/Studio";
import { DemoSuggestions } from "@/components/shell/DemoNotice";
import { TracePanel } from "@/components/TracePanel";
import { deleteDocument, deletePattern, fetchNotes, fetchWorkspace, listPatterns, reverifyPattern, savePattern, uploadPdf } from "@/lib/api";
import { flattenPlaced, placeBlocksByRegion } from "@/lib/layout";
import { blockTitle } from "@/lib/tables";
import { streamApply, streamChat } from "@/lib/stream";
import { activeLayout, useWorkspace } from "@/lib/store";
import {
  activeChat,
  addSimulationTurn,
  addTurn,
  deleteChat,
  deleteTurn,
  loadChats,
  renameChat,
  setActiveChat,
  type Conversation,
  type Turn,
} from "@/lib/history";
import { ChatList, StudioList } from "@/components/shell/HistoryList";
import { Axi } from "@/components/shell/Axi";
import {
  SimulationCard,
  SimulationDrawer,
  SimulationLauncher,
  type DrawerRequest,
  type ReadySimulation,
} from "@/components/shell/SimulationDrawer";

/** The topic a Studio tool runs on when none is typed: the concept the most papers share, then the best connected (most links).
 *  Read once per page load; "the documents" when there are no notes. */
let topicCache: string | null = null;
async function defaultTopic(): Promise<string> {
  if (topicCache) return topicCache;
  const result = await fetchNotes();
  const graph = result.ok ? result.workspace.blocks.find((b) => b.type === "NotesGraph") : undefined;
  const nodes = graph && graph.type === "NotesGraph" && graph.meta.status === "ready" ? graph.data.nodes : [];
  const best = [...nodes].sort((a, b) => b.documents - a.documents || b.degree - a.degree)[0];
  topicCache = best?.label ?? "the documents";
  return topicCache;
}

/** The asker's question, on the right, as chat assistants draw it. */
function QuestionBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <p className="max-w-[80%] rounded-2xl rounded-br-md bg-stone-200/70 px-4 py-2 text-[15px] text-stone-900">{text}</p>
    </div>
  );
}

/** A simulation kept in the chat: the engine's short note as an ordinary chat message, then the card holding only the simulation. */
function SimulationTurn({ sim }: { sim: { envId: string; title: string; note?: string; label?: string } }) {
  return (
    <div className="space-y-3">
      {sim.note?.trim() && (
        <div className="flex gap-3 rounded-2xl bg-white p-4 shadow-[0_1px_2px_rgba(35,33,28,0.06),0_0_0_1px_var(--color-stone-200)]">
          <Axi size={30} />
          <div className="min-w-0">
            <p className="nb-label">Quick study note</p>
            <p className="mt-1 whitespace-pre-wrap font-serif text-[15px] leading-relaxed text-stone-800">{sim.note.trim()}</p>
          </div>
        </div>
      )}
      <SimulationCard envId={sim.envId} title={sim.title} label={sim.label} />
    </div>
  );
}

/** Document tile colours, from the FYP1 notebook design (a source's kind badge). */
const DOC_TILES = ["bg-[#2f5fa8]", "bg-[#3d7a52]", "bg-[#9a6b18]", "bg-[#6a4ea8]", "bg-[#a8423a]"];

export function Workspace() {
  const { documents, order, blocks, workspaceBlocks, layouts, layoutChoice, turn, turnError, patterns, panes, paneShare, paneFocus } =
    useWorkspace();
  const centre = useRef<HTMLDivElement | null>(null);
  const [question, setQuestion] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<ErrorEnvelope | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [staleId, setStaleId] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  // Chats, as chat assistants keep them (lib/history.ts): the list, the open chat, which of its turns the workspace is showing
  // (null while a new answer streams), and the question above the current answer.
  const [chats, setChats] = useState<Conversation[]>([]);
  const [chatId, setChatId] = useState<string | null>(null);
  const chatRef = useRef<string | null>(null);
  const [shownTurnId, setShownTurnId] = useState<string | null>(null);
  const [asked, setAsked] = useState<string | null>(null);
  /** A simulation being built in the chat from a question (null when none). */
  const [liveSim, setLiveSim] = useState<{ question: string; nonce: number } | null>(null);
  // Like a chat assistant: opening a chat or asking scrolls to the latest question, with the earlier ones above it.
  const currentQuestion = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (asked) currentQuestion.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }, [asked, shownTurnId]);

  const openChat = useCallback((id: string, turnId?: string) => {
    if (useWorkspace.getState().turn === "streaming") return;
    const chat = loadChats().find((c) => c.id === id);
    const turn = chat && (turnId ? chat.turns.find((t) => t.id === turnId) : chat.turns[chat.turns.length - 1]);
    if (!chat || !turn) return;
    abort.current?.abort();
    useWorkspace.getState().restoreTurn({ blocks: turn.blocks, adaptive: turn.adaptive });
    setLiveSim(null);
    chatRef.current = chat.id;
    setChatId(chat.id);
    setActiveChat(chat.id);
    setShownTurnId(turn.id);
    setAsked(turn.question);
    setQuestion("");
  }, []);

  const newChat = useCallback(() => {
    if (useWorkspace.getState().turn === "streaming") return;
    abort.current?.abort();
    useWorkspace.getState().restoreTurn({ blocks: [], adaptive: null });
    setLiveSim(null);
    chatRef.current = null;
    setChatId(null);
    setActiveChat(null);
    setShownTurnId(null);
    setAsked(null);
    setQuestion("");
  }, []);

  useEffect(() => {
    // Browser storage is only readable after mount: the chats, and the chat that was open (reopened as it was left).
    const all = loadChats();
    setChats(all); // eslint-disable-line react-hooks/set-state-in-effect -- browser storage is only readable after mount
    const open = activeChat();
    if (open && all.some((c) => c.id === open)) openChat(open);
  }, [openChat]);

  const loadWorkspace = useCallback(async () => {
    const result = await fetchWorkspace();
    if (result.ok) useWorkspace.getState().setWorkspace(result.workspace);
    // If it fails the fallback layout stays and the sources panel shows only what was uploaded in this session.
  }, []);

  const loadPatterns = useCallback(async () => {
    const result = await listPatterns();
    if (result.ok) useWorkspace.getState().setPatterns(result.patterns);
  }, []);

  useEffect(() => {
    void loadWorkspace();
    void loadPatterns();
  }, [loadWorkspace, loadPatterns]);

  // Show a saved view again. It streams like an answer (so it goes through the same block and layout path) but asks
  // no question and calls no model; a refusal arrives as an error and shows nothing.
  const showView = useCallback(async (id: string) => {
    if (useWorkspace.getState().turn === "streaming") return;
    setSavedMessage(null);
    setStaleId(null);
    abort.current?.abort();
    abort.current = new AbortController();
    useWorkspace.getState().startTurn();
    await streamApply(
      id,
      {
        onBlock: (block) => useWorkspace.getState().upsertBlock(block),
        onLayout: (next) => useWorkspace.getState().setLayout(next),
        onError: (error) => {
          useWorkspace.getState().finishTurn();
          setSavedMessage(refusalWords(error));
          // A view whose layout moved on can be checked again; any other refusal is final until the documents change.
          if (error.code === "pattern_refused" && error.issues[0]?.path === "template_changed") setStaleId(id);
        },
        onDone: () => {
          useWorkspace.getState().finishTurn();
          void loadPatterns(); // its use count moved
        },
      },
      { signal: abort.current.signal },
    );
  }, [loadPatterns]);

  const checkAgain = useCallback(
    async (id: string) => {
      setSavedMessage(null);
      setStaleId(null);
      const result = await reverifyPattern(id);
      if (!result.ok) {
        setSavedMessage(refusalWords(result.error));
        return;
      }
      await loadPatterns();
      await showView(id); // it is current now: show it
    },
    [loadPatterns, showView],
  );

  const removeView = useCallback(
    async (id: string) => {
      setSavedMessage(null);
      const result = await deletePattern(id);
      if (!result.ok) setSavedMessage(result.error.message);
      await loadPatterns();
    },
    [loadPatterns],
  );

  // Simulations run IN the chat (generative UI). "Simulate" beside Ask, or a pick from the drawer of prebuilt ones, starts one as the
  // chat's next turn; when the engine reports it ready it is kept as a turn of the open chat (and listed under Previous studios).
  const [drawer, setDrawer] = useState<DrawerRequest | null>(null);
  const runSim = useCallback((q: string | null) => {
    const text = (q ?? "").trim().replace(/^Simulate:\s*/i, "");
    if (!text) {
      setDrawer({ kind: "picker" }); // no question: offer the prebuilt ones
      return;
    }
    if (useWorkspace.getState().turn === "streaming") return;
    setDrawer(null);
    abort.current?.abort();
    useWorkspace.getState().restoreTurn({ blocks: [], adaptive: null });
    setShownTurnId(null); // the chat's turns so far stay above it as the thread
    setAsked(`Simulate: ${text}`);
    setQuestion("");
    setLiveSim({ question: text, nonce: Date.now() });
  }, []);
  const onSimReady = useCallback((sim: ReadySimulation) => {
    const saved = addSimulationTurn(chatRef.current, `Simulate: ${sim.question}`, { envId: sim.envId, title: sim.title, note: sim.note, label: sim.label });
    setChats(saved.chats);
    chatRef.current = saved.chatId;
    setChatId(saved.chatId);
    setShownTurnId(saved.turnId);
    setLiveSim(null); // the card now shows the finished simulation alone, by id
  }, []);

  const [deleting, setDeleting] = useState<string | null>(null);
  const removeDoc = useCallback(
    async (docId: string, title: string) => {
      if (!window.confirm(`Remove "${title.replaceAll("_", " ")}" from your sources? Its passages and graph links are deleted.`)) return;
      setDeleting(docId);
      setUploadError(null);
      const result = await deleteDocument(docId);
      if (!result.ok) setUploadError(result.error);
      await loadWorkspace();
      setDeleting(null);
    },
    [loadWorkspace],
  );

  const onFile = useCallback(
    async (file: File | undefined) => {
      if (!file) return;
      setUploading(true);
      setUploadError(null);
      const result = await uploadPdf(file);
      if (result.ok) {
        useWorkspace.getState().addDocument(result.document);
        await loadWorkspace(); // the source list now includes it
      } else setUploadError(result.error);
      setUploading(false);
    },
    [loadWorkspace],
  );

  const ask = useCallback(async (override?: string) => {
    const message = (override ?? question).trim();
    if (!message || useWorkspace.getState().turn === "streaming") return;
    abort.current?.abort();
    abort.current = new AbortController();
    const store = useWorkspace.getState();
    store.startTurn();
    setLiveSim(null);
    setShownTurnId(null);
    setAsked(message);
    setQuestion("");
    await streamChat(
      { message, history: [] },
      {
        onBlock: (block) => useWorkspace.getState().upsertBlock(block),
        onLayout: (next) => useWorkspace.getState().setLayout(next),
        onError: (error) => useWorkspace.getState().failTurn(error),
        onDone: () => useWorkspace.getState().finishTurn(),
      },
      { signal: abort.current.signal },
    );
    // Keep the finished turn in the open chat (a new chat on the first question), so it can be shown again for free.
    const done = useWorkspace.getState();
    if (done.turn !== "failed") {
      const kept = done.order.map((id) => done.blocks[id]).filter((b): b is UIBlock => b !== undefined);
      const saved = addTurn(chatRef.current, message, kept, done.layouts.adaptive);
      setChats(saved.chats);
      if (saved.turnId) {
        chatRef.current = saved.chatId;
        setChatId(saved.chatId);
        setShownTurnId(saved.turnId);
      }
    }
  }, [question]);

  // A question handed over by another screen (the Knowledge graph tab's "ask about this concept"): asked once, then removed from
  // the address so a reload does not ask it again.
  const handed = useRef(false);
  useEffect(() => {
    if (handed.current) return;
    handed.current = true;
    const params = new URLSearchParams(window.location.search);
    const q = params.get("ask")?.trim();
    if (!q) return;
    window.history.replaceState(null, "", window.location.pathname);
    setQuestion(q); // eslint-disable-line react-hooks/set-state-in-effect -- a one-time hand-over from the address
    void ask(q);
  }, [ask]);

  // The open chat's turns before the one the workspace shows: drawn above it as the thread, read-only, as they were.
  const openChatData = chats.find((c) => c.id === chatId) ?? null;
  const shownIndex = openChatData && shownTurnId ? openChatData.turns.findIndex((t) => t.id === shownTurnId) : -1;
  const earlier: Turn[] = openChatData ? (shownIndex >= 0 ? openChatData.turns.slice(0, shownIndex) : openChatData.turns) : [];
  // Turns after the one shown (a simulation brought in from the drawer lands here, below the current answer).
  const later: Turn[] = openChatData && shownIndex >= 0 ? openChatData.turns.slice(shownIndex + 1) : [];
  const shownTurn = openChatData && shownIndex >= 0 ? openChatData.turns[shownIndex] : undefined;

  /** A turn kept in the chat, drawn read-only as it was: the question, then its blocks or its simulation. */
  const storedTurn = (t: Turn) => (
    <div key={t.id} id={`turn-${t.id}`} className="scroll-mt-4 space-y-3">
      <QuestionBubble text={t.question} />
      {t.simulation ? (
        <SimulationTurn sim={t.simulation} />
      ) : (
        <div className="space-y-3 opacity-95">
          {t.blocks
            .filter((b) => b.type !== "SourceList") // the list of documents is the same every turn: shown once, on the left
            .map((b) => (
              <div key={`${t.id}-${b.id}`}>{renderBlock(b)}</div>
            ))}
        </div>
      )}
    </div>
  );
  const studioItems = chats
    .flatMap((c) => c.turns.filter((t) => t.tool).map((turn) => ({ chatId: c.id, turn })))
    .sort((a, b) => b.turn.at - a.turn.at);

  const layout = activeLayout({ layouts, layoutChoice });
  const byRegion = useMemo(
    () =>
      placeBlocksByRegion(
        layout,
        order.map((id) => blocks[id]).filter((b): b is UIBlock => b !== undefined),
        Object.values(workspaceBlocks),
      ),
    [layout, order, blocks, workspaceBlocks],
  );
  const placed = useMemo(() => flattenPlaced(byRegion), [byRegion]);

  // Uploads this session that the source list does not show: a document that failed to ingest (with its reason), and a
  // ready one the list has not caught up with (or when `/workspace` could not be reached).
  const listed = new Set(
    placed.sources.flatMap((b) => (b.type === "SourceList" ? b.data.documents.map((d) => d.docId) : [])),
  );
  const localDocs = documents.filter((d) => !listed.has(d.docId));

  // The answer block's id is the turn's id (other blocks of the turn have derived ids). Offer the trace once the turn
  // has ended, including a turn that ended in an error (the trace of a failure is the one most worth reading). A turn
  // whose connection died may have no trace on the server; opening the panel then shows the server's not-found message.
  const traced = turn !== "streaming" ? placed.chat.find((b) => b.type === "CitedSummary") : undefined;

  // A view can be saved from a finished, answered turn (its id is the answer block's id) and not from a view that was itself
  // applied from a saved one. Which kinds the server will accept is the server's decision; it says why if it refuses.
  const turnId = turn === "idle" ? placed.chat.find((b) => b.type === "CitedSummary")?.id : undefined;
  const SAVEABLE = ["GraphView", "TraversalView", "ComparisonGrid", "ConceptMap"];
  const KIND_NAMES: Record<string, string> = {
    GraphView: "Connection graph",
    TraversalView: "Search path",
    ComparisonGrid: "Document comparison",
    ConceptMap: "Connection path",
  };
  const inPane = (block: UIBlock) => panes.some((p) => p.id === block.id);
  const withSave = (block: UIBlock) => (
    <div key={block.id}>
      {block.meta.status === "ready" || block.meta.status === "partial" ? (
        <div className="mb-1 flex justify-end print:hidden">
          {inPane(block) ? (
            <button
              type="button"
              onClick={() => useWorkspace.getState().closePane(block.id)}
              className="rounded border border-stone-300 px-2 py-0.5 text-xs text-stone-600 hover:bg-stone-50"
            >
              Show here again
            </button>
          ) : (
            <button
              type="button"
              aria-label={`Open in a pane: ${blockTitle(block)}`}
              onClick={() => useWorkspace.getState().openPane(block)}
              className="rounded border border-stone-300 px-2 py-0.5 text-xs text-stone-600 hover:bg-stone-50"
            >
              Open in a pane
            </button>
          )}
        </div>
      ) : null}
      {inPane(block) ? (
        <p className="rounded border border-dashed border-stone-300 p-3 text-sm text-stone-500">
          {blockTitle(block)} is open in a pane.
        </p>
      ) : (
        renderBlock(block)
      )}
      {turnId && block.meta.status === "ready" && SAVEABLE.includes(block.type) && block.id.startsWith(turnId) && (
        <SaveView
          defaultName={KIND_NAMES[block.type] ?? block.type}
          onSave={async (name): Promise<SaveOutcome> => {
            const result = await savePattern({ turnId, templateId: block.type, name });
            if (!result.ok) return { ok: false, message: result.error.message };
            await loadPatterns();
            return { ok: true };
          }}
        />
      )}
    </div>
  );

  const studioHasShelf = layout.panels.some((p) => p.id === "studio" && p.regions.some((r) => r.id === "shelf"));
  // The studio shelf: the Studio's starters (they put a request in the question box), the saved views, and any block the layout places
  // there. A layout with no shelf region (a version 1 layout, or one from an older server) would leave these nowhere to
  // go, so they are shown after the graph area instead and the saved views stay reachable.
  const shelf = (
    // Studio's tools stay fixed at the top; only the Previous studios list scrolls (at phone width the page scrolls instead).
    <div className={`p-1 ${studioHasShelf ? "flex flex-col gap-4 md:h-full md:min-h-0" : "space-y-4"}`}>
      <Studio
        onStart={(request, submit) => {
          if (submit) {
            setQuestion(request);
            void ask(request);
            return;
          }
          // One click starts the tool. Its topic is what is in the question box (if it is not itself a tool's request), else the
          // best connected concept in the notes (the rule the server uses for a cheat sheet that names none).
          const typed = question.trim();
          const isStarter = STARTERS.some((s) => typed.toLowerCase().startsWith(s.request.trim().toLowerCase()));
          void (async () => {
            const topic = typed && !isStarter ? typed : await defaultTopic();
            const full = `${request}${topic}`;
            setQuestion(full);
            void ask(full);
          })();
        }}
      />
      <StudioList
        items={studioItems}
        busy={turn === "streaming"}
        onOpen={(id, turnId) => openChat(id, turnId)}
        onDelete={(id, turnId) => {
          setChats(deleteTurn(id, turnId));
          if (turnId === shownTurnId) newChat();
        }}
      />
      {(patterns.length > 0 || savedMessage || byRegion.studio.shelf.length > 0) && (
        <div className="space-y-4 md:max-h-[35vh] md:shrink-0 md:overflow-y-auto">
          {(patterns.length > 0 || savedMessage) && (
            <SavedViews
              patterns={patterns}
              busy={turn === "streaming"}
              message={savedMessage}
              staleId={staleId}
              onApply={(id) => void showView(id)}
              onDelete={(id) => void removeView(id)}
              onReverify={(id) => void checkAgain(id)}
            />
          )}
          {byRegion.studio.shelf.map(withSave)}
        </div>
      )}
    </div>
  );

  const panels: Record<PanelId, Partial<Record<RegionId, React.ReactNode>>> = {
    sources: {
      main: (
        <div className="space-y-4 p-1">
          <ChatList
            chats={chats}
            activeId={chatId}
            busy={turn === "streaming"}
            onNew={newChat}
            onOpen={(id) => openChat(id)}
            onRename={(id, title) => setChats(renameChat(id, title))}
            onDelete={(id) => {
              setChats(deleteChat(id));
              if (id === chatId) newChat();
            }}
          />
          <h2 className="nb-label border-t border-stone-200 pt-4">
            Sources<span className="nb-aside">your corpus</span>
          </h2>
          <label className="block cursor-pointer rounded-xl border border-dashed border-stone-300 bg-white/40 p-4 text-center text-sm text-stone-700 hover:border-stone-500 hover:bg-white">
            <span>{uploading ? "Reading the PDF…" : "+ Upload a PDF"}</span>
            {!uploading && <span className="ml-2 font-serif text-xs italic text-stone-500">graph built on upload</span>}
            <input
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              aria-label="Upload a PDF"
              disabled={uploading}
              onChange={(e) => {
                void onFile(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </label>
          {uploadError && (
            <p role="alert" className="text-sm text-red-700">
              {uploadError.message}
            </p>
          )}
          {localDocs.length > 0 && (
            <ul className="space-y-2 text-sm">
              {localDocs.map((doc, i) => (
                <li
                  key={doc.docId}
                  className="flex items-start gap-3 rounded-xl bg-white p-3 shadow-[0_1px_2px_rgba(35,33,28,0.06),0_0_0_1px_var(--color-stone-200)]"
                >
                  <span
                    aria-hidden
                    className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-md text-[10px] font-bold text-[#fff] ${DOC_TILES[i % DOC_TILES.length]}`}
                  >
                    PDF
                  </span>
                  <span className="min-w-0">
                    <span className="block font-medium text-stone-800">{doc.title}</span>
                    <span className={`block font-serif italic ${doc.status === "ready" ? "text-stone-500" : "text-red-700"}`}>
                      {doc.status === "ready" ? `${doc.chunkCount} passages` : (doc.error ?? "Failed")}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
          {placed.sources.map((block) =>
            block.type === "SourceList" && block.meta.status === "ready" ? (
              <section key={block.id} aria-label="Documents" className="space-y-1.5">
                <h3 className="px-1 text-[11px] font-semibold uppercase tracking-wide text-stone-500">
                  Documents ({block.data.documents.length})
                </h3>
                <ul className="space-y-1.5 text-sm">
                  {block.data.documents.map((doc, i) => (
                    <li
                      key={doc.docId}
                      className="group flex items-start gap-2.5 rounded-xl bg-white px-2.5 py-2 shadow-[0_0_0_1px_var(--color-stone-200)]"
                    >
                      <span
                        aria-hidden
                        className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md text-[9px] font-bold text-[#fff] ${DOC_TILES[i % DOC_TILES.length]}`}
                      >
                        PDF
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-medium leading-snug text-stone-800">{doc.title.replaceAll("_", " ")}</span>
                        <span className="block font-serif text-xs italic text-stone-500">{doc.chunkCount} passages</span>
                      </span>
                      <button
                        type="button"
                        aria-label={`Delete document: ${doc.title}`}
                        disabled={turn === "streaming" || deleting === doc.docId}
                        onClick={() => void removeDoc(doc.docId, doc.title)}
                        className="shrink-0 rounded px-1 text-stone-400 opacity-0 hover:text-red-700 focus:opacity-100 group-hover:opacity-100 disabled:opacity-40"
                      >
                        {deleting === doc.docId ? "…" : "×"}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ) : (
              <div key={block.id}>{renderBlock(block)}</div>
            ),
          )}
        </div>
      ),
    },
    chat: {
      main: (
        <div
          ref={centre}
          className={
            panes.length > 0
              ? "grid min-h-full gap-2 p-1 md:h-full md:min-h-0 md:grid-rows-[minmax(0,1fr)] md:[grid-template-columns:var(--cols)]"
              : "flex min-h-full flex-col p-1"
          }
          style={
            panes.length > 0
              ? ({
                  "--cols": paneFocus ? "minmax(0,1fr)" : `minmax(0,${100 - paneShare}fr) 0.5rem minmax(0,${paneShare}fr)`,
                } as React.CSSProperties)
              : undefined
          }
        >
        {/* With panes open the conversation scrolls on its own and each pane scrolls inside itself (md and wider). */}
        <div
          className={`flex min-h-full min-w-0 flex-1 flex-col gap-4 ${
            panes.length > 0 ? "md:h-full md:min-h-0 md:overflow-y-auto" : ""
          } ${paneFocus && panes.length > 0 ? "hidden" : ""}`}
        >
          <h2 className="nb-label border-b border-stone-200 pb-3">
            Conversation<span className="nb-aside">grounded in your corpus</span>
          </h2>

          {earlier.length > 0 && (
            <section aria-label="Earlier in this chat" className="space-y-6">
              {earlier.map(storedTurn)}
              <hr className="border-stone-200" />
            </section>
          )}
          {asked && (
            <div ref={currentQuestion} className="scroll-mt-4">
              <QuestionBubble text={asked} />
            </div>
          )}

          <section aria-label="Answer" className="flex-1 space-y-4">
            {liveSim && (
              <SimulationCard key={liveSim.nonce} question={liveSim.question} title={liveSim.question} onReady={onSimReady} />
            )}
            {!liveSim && shownTurn?.simulation && (
              <SimulationTurn sim={shownTurn.simulation} />
            )}
            {placed.chat.length === 0 && earlier.length === 0 && !asked && turn !== "streaming" && !(turn === "failed" && turnError) && (
              <div className="mx-auto max-w-2xl rounded-2xl bg-white p-6 shadow-[0_8px_24px_rgba(35,33,28,0.06),0_0_0_1px_var(--color-stone-200)]">
                <div className="flex items-center gap-3">
                  <Axi size={52} bob />
                  <p className="font-display text-2xl font-semibold text-stone-900">Welcome back</p>
                </div>
                <p className="mt-1 font-serif text-base italic text-stone-600">
                  Your sources are indexed into one knowledge graph. Just ask, and the interface adapts.
                </p>
                <p className="mt-3 text-sm leading-relaxed text-stone-600">
                  <span className="font-semibold text-stone-800">How this works.</span> Every answer is grounded in your documents
                  first, and every claim carries a citation you can check. It does not search the web: a general question your papers do
                  not cover gets a clear &ldquo;not found&rdquo; instead of a guess. Ask a question and the workspace arranges itself, or tap a tool
                  in the Studio. To see an idea move, press <span className="font-medium">Simulate</span> beside Ask: your question becomes an
                  interactive simulation, checked in a real browser first.
                </p>
                <DemoSuggestions
                  onPick={(q) => {
                    setQuestion(q);
                    void ask(q);
                  }}
                />
              </div>
            )}
            {byRegion.chat.main.map(withSave)}
            {traced && traced.meta.status !== "loading" && <TracePanel key={traced.id} turnId={traced.id} />}
            {turn === "failed" && placed.chat.length === 0 && turnError && (
              <p role="alert" className="text-sm text-red-700">
                {turnError.message}
              </p>
            )}
          </section>

          {later.length > 0 && (
            <section aria-label="Later in this chat" className="space-y-6">
              <hr className="border-stone-200" />
              {later.map(storedTurn)}
            </section>
          )}

          {turn === "streaming" && (
            <p role="status" className="flex items-center gap-2 font-serif text-sm italic text-stone-500">
              <Axi size={28} mood="thinking" bob />
              Axi is reading your papers and checking every quote…
            </p>
          )}
          <form
            className="sticky bottom-0 flex gap-2 rounded-2xl bg-white p-1.5 pl-4 shadow-[0_8px_24px_rgba(35,33,28,0.08),0_0_0_1px_var(--color-stone-300)]"
            onSubmit={(e) => {
              e.preventDefault();
              void ask();
            }}
          >
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything across your sources…"
              aria-label="Question"
              maxLength={4000}
              className="min-w-0 flex-1 bg-transparent py-2 font-serif text-base text-stone-900 italic outline-none placeholder:text-stone-400 [&:not(:placeholder-shown)]:not-italic [&:not(:placeholder-shown)]:font-sans"
            />
            <button
              type="button"
              onClick={() => runSim(question.trim() || asked)}
              title="Turn this question into an interactive simulation, checked in a real browser"
              className="flex items-center gap-1.5 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:border-stone-500"
            >
              <Axi size={20} />
              Simulate
            </button>
            <button
              type="submit"
              disabled={turn === "streaming" || !question.trim()}
              className="rounded-xl bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            >
              Ask
            </button>
          </form>
        </div>
        {panes.length > 0 && (
          <>
            {!paneFocus && (
              <PaneSeparator share={paneShare} onShare={(n) => useWorkspace.getState().setPaneShare(n)} container={centre} />
            )}
            <Panes
              panes={panes}
              onClose={(id) => useWorkspace.getState().closePane(id)}
              onCloseAll={() => useWorkspace.getState().closePanes()}
              focused={paneFocus}
              onToggleFocus={() => useWorkspace.getState().togglePaneFocus()}
            />
          </>
        )}
        </div>
      ),
      secondary:
        byRegion.chat.secondary.length > 0 ? (
          <div className="space-y-4 p-1">{byRegion.chat.secondary.map(withSave)}</div>
        ) : undefined,
    },
    studio: {
      main: (
        <div className="space-y-4 p-1">
          <h2 className="nb-label border-b border-stone-200 pb-3">
            Knowledge graph<span className="nb-aside">and connections</span>
          </h2>
          {byRegion.studio.main.length === 0 ? (
            <p className="font-serif text-sm italic text-stone-500">
              {layout.origin === "prebuilt"
                ? "In Basic, graphs and connections appear below the answer. Adaptive gives them this space."
                : "Graphs and connections appear here when your question needs them."}{" "}
              The whole corpus as a graph is in the <a href="/graph" className="not-italic text-stone-800 underline underline-offset-2">Knowledge graph</a> tab.
            </p>
          ) : (
            byRegion.studio.main.map(withSave)
          )}
          {!studioHasShelf && shelf}
        </div>
      ),
      shelf: studioHasShelf ? shelf : undefined,
    },
  };

  // A region this screen gives no content of its own (a component may ask for any region of any panel) still shows the
  // blocks placed in it, so a validated placement is never drawn nowhere.
  for (const panel of layout.panels) {
    for (const region of panel.regions) {
      const content = panels[panel.id];
      if (content[region.id] === undefined && byRegion[panel.id][region.id].length > 0) {
        content[region.id] = <div className="space-y-4 p-1">{byRegion[panel.id][region.id].map(withSave)}</div>;
      }
    }
  }

  // The Studio's top region holds only what an answer places there (a graph, connections). With nothing in it, it gives its
  // space to the Studio below; the corpus graph has its own tab. A viewer's arrangement only: the server's layout is unchanged.
  const studioTopEmpty = byRegion.studio.main.length === 0;
  const shownLayout = studioTopEmpty
    ? {
        ...layout,
        panels: layout.panels.map((p) =>
          p.id === "studio" && p.regions.some((r) => r.id === "shelf")
            ? { ...p, regions: p.regions.map((r) => (r.id === "main" ? { ...r, size: 0 } : r.id === "shelf" ? { ...r, size: 100 } : r)) }
            : p,
        ),
      }
    : layout;

  return (
    <>
    <SimulationLauncher onOpen={() => setDrawer({ kind: "picker" })} />
    <SimulationDrawer request={drawer} onClose={() => setDrawer(null)} onPick={(q) => runSim(q)} />
    <Shell
      layout={shownLayout}
      widenChat={panes.length > 0 && !paneFocus}
      header={
        <div className="flex items-center gap-3">
          <AppNav current="chat" />
          <LayoutSwitch
            choice={layoutChoice}
            adaptiveAvailable={layouts.adaptive !== null}
            onChoose={(choice) => useWorkspace.getState().chooseLayout(choice)}
          />
        </div>
      }
      panels={panels}
    />
    </>
  );
}
