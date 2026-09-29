"use client";

import { useEffect, useRef } from "react";
import PixelAgent from "./pixel/PixelAgent";
import { AGENT_INFO } from "@/lib/agents";
import { stageLabel } from "@/lib/graphState";
import type { Utterance } from "@/lib/scene";

const toneBorder = { neutral: "border-cream/10", good: "border-green-500/40", bad: "border-red-500/40" } as const;

/** Claude-chat style log of everything said in court. */
export default function Transcript({ items, onEvidence }: { items: Utterance[]; onEvidence: (id: string) => void }) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // Scroll only the rail, never the page.
    const box = end.current?.closest<HTMLElement>("[data-scroll]");
    if (box) box.scrollTo({ top: box.scrollHeight, behavior: "smooth" });
  }, [items.length]);

  if (!items.length) {
    return <p className="p-6 text-center text-sm text-cream/40">The transcript fills in as the agents speak.</p>;
  }
  return (
    <ol className="space-y-3 p-3">
      {items.map((u, i) => {
        const newStage = i === 0 || items[i - 1].stage !== u.stage;
        const agent = u.agent === "court" ? null : u.agent;
        return (
          <li key={u.id}>
            {newStage && (
              <div className="font-pixel my-2 text-center text-[10px] text-clay">── {stageLabel(u.stage)} ──</div>
            )}
            {!agent ? (
              <p className="text-center text-xs italic text-cream/60">{u.text}</p>
            ) : (
              <div className="flex gap-2">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-cream">
                  <PixelAgent id={agent} size={28} className="!animate-none" title={AGENT_INFO[agent].name} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-pixel text-[10px] text-cream/70">{AGENT_INFO[agent].name}</div>
                  <div className={`mt-0.5 rounded-xl rounded-tl-sm border bg-white/5 px-3 py-2 text-[13px] leading-snug text-cream/90 ${toneBorder[u.tone]}`}>
                    {u.text}
                    {u.evidenceId && (
                      <button onClick={() => onEvidence(u.evidenceId!)} className="ml-1 text-xs text-clay underline">
                        view quote
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </li>
        );
      })}
      <div ref={end} />
    </ol>
  );
}
