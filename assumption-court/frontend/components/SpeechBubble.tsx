import type { Utterance } from "@/lib/scene";
import { AGENT_INFO } from "@/lib/agents";

const toneClass = { neutral: "text-ink", good: "text-green-800", bad: "text-red-800" } as const;

/** Typewriter bubble. Pure CSS: each character fades in with a staggered delay (restarts via `key`). */
export default function SpeechBubble({ u, tailX, speed }: { u: Utterance; tailX: number; speed: number }) {
  const who = u.agent === "court" ? "Clerk of the court" : AGENT_INFO[u.agent].name;
  const text = u.text.length > 420 ? `${u.text.slice(0, 419)}…` : u.text;
  const step = 16 / speed;
  return (
    <div className="bubble-in relative rounded-2xl border-4 border-ink bg-cream px-4 py-3 shadow-[0_6px_0_rgba(0,0,0,0.35)]">
      <div className="font-pixel mb-1 text-[10px] uppercase text-clay-dark">{who}</div>
      <p className={`line-clamp-3 text-sm leading-snug ${toneClass[u.tone]}`} aria-live="polite" title={u.text}>
        {[...text].map((ch, i) => (
          <span key={i} className="tw-char" style={{ animationDelay: `${Math.round(i * step)}ms` }}>
            {ch}
          </span>
        ))}
      </p>
      <span
        aria-hidden
        className="absolute -bottom-[14px] h-0 w-0 border-x-[12px] border-t-[14px] border-x-transparent border-t-ink transition-[left] duration-500"
        style={{ left: `calc(${tailX}% - 12px)` }}
      />
    </div>
  );
}
