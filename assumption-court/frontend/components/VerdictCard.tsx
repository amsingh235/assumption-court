import type { CauseResult, Report, Verdict } from "@/lib/types";

const labelClass: Record<Verdict["label"], string> = {
  SUPPORTED: "bg-green-600 text-white",
  REFUTED: "bg-red-600 text-white",
  INCONCLUSIVE: "bg-cream/20 text-cream",
};

function Scores({ v }: { v: Verdict }) {
  const pct = (n: number) => `${Math.max(2, (n / 12) * 100)}%`;
  return (
    <div className="space-y-1.5">
      {([["Bull", v.bull_total, "bg-green-500"], ["Bear", v.bear_total, "bg-red-500"]] as const).map(([name, total, color]) => (
        <div key={name} className="flex items-center gap-2 text-xs">
          <span className="font-pixel w-10 text-[10px] text-cream/70">{name}</span>
          <div className="h-3 flex-1 rounded-sm bg-white/10">
            <div className={`h-3 rounded-sm ${color}`} style={{ width: pct(total) }} />
          </div>
          <span className="w-12 text-right font-mono text-cream/90">{total}/12</span>
        </div>
      ))}
    </div>
  );
}

function VerdictBlock({ title, v }: { title: string; v: Verdict }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-pixel text-xs text-cream/80">{title}</span>
        <span className={`font-pixel rounded px-2 py-0.5 text-xs ${labelClass[v.label]}`}>{v.label}</span>
        <span className="text-xs text-cream/60">confidence {(v.confidence * 100).toFixed(0)}%</span>
        {v.override && (
          <span className="rounded bg-amber-400/20 px-2 py-0.5 text-[10px] text-amber-200" title="Anti-neutral rule">
            code override
          </span>
        )}
      </div>
      <Scores v={v} />
      <p className="text-sm text-cream/85">{v.rationale}</p>
      {v.verdict_changers.length > 0 && (
        <div>
          <div className="font-pixel text-[10px] text-clay">What would change the verdict</div>
          <ul className="ml-4 list-disc text-sm text-cream/75">
            {v.verdict_changers.map((c) => <li key={c}>{c}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function CauseRow({ c, i }: { c: CauseResult; i: number }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="mb-2 text-xs text-cream/60">Cause {i + 1}: {c.cause_text}</div>
      <VerdictBlock title="Cause ruling" v={c.verdict} />
    </div>
  );
}

/** Final ruling, shown once playback has finished. */
export default function VerdictCard({ report }: { report: Report | null }) {
  if (!report) return null;
  const fake = report.cost.llm_provider === "fake" || report.cost.retrieval_provider === "fake";
  return (
    <section aria-label="Ruling" className="w-full rounded-2xl border-4 border-ink bg-coal p-5 shadow-[0_6px_0_rgba(0,0,0,0.4)]">
      <h2 className="font-pixel mb-3 text-lg text-clay">⚖ THE RULING</h2>
      {fake && (
        <div className="mb-3 rounded-md border border-amber-400/30 bg-amber-400/10 p-2 text-xs text-amber-200">
          Offline placeholder: produced with the fake LLM/retrieval, not a real model. These verdicts mean nothing.
        </div>
      )}
      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <div className="space-y-4">
          <VerdictBlock title="Premise" v={report.premise_verdict} />
          {report.causes.map((c, i) => <CauseRow key={c.cause_text} c={c} i={i} />)}
        </div>
        <div>
          <div className="font-pixel text-[10px] text-clay">3 questions to ask before you bet on this</div>
          <ol className="ml-4 mt-1 list-decimal space-y-1 text-sm text-cream/85">
            {report.questions_to_ask.map((q) => <li key={q}>{q}</li>)}
          </ol>
          <div className="mt-4 text-[11px] text-cream/50">
            {report.cost.llm_calls} LLM calls · {report.cost.retrieval_queries ?? "?"} searches · {report.cost.seconds}s ·{" "}
            {report.evidence.filter((e) => e.status === "UNVERIFIED").length} of {report.evidence.length} exhibits not admitted
          </div>
        </div>
      </div>
    </section>
  );
}
