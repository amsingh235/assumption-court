import PixelAgent from "./pixel/PixelAgent";
import { AGENT_INFO, AGENT_ORDER } from "@/lib/agents";
import type { AgentName } from "@/lib/types";
import type { Speaker } from "@/lib/scene";

/** Pixel title + "org chart" of the five agents (orange connectors down to cream tiles). */
export default function AgentsHeader({ active }: { active: Speaker | null }) {
  return (
    <header className="px-4 pt-4">
      <h1 className="font-pixel text-center text-3xl tracking-wider text-clay sm:text-4xl [text-shadow:0_4px_0_#7a3a22]">
        ASSUMPTION COURT
      </h1>
      <p className="mt-1 text-center text-xs text-cream/60">
        Five agents put your assumption on trial. Every claim needs a retrieved quote, or it is thrown out.
      </p>
      <div className="relative mx-auto mt-2 max-w-2xl">
        {/* connector: stem from title, bar across, drops to each tile */}
        <div className="mx-auto h-3 w-1 bg-clay" />
        <div className="mx-[10%] h-1 bg-clay" />
        <div className="grid grid-cols-5 gap-2 sm:gap-4">
          {AGENT_ORDER.map((id: AgentName) => {
            const on = active === id;
            return (
              <div key={id} className="flex flex-col items-center">
                <div className="h-3 w-1 bg-clay" />
                <div
                  aria-current={on ? "true" : undefined}
                  className={`flex aspect-square w-full max-w-[76px] items-center justify-center rounded-2xl bg-cream shadow-[0_4px_0_#b9a58f] transition-all duration-300 ${
                    on ? "-translate-y-1 ring-4 ring-clay shadow-[0_0_24px_6px_rgba(217,119,87,0.55)]" : ""
                  }`}
                >
                  <PixelAgent id={id} pose={on ? "talk" : "idle"} size={50} title={AGENT_INFO[id].name} />
                </div>
                <span className={`font-pixel mt-1 text-[10px] sm:text-xs ${on ? "text-clay" : "text-cream/80"}`}>
                  {AGENT_INFO[id].name}
                </span>
                
              </div>
            );
          })}
        </div>
      </div>
    </header>
  );
}
