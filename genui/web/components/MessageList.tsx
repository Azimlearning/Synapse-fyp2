"use client";

// Adapted from Synapse v3: frontend/components/chat/MessageList.tsx and StreamRenderer.tsx (Genui monorepo, commit 835a2cefda28). Kept: the question bubble, the
// teal-ruled response, the streaming caret. Changed: a turn is V4's (lib/turns.ts), the Environment is a Peek card shown inline (or a lab bench column on a wide
// screen, see LabBench), and the progress card shows the real pipeline layers.
import { useEffect, useRef, type RefObject } from "react";
import { useT } from "../lib/i18n";
import { useEmbedParams } from "../lib/embed";
import { usePacedStep } from "../lib/pace";
import type { Turn } from "../lib/turns";
import { BuildDetails, BuildLog } from "./BuildLog";
import { DegradedCard } from "./DegradedCard";
import { ExamCard } from "./ExamCard";
import { Peek } from "./Peek";
import { ProbeCard } from "./ProbeCard";
import { PeekSkeleton } from "./PeekSkeleton";
import { ProgressStages } from "./ProgressStages";
import { Stage } from "./Stage";

/** On a narrow screen: the progress bar (and the draft under it) while the question is worked on, then the lab. Same pacing as the bench column (lib/pace.ts). */
function TurnWork({
  turn,
  labRef,
  stagedId,
  onOpen,
  onBack,
}: {
  turn: Turn;
  labRef: RefObject<HTMLDivElement | null> | undefined;
  stagedId: string | null;
  onOpen: (id: string, present?: boolean) => void;
  onBack: () => void;
}) {
  const shown = usePacedStep(turn.step, turn.id);
  const { embedded } = useEmbedParams();
  const working = turn.open || (turn.block !== null && shown !== "ready");
  if (working) {
    // Inside the Synapse workspace the chat shows the question and the note; this card shows how the simulation is built (its code).
    return (
      <div className="grid gap-3">
        <div data-embed-hide>
          <ProgressStages step={shown} />
        </div>
        <BuildLog log={turn.log} draft={turn.draft} code={turn.code} open={embedded} />
        {turn.draft && !turn.block ? <PeekSkeleton draft={turn.draft} /> : null}
      </div>
    );
  }
  if (!turn.block) return null;
  return (
    <div ref={labRef} className="scroll-mt-2">
      {stagedId === turn.block.id ? <Stage block={turn.block} onBack={onBack} /> : <Peek block={turn.block} onOpen={() => onOpen(turn.block!.id)} />}
      <div className="mt-3">
        <BuildDetails block={turn.block} log={turn.log} />
      </div>
    </div>
  );
}

export function MessageList({
  turns,
  wide,
  stagedId,
  onOpen,
  onBack,
  onRetry,
}: {
  turns: Turn[];
  /** On a wide screen the Environment, the draft and the progress live in the lab bench column, so they are not repeated here. */
  wide: boolean;
  stagedId: string | null;
  onOpen: (id: string, present?: boolean) => void;
  onBack: () => void;
  onRetry: (question: string) => void;
}) {
  const t = useT();
  const bottom = useRef<HTMLDivElement>(null);
  const lab = useRef<HTMLDivElement>(null);
  const last = turns[turns.length - 1];
  // While a turn streams, follow its words to the bottom. Once its lab arrives on a narrow screen, bring the lab to the top instead and keep it there: the practice
  // cards that come after it would otherwise scroll a phone user straight past the lab.
  const labShown = !wide && last?.block ? last.block.id : null;
  useEffect(() => {
    if (labShown && lab.current) lab.current.scrollIntoView?.({ block: "start" });
    else bottom.current?.scrollIntoView?.({ block: "end" });
  }, [turns, labShown]);

  return (
    <div className="flex-1 space-y-6 overflow-y-auto py-6">
      {turns.map((turn) => (
        <div key={turn.id} className="space-y-4">
          <div data-embed-hide className="flex justify-end">
            <div className="max-w-[85%] rounded-card border-2 border-line bg-card px-4 py-2.5 text-[15px] font-medium text-ink shadow-[0_3px_0_var(--line-2)]">{turn.question}</div>
          </div>
          <div className="study-response grid gap-3">
            <p data-embed-hide className="study-kicker">{turn.fromLibrary ? t("fromLibrary") : t("quickNote")}</p>
            <div data-embed-hide data-testid="answer" aria-live="polite" className={`text-[15px] leading-7 whitespace-pre-wrap ${turn.open && !turn.block ? "caret" : ""}`}>
              {/* The offline model tags its text "[fake:<purpose>:<hash>] " for the tests; the tag is not shown to a learner. */}
              {turn.text.replace(/^\[fake:[^\]]*\]\s*/, "")}
            </div>
            {turn.note ? <DegradedCard kind="note" message={turn.note} /> : null}
            {turn.error ? (
              <DegradedCard
                kind="error"
                message={
                  typeof turn.error === "string"
                    ? turn.error
                    : `${turn.error.message}${turn.error.issues.length > 0 ? ` (${turn.error.issues.map((i) => `${i.path}: ${i.message}`).join("; ")})` : ""}`
                }
                onRetry={typeof turn.error === "string" || turn.error.retryable ? () => onRetry(turn.question) : undefined}
              />
            ) : null}
            {!wide ? (
              <TurnWork turn={turn} labRef={turn === last ? lab : undefined} stagedId={stagedId} onOpen={onOpen} onBack={onBack} />
            ) : null}
            {turn.probe ? <div data-embed-hide><ProbeCard probe={turn.probe} /></div> : null}
            {turn.exam ? <div data-embed-hide><ExamCard item={turn.exam} /></div> : null}
          </div>
        </div>
      ))}
      <div ref={bottom} />
    </div>
  );
}
