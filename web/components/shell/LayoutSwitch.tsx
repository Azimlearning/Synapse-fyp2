// The Basic | Adaptive control. Basic is the fixed starting layout; Adaptive is the one composed for the current answer
// and exists only after an answer. Choosing Basic pins it (a later adaptive layout no longer takes over by itself);
// choosing Adaptive un-pins it. Both buttons state their pressed state, and Adaptive says why it is unavailable.

import type { LayoutChoice } from "@/lib/store";

export function LayoutSwitch({
  choice,
  adaptiveAvailable,
  onChoose,
}: {
  choice: LayoutChoice;
  adaptiveAvailable: boolean;
  onChoose: (choice: LayoutChoice) => void;
}) {
  const button = (value: LayoutChoice, label: string, disabled = false) => (
    <button
      type="button"
      aria-pressed={choice === value}
      disabled={disabled}
      aria-describedby={disabled ? "adaptive-hint" : undefined}
      title={disabled ? "Adaptive is available after your first answer." : value === "adaptive" ? "The layout composed for this answer" : "The fixed layout"}
      onClick={() => onChoose(value)}
      className={`rounded-full px-3 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-40 ${
        choice === value
          ? "bg-white font-medium text-stone-900 shadow-[0_0_0_1px_var(--color-stone-200)]"
          : "text-stone-600 hover:text-stone-900"
      }`}
    >
      {label}
    </button>
  );
  return (
    <div className="flex items-center gap-2">
      <div role="group" aria-label="Layout" data-tour="layout" className="flex gap-0.5 rounded-full border border-stone-200 bg-stone-100 p-0.5">
        {button("basic", "Basic")}
        {button("adaptive", "Adaptive", !adaptiveAvailable)}
      </div>
      {!adaptiveAvailable && (
        <span id="adaptive-hint" className="sr-only">
          Adaptive is available after your first answer.
        </span>
      )}
    </div>
  );
}
