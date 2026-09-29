import type { AgentName } from "@/lib/types";

const AGENTS: { id: AgentName; avatar: string; name: string; role: string }[] = [
  { id: "researcher", avatar: "🔍", name: "Researcher", role: "finds sources" },
  { id: "bull", avatar: "📈", name: "Bull", role: "argues it holds" },
  { id: "bear", avatar: "📉", name: "Bear", role: "argues it fails" },
  { id: "factchecker", avatar: "🧮", name: "Fact-checker", role: "checks quotes" },
  { id: "judge", avatar: "⚖️", name: "Judge", role: "scores & rules" },
];

export default function AgentBench({ active, statusLine }: { active: AgentName | null; statusLine: string }) {
  return (
    <section aria-label="Agent bench" className="w-full">
      <div className="flex gap-2 overflow-x-auto pb-1 sm:justify-center">
        {AGENTS.map((a) => {
          const on = a.id === active;
          return (
            <div
              key={a.id}
              aria-current={on ? "true" : undefined}
              className={`flex min-w-[104px] flex-col items-center rounded-xl border px-3 py-2 transition-shadow duration-300 ${
                on ? "border-accent bg-blue-50 shadow-[0_0_18px_4px_rgba(59,130,246,0.55)]" : "border-slate-200 bg-white"
              }`}
            >
              <span className="text-2xl" aria-hidden>{a.avatar}</span>
              <span className="text-xs font-semibold text-navy">{a.name}</span>
              <span className="text-[10px] text-slate-500">{a.role}</span>
            </div>
          );
        })}
      </div>
      <p className="mt-1 min-h-5 text-center text-xs text-slate-600" aria-live="polite">{statusLine}</p>
    </section>
  );
}
