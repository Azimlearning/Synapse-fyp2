// Adapted from Azimlearning/GenUI-Education (Synapse v5), web/components/Mascot.tsx @ 7c2b84c (itself ported from Synapse v3).
// Read in full. Kept: Axi as drawn, in the "happy" and "thinking" moods, and the gentle bob. Changed: two moods only and a fixed
// gradient id (every copy draws the same gradient, so a shared id is harmless) so the component needs no hook. Decorative:
// hidden from assistive technology; whatever Axi signals is also said in text next to it.

const INK = "#14312c";

export function Axi({
  size = 34,
  className = "",
  mood = "happy",
  bob = false,
}: {
  size?: number;
  className?: string;
  mood?: "happy" | "thinking";
  bob?: boolean;
}) {
  const thinking = mood === "thinking";
  const dx = thinking ? 1.5 : 0;
  const dy = thinking ? -2.5 : 0;
  return (
    <span
      className={`inline-block shrink-0 ${bob ? "motion-safe:animate-[axi-bob_2.4s_ease-in-out_infinite]" : ""} ${className}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg viewBox="0 0 100 100" width={size} height={size} fill="none">
        <defs>
          <linearGradient id="axi-body" x1="0" y1="0" x2="0.35" y2="1">
            <stop offset="0%" stopColor="#16b6a3" />
            <stop offset="100%" stopColor="#0a776b" />
          </linearGradient>
        </defs>
        <ellipse cx="50" cy="52" rx="46" ry="16.5" stroke="#12a594" strokeWidth="3" transform="rotate(-18 50 52)" opacity="0.9" />
        <circle cx="93" cy="38" r="4" fill="#12a594" />
        <ellipse cx="42" cy="83" rx="6" ry="4" fill="#0e8a7c" />
        <ellipse cx="58" cy="83" rx="6" ry="4" fill="#0e8a7c" />
        <ellipse cx="24" cy="63" rx="5" ry="8" fill="#12a594" transform="rotate(-14 24 63)" />
        <ellipse cx="76" cy="63" rx="5" ry="8" fill="#12a594" transform="rotate(14 76 63)" />
        <circle cx="50" cy="56" r="27" fill="url(#axi-body)" />
        <ellipse cx="50" cy="63" rx="17" ry="13" fill="#3dc2b2" opacity="0.9" />
        <ellipse cx="33" cy="61" rx="4.2" ry="2.7" fill="#f4a28c" opacity="0.55" />
        <ellipse cx="67" cy="61" rx="4.2" ry="2.7" fill="#f4a28c" opacity="0.55" />
        <ellipse cx="42" cy="53" rx="7" ry="8" fill="#ffffff" />
        <ellipse cx="58" cy="53" rx="7" ry="8" fill="#ffffff" />
        <circle cx={42 + dx} cy={53 + dy} r="3.4" fill={INK} />
        <circle cx={58 + dx} cy={53 + dy} r="3.4" fill={INK} />
        <circle cx={40.6 + dx} cy={51 + dy} r="1.3" fill="#ffffff" />
        <circle cx={56.6 + dx} cy={51 + dy} r="1.3" fill="#ffffff" />
        {thinking ? (
          <>
            <ellipse cx="50" cy="64" rx="2.6" ry="2.2" fill={INK} />
            <circle cx="74" cy="33" r="2.2" fill="#838e88" />
            <circle cx="80" cy="27" r="2.8" fill="#838e88" />
            <circle cx="87" cy="20" r="3.4" fill="#838e88" />
          </>
        ) : (
          <path d="M45 63 q5 5 10 0" stroke={INK} strokeWidth="2.2" strokeLinecap="round" />
        )}
      </svg>
    </span>
  );
}
