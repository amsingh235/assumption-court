"use client";

import { useEffect, useRef, useState } from "react";
import PixelAgent, { type Pose } from "./pixel/PixelAgent";
import SpeechBubble from "./SpeechBubble";
import ExhibitCard, { ExhibitDetail } from "./ExhibitCard";
import { AGENT_INFO } from "@/lib/agents";
import type { SceneState, Speaker } from "@/lib/scene";
import type { AgentName } from "@/lib/types";

type Pt = { x: number; y: number }; // % of the stage

// Stage coordinates (% of the stage box). The speech bubble sits at y≈21-42%, between the bench and the podiums.
const JUDGE: Pt = { x: 50, y: 10 };
const DESK: Record<"researcher" | "factchecker", { home: Pt; floor: Pt }> = {
  researcher: { home: { x: 8, y: 58 }, floor: { x: 43, y: 62 } },
  factchecker: { home: { x: 92, y: 58 }, floor: { x: 57, y: 62 } },
};
const PODIUM = {
  left: { home: { x: 24, y: 52 }, floor: { x: 38, y: 58 } },
  right: { home: { x: 76, y: 52 }, floor: { x: 62, y: 58 } },
};

function target(agent: AgentName, scene: SceneState): Pt {
  if (agent === "judge") return JUDGE;
  const spot = scene.spots[agent];
  if (agent === "bull" || agent === "bear") return PODIUM[scene.podium[agent]][spot];
  return DESK[agent][spot];
}

/** One sprite that walks (CSS transition on left/top) whenever its target spot changes. */
function Actor({ agent, pt, pose, shakeKey, dim, faceLeft }: {
  agent: AgentName; pt: Pt; pose: Pose; shakeKey: number; dim: boolean; faceLeft: boolean;
}) {
  const [walking, setWalking] = useState(false);
  const last = useRef(pt);
  useEffect(() => {
    if (last.current.x === pt.x && last.current.y === pt.y) return;
    last.current = pt;
    const start = setTimeout(() => setWalking(true), 0);
    const end = setTimeout(() => setWalking(false), 750);
    return () => {
      clearTimeout(start);
      clearTimeout(end);
    };
  }, [pt]);
  return (
    <div
      className="absolute z-10 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center transition-[left,top] duration-700 ease-in-out"
      style={{ left: `${pt.x}%`, top: `${pt.y}%` }}
    >
      <div key={shakeKey} className={`${shakeKey ? "px-shake" : ""} ${dim ? "opacity-50" : ""}`}>
        <PixelAgent
          id={agent}
          pose={walking ? "walk" : pose}
          size={88}
          flip={faceLeft}
          className="h-[52px] w-[52px] drop-shadow-[0_6px_0_rgba(0,0,0,0.35)] sm:h-[88px] sm:w-[88px]"
          title={AGENT_INFO[agent].name}
        />
      </div>
      <span className="font-pixel mt-1 rounded bg-ink/70 px-1.5 py-0.5 text-[8px] text-cream sm:text-[10px]">
        {AGENT_INFO[agent].name}
      </span>
    </div>
  );
}

const labelColor = { SUPPORTED: "text-green-400", REFUTED: "text-red-400", INCONCLUSIVE: "text-cream" } as const;

