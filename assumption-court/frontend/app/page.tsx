"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AgentBench from "@/components/AgentBench";
import DetailsPanel from "@/components/DetailsPanel";
import InputBar from "@/components/InputBar";
import TrialGraph from "@/components/TrialGraph";
import VerdictCard from "@/components/VerdictCard";
import { getTrial, loadExamples, startTrial } from "@/lib/api";
import { applyEvent, applyEvents, emptyState, stageLabel, stagesOf, type CourtNodeData, type CourtState } from "@/lib/graphState";
import type { CachedCase, Report } from "@/lib/types";

type Phase = "idle" | "running" | "replaying" | "done" | "error";
const POLL_MS = 1500;
const REPLAY_MS = 120;

export default function Home() {
  const [court, setCourt] = useState<CourtState>(emptyState);
  const [phase, setPhase] = useState<Phase>("idle");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [examples, setExamples] = useState<CachedCase[]>([]);
  const [selected, setSelected] = useState<CourtNodeData | null>(null);
  const [pinnedStage, setPinnedStage] = useState<string | null>(null); // null = follow the latest stage
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    loadExamples().then(setExamples).catch(() => setExamples([]));
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  const reset = () => {
    if (timer.current) clearTimeout(timer.current);
    setCourt(emptyState());
    setReport(null);
    setError(null);
    setSelected(null);
    setPinnedStage(null);
  };

  const runLive = useCallback(async (text: string) => {
    reset();
    setPhase("running");
    try {
      const jobId = await startTrial(text);
      const poll = async () => {
        try {
          const job = await getTrial(jobId);
          setCourt((s) => applyEvents(s, job.events));
          if (job.status === "done") {
            setReport(job.report);
            setCourt((s) => ({ ...s, activeAgent: null, statusLine: "Verdict delivered." }));
            setPhase("done");
          } else if (job.status === "error") {
            setError(job.error ?? "The trial failed.");
            setPhase("error");
          } else {
            timer.current = setTimeout(poll, POLL_MS);
          }
        } catch (e) {
          setError(`Lost contact with the court: ${(e as Error).message}. Try an example.`);
          setPhase("error");
        }
      };
      await poll();
    } catch (e) {
      setError(`${(e as Error).message}`.includes("fetch") ? "The backend is unreachable. Try an example." : (e as Error).message);
      setPhase("error");
    }
  }, []);

  const replay = useCallback((c: CachedCase) => {
    reset();
    setPhase("replaying");
    const events = [...c.events].sort((a, b) => a.seq - b.seq);
    let i = 0;
    const step = () => {
      if (i >= events.length) {
        setReport(c.report);
        setCourt((s) => ({ ...s, activeAgent: null, statusLine: "Replay finished." }));
        setPhase("done");
        return;
      }
      const ev = events[i++];
      setCourt((s) => applyEvent(s, ev));
      timer.current = setTimeout(step, REPLAY_MS);
    };
    step();
  }, []);

  const busy = phase === "running" || phase === "replaying";
  const stages = stagesOf(court);
  const stage = pinnedStage ?? stages[stages.length - 1] ?? "premise";
  const visibleNodes = court.nodes.filter((n) => n.data.payload.stage === stage);
  const visibleIds = new Set(visibleNodes.map((n) => n.id));
  const visibleEdges = court.edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));

  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-navy px-4 py-3 text-white">
        <div className="mx-auto flex max-w-6xl items-baseline justify-between gap-2">
          <h1 className="text-lg font-bold">⚖️ Assumption Court</h1>
          <p className="hidden text-xs text-blue-200 sm:block">Every claim grounded in a retrieved quote. Unverified evidence doesn&apos;t count.</p>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 px-4 py-4">
        <AgentBench active={court.activeAgent} statusLine={court.statusLine} />

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
        )}
        {court.retrievalFailed && (
          <div role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Retrieval failed for part of this trial: no sources were found, so that verdict is INCONCLUSIVE. Nothing was made up.
          </div>
        )}

        {phase === "idle" ? (
          <div className="flex h-[40vh] items-center justify-center rounded-xl border border-dashed border-slate-300 text-center text-sm text-slate-500">
            <p className="max-w-md px-4">
              Type an assumption (or a “why” question) below, or replay an example. The court retrieves sources, argues both
              sides, throws out anything a quote doesn&apos;t support, and scores what is left.
            </p>
          </div>
        ) : (
          <>
            {phase === "running" && court.nodes.length === 0 && (
              <p className="text-center text-sm text-slate-500">Convening the court…</p>
            )}
            {stages.length > 1 && (
              <div role="tablist" aria-label="Trial stages" className="flex gap-1 overflow-x-auto">
                {stages.map((st) => (
                  <button
                    key={st}
                    role="tab"
                    aria-selected={st === stage}
                    onClick={() => setPinnedStage(st)}
                    className={`shrink-0 rounded-md px-3 py-1 text-xs font-semibold ${
                      st === stage ? "bg-navy text-white" : "bg-slate-100 text-navy hover:bg-slate-200"
                    }`}
                  >
                    {stageLabel(st)}
                    {court.verdicts[st] ? ` · ${court.verdicts[st].label}` : ""}
                  </button>
                ))}
              </div>
            )}
            <TrialGraph nodes={visibleNodes} edges={visibleEdges} onSelect={setSelected} />
            <DetailsPanel data={selected} onClose={() => setSelected(null)} />
          </>
        )}

        <VerdictCard report={report} live={court.verdicts} />
      </main>

      <InputBar busy={busy} examples={examples} onSubmit={runLive} onExample={replay} />
    </div>
  );
}
