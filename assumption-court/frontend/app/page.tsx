"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AgentsHeader from "@/components/AgentsHeader";
import Courtroom from "@/components/Courtroom";
import InputBar from "@/components/InputBar";
import PlaybackControls from "@/components/PlaybackControls";
import Transcript from "@/components/Transcript";
import TrialGraph from "@/components/TrialGraph";
import VerdictCard from "@/components/VerdictCard";
import { getTrial, loadExamples, startTrial } from "@/lib/api";
import { stageLabel, stagesOf } from "@/lib/graphState";
import { usePlayback } from "@/lib/usePlayback";
import type { CachedCase, Report } from "@/lib/types";

type Mode = "idle" | "live" | "replay";
type RailTab = "transcript" | "graph";
const POLL_MS = 1500;

export default function Home() {
  const pb = usePlayback();
  const [mode, setMode] = useState<Mode>("idle");
  const [jobDone, setJobDone] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [examples, setExamples] = useState<CachedCase[]>([]);
  const [tab, setTab] = useState<RailTab>("transcript");
  const [pinnedStage, setPinnedStage] = useState<string | null>(null);
  const [openExhibit, setOpenExhibit] = useState<string | null>(null);
  const poller = useRef<ReturnType<typeof setTimeout> | null>(null);
  const run = useRef(0); // invalidates stale polls when a new trial starts

  useEffect(() => {
    loadExamples().then(setExamples).catch(() => setExamples([]));
    return () => {
      if (poller.current) clearTimeout(poller.current);
    };
  }, []);

  const start = (m: Mode) => {
    if (poller.current) clearTimeout(poller.current);
    run.current += 1;
    pb.reset();
    setMode(m);
    setJobDone(false);
    setReport(null);
    setError(null);
    setPinnedStage(null);
    setOpenExhibit(null);
    return run.current;
  };

  const runLive = useCallback(async (text: string) => {
    const id = start("live");
    try {
      const jobId = await startTrial(text);
      const poll = async () => {
        if (id !== run.current) return;
        try {
          const job = await getTrial(jobId);
          if (id !== run.current) return;
          pb.enqueue(job.events);
          if (job.status === "done") {
            setReport(job.report);
            setJobDone(true);
          } else if (job.status === "error") {
            setError(job.error ?? "The trial failed.");
            setJobDone(true);
          } else {
            poller.current = setTimeout(poll, POLL_MS);
          }
        } catch (e) {
          setError(`Lost contact with the court (${(e as Error).message}). Try an example.`);
          setJobDone(true);
        }
      };
      await poll();
    } catch (e) {
      const msg = (e as Error).message;
      setError(/fetch|network/i.test(msg) ? "The court's backend is unreachable. Replay an example instead." : msg);
      setJobDone(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const replay = useCallback((c: CachedCase) => {
    start("replay");
    setReport(c.report);
    setJobDone(true);
    pb.enqueue(c.events);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const finished = jobDone && !pb.playing && pb.pending === 0;
  const busy = mode !== "idle" && !finished;
  const { court, scene } = pb;

  const stages = stagesOf(court);
  const graphStage = pinnedStage ?? stages[stages.length - 1] ?? "premise";
  const visibleNodes = court.nodes.filter((n) => n.data.payload.stage === graphStage);
  const visibleIds = new Set(visibleNodes.map((n) => n.id));
  const visibleEdges = court.edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));

  const railTab = (t: RailTab, label: string) => (
    <button
      role="tab"
      aria-selected={tab === t}
      onClick={() => setTab(t)}
      className={`font-pixel flex-1 px-3 py-2 text-[11px] ${tab === t ? "bg-cream text-ink" : "text-cream/60 hover:text-cream"}`}
    >
      {label}
    </button>
  );

  return (
    <div className="flex min-h-screen flex-col">
      <AgentsHeader active={mode === "idle" || finished ? null : scene.speaker} />

      <main className="mx-auto mt-4 flex w-full max-w-[1500px] flex-1 flex-col gap-3 px-4 pb-4">
        {/* stage bar */}
        <div className="flex flex-col gap-2 rounded-xl bg-coal px-4 py-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <span className="font-pixel mr-2 text-[11px] text-clay">
              {mode === "idle" ? "COURT IN RECESS" : `${stageLabel(scene.stage).toUpperCase()}${scene.round ? ` · ROUND ${scene.round}` : ""}`}
            </span>
            {scene.onTrial && <span className="text-sm text-cream/80">On trial: “{scene.onTrial}”</span>}
          </div>
          <PlaybackControls speed={pb.speed} onSpeed={pb.setSpeed} onSkip={pb.skip} pending={pb.pending} disabled={mode === "idle"} />
        </div>

        {error && (
          <div role="alert" className="rounded-xl border border-red-400/40 bg-red-500/10 p-3 text-sm text-red-200">{error}</div>
        )}
        {court.retrievalFailed && (
          <div role="status" className="rounded-xl border border-amber-400/40 bg-amber-400/10 p-3 text-sm text-amber-100">
            Retrieval failed for part of this trial: no sources were found, so that verdict is INCONCLUSIVE. Nothing was made up.
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_420px]">
          <Courtroom scene={scene} speed={pb.speed} idle={mode === "idle"} openId={openExhibit} onOpen={setOpenExhibit} />

          <aside className="flex h-[520px] flex-col overflow-hidden rounded-2xl border-4 border-ink bg-coal lg:h-[max(480px,calc(100vh-370px))]">
            <div role="tablist" aria-label="Court record" className="flex border-b border-white/10">
              {railTab("transcript", "Transcript")}
              {railTab("graph", "Evidence graph")}
            </div>
            {tab === "transcript" ? (
              <div data-scroll className="min-h-0 flex-1 overflow-y-auto">
                <Transcript items={scene.transcript} onEvidence={setOpenExhibit} />
              </div>
            ) : (
              <div className="flex min-h-0 flex-1 flex-col">
                {stages.length > 1 && (
                  <div role="tablist" aria-label="Trial stages" className="flex gap-1 overflow-x-auto p-2">
                    {stages.map((st) => (
                      <button
                        key={st}
                        role="tab"
                        aria-selected={st === graphStage}
                        onClick={() => setPinnedStage(st)}
                        className={`font-pixel shrink-0 rounded-md px-2 py-1 text-[10px] ${
                          st === graphStage ? "bg-clay text-ink" : "bg-white/10 text-cream/70 hover:bg-white/20"
                        }`}
                      >
                        {stageLabel(st)}
                        {court.verdicts[st] ? ` · ${court.verdicts[st].label}` : ""}
                      </button>
                    ))}
                  </div>
                )}
                <div className="min-h-0 flex-1">
                  {court.nodes.length ? (
                    <TrialGraph nodes={visibleNodes} edges={visibleEdges} onSelect={(d) => d?.payload.kind === "evidence" && setOpenExhibit(d.payload.id)} />
                  ) : (
                    <p className="p-6 text-center text-sm text-cream/40">The evidence graph builds as exhibits are entered.</p>
                  )}
                </div>
              </div>
            )}
          </aside>
        </div>

        {finished && <VerdictCard report={report} />}
      </main>

      <InputBar busy={busy} examples={examples} onSubmit={runLive} onExample={replay} />
    </div>
  );
}
