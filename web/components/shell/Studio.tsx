// The Studio area (D-32, D-42): the learning and writing tools a learner uses to turn their documents into study material, and
// below them the outputs shelf. Each tool is a starter, not a generator of its own: it puts a request in the question box (or
// asks it at once), and the Orchestrator's `write` and `study` intents route it to the Studio agent. So the shelf holds no
// behaviour the server does not have, and nothing here calls the server directly.

export interface StudioStarter {
  id: string;
  label: string;
  hint: string;
  /** The request put in the question box. */
  request: string;
  /** True when the request is complete and is asked at once; false when the learner adds a topic first. */
  submit: boolean;
}

/** The tools the Studio agent has, in the order they are shown. Each request opens with the words the server recognises. */
export const STARTERS: readonly StudioStarter[] = [
  { id: "quiz", label: "Quiz me", hint: "Fill the blank", request: "Quiz me on ", submit: false },
  { id: "flashcards", label: "Flashcards", hint: "Name a topic", request: "Make flashcards for ", submit: false },
  { id: "blurt", label: "Blurting", hint: "Recall, then check", request: "Make a blurting exercise for ", submit: false },
  { id: "cornell", label: "Cornell notes", hint: "Name a topic", request: "Give me cornell notes on ", submit: false },
  { id: "socratic", label: "Socratic questions", hint: "Name a topic", request: "Guide me with socratic questions about ", submit: false },
  { id: "insights", label: "Learning insights", hint: "Where you stand", request: "Show my learning insights", submit: true },
  { id: "review", label: "Review schedule", hint: "What is due", request: "What should I review today?", submit: true },
  { id: "brief", label: "Document brief", hint: "Key points, next steps", request: "Brief me on ", submit: false },
  { id: "sheet", label: "Cheat sheet", hint: "One page, with a diagram", request: "Make a cheat sheet for ", submit: false },
  { id: "write", label: "Write an outline", hint: "Name a topic", request: "Write an outline on ", submit: false },
  { id: "litreview", label: "Literature review", hint: "Cited, by theme", request: "Write a literature review of ", submit: false },
  { id: "abstract", label: "Abstract", hint: "Cited, short", request: "Write an abstract on ", submit: false },
  { id: "audio", label: "Audio overview", hint: "A script to listen to", request: "Make an audio overview of ", submit: false },
];

/** The icon tile for each tool, in the FYP1 notebook design's colours (a glyph on a coloured square). */
const TILES: Record<string, { glyph: string; bg: string }> = {
  quiz: { glyph: "?", bg: "bg-[#3d7a52]" },
  flashcards: { glyph: "▤", bg: "bg-[#3d7a52]" },
  blurt: { glyph: "✎", bg: "bg-[#9a6b18]" },
  cornell: { glyph: "▥", bg: "bg-[#3d7a52]" },
  socratic: { glyph: "◎", bg: "bg-[#6a4ea8]" },
  insights: { glyph: "◔", bg: "bg-[#2f5fa8]" },
  review: { glyph: "◷", bg: "bg-[#9a6b18]" },
  brief: { glyph: "≡", bg: "bg-[#2f5fa8]" },
  sheet: { glyph: "▦", bg: "bg-[#9a6b18]" },
  write: { glyph: "§", bg: "bg-[#23211c]" },
  litreview: { glyph: "⊞", bg: "bg-[#2f5fa8]" },
  abstract: { glyph: "¶", bg: "bg-[#23211c]" },
  audio: { glyph: "♪", bg: "bg-[#a8423a]" },
  notes: { glyph: "✱", bg: "bg-[#6a4ea8]" },
};

const TILE = "flex h-full w-full items-start gap-2 rounded-xl bg-white p-2 text-left text-[13px] leading-snug shadow-[0_1px_2px_rgba(35,33,28,0.06),0_0_0_1px_var(--color-stone-200)] transition hover:-translate-y-px hover:shadow-[0_6px_16px_rgba(35,33,28,0.10),0_0_0_1px_var(--color-stone-300)] disabled:cursor-not-allowed disabled:opacity-60";

function Glyph({ id }: { id: string }) {
  const t = TILES[id] ?? { glyph: "•", bg: "bg-stone-700" };
  return (
    // Drawn as a pseudo-element so the glyph is decoration only: not in the tile's text, not read aloud.
    <span
      aria-hidden
      data-glyph={t.glyph}
      className={`grid h-6 w-6 shrink-0 place-items-center rounded-md text-xs text-[#fff] before:content-[attr(data-glyph)] ${t.bg}`}
    />
  );
}

export function Studio({ onStart }: { onStart?: (request: string, submit: boolean) => void }) {
  return (
    <section aria-label="Studio" data-tour="studio" className="shrink-0 space-y-2">
      <h2 className="nb-label border-b border-stone-200 pb-3">
        Studio<span className="nb-aside">{STARTERS.length + 1} tools</span>
      </h2>
      {/* Two tiles a row when the panel is wide enough, one when it is narrow, so a label never breaks letter by letter. */}
      <ul className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-2 text-sm">
        {STARTERS.map((s) => (
          <li key={s.id}>
            <button type="button" disabled={!onStart} onClick={() => onStart?.(s.request, s.submit)} className={TILE}>
              <Glyph id={s.id} />
              <span className="min-w-0">
                <span className="block font-medium text-stone-800">{s.label}</span>
                <span className="block font-serif text-xs italic text-stone-500">{s.hint}</span>
              </span>
            </button>
          </li>
        ))}
        <li>
          <a href="/notes" data-tour="notes" className={TILE}>
            <Glyph id="notes" />
            <span className="min-w-0">
              <span className="block font-medium text-stone-800">Notes</span>
              <span className="block font-serif text-xs italic text-stone-500">Pages, graph, quiz</span>
            </span>
          </a>
        </li>
      </ul>
    </section>
  );
}
