import type { CauseResult, Report, Verdict } from "@/lib/types";

const labelClass: Record<Verdict["label"], string> = {
  SUPPORTED: "bg-green-700",
  REFUTED: "bg-red-700",
  INCONCLUSIVE: "bg-slate-500",
};

function Scores({ v }: { v: Verdict }) {
  return (
    <div className="grid grid-cols-2 gap-2 text-center text-sm">
      <div className="rounded-md bg-green-50 p-2">
        <div className="text-[11px] text-green-800">📈 Bull</div>
        <div className="text-lg font-bold text-green-800">{v.bull_total}/12</div>
      </div>
      <div className="rounded-md bg-red-50 p-2">
        <div className="text-[11px] text-red-800">📉 Bear</div>
        <div className="text-lg font-bold text-red-800">{v.bear_total}/12</div>
      </div>
    </div>
  );
}

function VerdictBlock({ title, v }: { title: string; v: Verdict }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-navy">{title}</span>
        <span className={`rounded px-2 py-0.5 text-xs font-bold text-white ${labelClass[v.label]}`}>{v.label}</span>
        <span className="text-xs text-slate-600">confidence {(v.confidence * 100).toFixed(0)}%</span>
        {v.override && (
          <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] text-amber-800" title="Anti-neutral rule">
            code override
          </span>
        )}
      </div>
      <Scores v={v} />
      <p className="text-sm text-slate-700">{v.rationale}</p>
      {v.verdict_changers.length > 0 && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">What would change the verdict</div>
          <ul className="ml-4 list-disc text-sm text-slate-700">
            {v.verdict_changers.map((c) => <li key={c}>{c}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function CauseRow({ c, i }: { c: CauseResult; i: number }) {
  return (
    <div className="rounded-md border border-slate-200 p-3">
      <div className="mb-2 text-xs text-slate-500">Cause {i + 1}: {c.cause_text}</div>
      <VerdictBlock title="Cause verdict" v={c.verdict} />
    </div>
  );
}

export default function VerdictCard({ report, live }: { report: Report | null; live: Record<string, Verdict> }) {
  const premise = report?.premise_verdict ?? live["premise"];
  if (!premise) return null;
  const fake = report?.cost.llm_provider === "fake" || report?.cost.retrieval_provider === "fake";
  return (
    <section aria-label="Verdict" className="w-full rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      {fake && (
        <div className="mb-3 rounded-md bg-amber-50 p-2 text-xs text-amber-900">
          Offline placeholder: produced with the fake LLM/retrieval, not a real model. Verdicts are not meaningful.
        </div>
      )}
      <VerdictBlock title="Premise verdict" v={premise} />
      {report && report.causes.length > 0 && (
        <div className="mt-4 space-y-3">{report.causes.map((c, i) => <CauseRow key={c.cause_text} c={c} i={i} />)}</div>
      )}
      {report && (
        <div className="mt-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">3 questions to ask</div>
          <ol className="ml-4 list-decimal text-sm text-slate-700">
            {report.questions_to_ask.map((q) => <li key={q}>{q}</li>)}
          </ol>
          <div className="mt-3 text-[11px] text-slate-500">
            {report.cost.llm_calls} LLM calls · {report.cost.retrieval_queries ?? "?"} searches · {report.cost.seconds}s ·{" "}
            {report.evidence.filter((e) => e.status === "UNVERIFIED").length} of {report.evidence.length} evidence items UNVERIFIED
          </div>
        </div>
      )}
    </section>
  );
}