export default function Courtroom({ scene, speed, idle, openId, onOpen }: {
  scene: SceneState; speed: number; idle: boolean; openId: string | null; onOpen: (id: string | null) => void;
}) {
  const open = openId ? scene.exhibits.find((e) => e.id === openId) : undefined;
  const agents: AgentName[] = ["judge", "researcher", "bull", "bear", "factchecker"];
  const speaker: Speaker | null = scene.speaker;
  const stageExhibits = scene.exhibits.filter((e) => e.stage === scene.stage && e.round === scene.round).slice(-6);
  const notAdmitted = scene.exhibits.filter((e) => e.stage === scene.stage && e.status === "UNVERIFIED").length;
  const speakerX = speaker && speaker !== "court" ? target(speaker, scene).x : 50;
  const ruling = scene.ruling && scene.ruling.stage === scene.stage ? scene.ruling : null;

  const hint = {
    id: "hint", seq: 0, agent: "court" as const, stage: "premise", tone: "neutral" as const,
    text: "The court is in recess. Put an assumption on trial below, or replay an example.",
  };
  const bubble = idle ? hint : scene.bubble;

  return (
    <div className="relative h-[460px] w-full overflow-hidden rounded-2xl border-4 border-ink bg-[radial-gradient(ellipse_at_50%_0%,#3a302a_0%,#26211d_55%,#1c1917_100%)] lg:h-[max(480px,calc(100vh-370px))]">
      {/* floor + furniture */}
      <div className="absolute inset-x-0 bottom-0 h-[42%] bg-[repeating-linear-gradient(90deg,#3b2a20_0_46px,#342519_46px_92px)] opacity-70" />
      <div className="absolute left-1/2 top-[16%] h-[5%] w-[26%] -translate-x-1/2 rounded-t-md bg-wood shadow-[0_6px_0_#4a2c1c]" />
      <div className="absolute left-[24%] top-[62%] h-[5%] w-[11%] -translate-x-1/2 rounded-t-md bg-wood/80" />
      <div className="absolute left-[76%] top-[62%] h-[5%] w-[11%] -translate-x-1/2 rounded-t-md bg-wood/80" />
      <div className="font-pixel absolute left-[24%] top-[68%] -translate-x-1/2 text-[8px] text-green-400/80 sm:text-[10px]">BULL</div>
      <div className="font-pixel absolute left-[76%] top-[68%] -translate-x-1/2 text-[8px] text-red-400/80 sm:text-[10px]">BEAR</div>

      {/* speech bubble */}
      {bubble && (
        <div className="absolute left-1/2 top-[22%] z-20 w-[92%] -translate-x-1/2 sm:w-[62%]">
          <SpeechBubble key={bubble.id} u={bubble} tailX={speakerX} speed={speed} />
        </div>
      )}

      {agents.map((a) => {
        const talking = speaker === a;
        const conceded = (a === "bull" || a === "bear") && scene.conceded[a];
        const pose: Pose = a === "judge" && ruling && talking ? "gavel" : conceded ? "flag" : talking ? "talk" : "idle";
        const pt = target(a, scene);
        return (
          <Actor
            key={a}
            agent={a}
            pt={pt}
            pose={pose}
            shakeKey={scene.shake?.agent === a ? scene.shake.seq : 0}
            dim={conceded}
            faceLeft={pt.x > 55}
          />
        );
      })}

      {/* ruling banner */}
      {ruling && (speaker === "judge" || speaker === "court") && (
        <div key={ruling.seq} className="gavel-in font-pixel absolute left-1/2 top-[60%] z-30 -translate-x-1/2 rounded-lg border-4 border-clay bg-ink px-4 py-2 text-center shadow-2xl">
          <div className={`text-lg sm:text-2xl ${labelColor[ruling.verdict.label]}`}>{ruling.verdict.label}</div>
          <div className="text-[9px] text-cream/80 sm:text-[11px]">
            Bull {ruling.verdict.bull_total} · Bear {ruling.verdict.bear_total} · {(ruling.verdict.confidence * 100).toFixed(0)}%
          </div>
        </div>
      )}

      {/* exhibits table */}
      <div className="absolute inset-x-0 bottom-0 z-10 px-3 pb-3">
        <div className="mb-1 flex items-center justify-between">
          <span className="font-pixel text-[9px] text-cream/60 sm:text-[10px]">EXHIBITS</span>
          {notAdmitted > 0 && (
            <span className="font-pixel text-[9px] text-slate-400 sm:text-[10px]">NOT ADMITTED: {notAdmitted}</span>
          )}
        </div>
        <div className="flex min-h-[64px] gap-2 overflow-x-auto pb-1">
          {stageExhibits.length === 0 ? (
            <span className="self-center text-xs text-cream/30">No exhibits on the table yet.</span>
          ) : (
            stageExhibits.map((ex) => <ExhibitCard key={ex.id} ex={ex} onOpen={(e) => onOpen(e.id)} />)
          )}
        </div>
      </div>

      {open && <ExhibitDetail ex={open} onClose={() => onOpen(null)} />}
    </div>
  );
}
