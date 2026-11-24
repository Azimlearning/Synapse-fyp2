// Conversations, kept in this browser the way chat assistants keep them: a list of chats (newest first), each a thread of turns
// (a question and the blocks the server sent for it, with the adaptive layout), which can be opened, renamed and deleted. Studio
// outputs (quiz, flashcards, brief, drafts...) are turns too; "Previous studios" lists them across all chats. Opening a turn shows
// the stored blocks again with no server call and no spend. Per viewer and per browser only (localStorage): a blocked or full
// storage keeps less, never fails the page.

import type { LayoutSpec, UIBlock } from "@arcana/schema";

import { STARTERS } from "@/components/shell/Studio";

export interface Turn {
  id: string;
  question: string;
  /** The Studio tool's name when the turn came from one (e.g. "Quiz me"), else null. */
  tool: string | null;
  at: number;
  blocks: UIBlock[];
  adaptive: LayoutSpec | null;
  /** A simulation brought into the chat from the simulation drawer: the engine's Environment id and title (it is shown again
   *  through the engine's delivery gate by id, never stored here). */
  simulation?: { envId: string; title: string; note?: string; label?: string } | null;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  turns: Turn[];
}

const KEY = "synapse-chats-v1";
const ACTIVE_KEY = "synapse-active-chat";
const MAX_CHATS = 40;

const newId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;

/** Which Studio tool a request came from, if any (it opens with that tool's words). */
export function studioToolOf(question: string): string | null {
  const q = question.trim().toLowerCase();
  const hit = STARTERS.find((s) => q.startsWith(s.request.trim().toLowerCase()));
  return hit ? hit.label : null;
}

/** A Studio request without the tool's own words ("Make flashcards for BM25" gives "BM25"). */
export function topicOf(turn: Turn): string {
  if (turn.simulation) return turn.simulation.title;
  const s = STARTERS.find((x) => turn.question.toLowerCase().startsWith(x.request.trim().toLowerCase()));
  return s ? turn.question.slice(s.request.length).trim() || turn.question : turn.question;
}

export function loadChats(): Conversation[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? (parsed as Conversation[]).filter((c) => c && Array.isArray(c.turns)) : [];
  } catch {
    return [];
  }
}

function save(chats: Conversation[]): Conversation[] {
  let keep = [...chats].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_CHATS);
  // Drop the oldest chats until it fits the browser's quota (the newest is always tried last-dropped).
  while (keep.length > 0) {
    try {
      localStorage.setItem(KEY, JSON.stringify(keep));
      return keep;
    } catch {
      if (keep.length === 1) {
        // One chat alone is too big: keep its newest turns only.
        const only = keep[0];
        if (!only || only.turns.length <= 1) break;
        keep = [{ ...only, turns: only.turns.slice(1) }];
      } else keep = keep.slice(0, -1);
    }
  }
  return keep;
}

/** Add a finished turn to the chat `chatId` (or to a new chat when null). Returns the chats and the chat and turn ids used. A turn
 *  with no ready block is not kept. */
export function addTurn(
  chatId: string | null,
  question: string,
  blocks: UIBlock[],
  adaptive: LayoutSpec | null,
): { chats: Conversation[]; chatId: string | null; turnId: string | null } {
  const chats = loadChats();
  if (!blocks.some((b) => b.meta.status === "ready")) return { chats, chatId, turnId: null };
  const turn: Turn = { id: newId(), question, tool: studioToolOf(question), at: Date.now(), blocks, adaptive };
  const existing = chatId ? chats.find((c) => c.id === chatId) : undefined;
  let next: Conversation[];
  let id: string;
  if (existing) {
    id = existing.id;
    next = chats.map((c) => (c.id === id ? { ...c, updatedAt: turn.at, turns: [...c.turns, turn] } : c));
  } else {
    id = newId();
    const title = (turn.tool ? `${turn.tool}: ${topicOf(turn)}` : question).slice(0, 80);
    next = [{ id, title, createdAt: turn.at, updatedAt: turn.at, turns: [turn] }, ...chats];
  }
  const saved = save(next);
  setActiveChat(id);
  return { chats: saved, chatId: id, turnId: turn.id };
}

/** Bring a simulation into the chat `chatId` (or a new chat): a turn of its own, after the others. */
export function addSimulationTurn(
  chatId: string | null,
  question: string,
  simulation: { envId: string; title: string; note?: string; label?: string },
): { chats: Conversation[]; chatId: string; turnId: string } {
  const chats = loadChats();
  // A simulation is a Studio output too: it is listed under "Previous studios" as "Simulation".
  const turn: Turn = { id: newId(), question, tool: "Simulation", at: Date.now(), blocks: [], adaptive: null, simulation };
  const existing = chatId ? chats.find((c) => c.id === chatId) : undefined;
  const id = existing ? existing.id : newId();
  const next = existing
    ? chats.map((c) => (c.id === id ? { ...c, updatedAt: turn.at, turns: [...c.turns, turn] } : c))
    : [{ id, title: `Simulation: ${simulation.title}`.slice(0, 80), createdAt: turn.at, updatedAt: turn.at, turns: [turn] }, ...chats];
  const saved = save(next);
  setActiveChat(id);
  return { chats: saved, chatId: id, turnId: turn.id };
}

export function renameChat(id: string, title: string): Conversation[] {
  const t = title.trim();
  if (!t) return loadChats();
  return save(loadChats().map((c) => (c.id === id ? { ...c, title: t.slice(0, 80) } : c)));
}

export function deleteChat(id: string): Conversation[] {
  if (activeChat() === id) setActiveChat(null);
  return save(loadChats().filter((c) => c.id !== id));
}

/** Remove one turn (a Studio output) from its chat; a chat left empty is removed. */
export function deleteTurn(chatId: string, turnId: string): Conversation[] {
  const next = loadChats()
    .map((c) => (c.id === chatId ? { ...c, turns: c.turns.filter((t) => t.id !== turnId) } : c))
    .filter((c) => c.turns.length > 0);
  return save(next);
}

export function activeChat(): string | null {
  try {
    return localStorage.getItem(ACTIVE_KEY);
  } catch {
    return null;
  }
}

export function setActiveChat(id: string | null): void {
  try {
    if (id) localStorage.setItem(ACTIVE_KEY, id);
    else localStorage.removeItem(ACTIVE_KEY);
  } catch {
    /* blocked storage: the choice lasts for this visit */
  }
}

/** The chats grouped by when they were last used, as chat assistants show them. */
export function groupChats(chats: Conversation[], now = Date.now()): { label: string; chats: Conversation[] }[] {
  const day = 24 * 60 * 60 * 1000;
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  const today = start.getTime();
  const groups: { label: string; test: (t: number) => boolean }[] = [
    { label: "Today", test: (t) => t >= today },
    { label: "Yesterday", test: (t) => t >= today - day && t < today },
    { label: "Previous 7 days", test: (t) => t >= today - 7 * day && t < today - day },
    { label: "Older", test: (t) => t < today - 7 * day },
  ];
  return groups
    .map((g) => ({ label: g.label, chats: chats.filter((c) => g.test(c.updatedAt)) }))
    .filter((g) => g.chats.length > 0);
}
