// Courtroom scene state, derived purely from the backend GraphEvent stream (same events as graphState.ts).
import type {
  AgentName,
  EdgeAddPayload,
  EvidenceStatus,
  FactCheck,
  GraphEvent,
  NodeAddPayload,
  Side,
  StancePayload,
  StatusPayload,
  Verdict,
  VerdictPayload,
} from "./types";

export type Speaker = AgentName | "court";
export type Tone = "neutral" | "good" | "bad";

export interface Utterance {
  id: string;
  seq: number;
  agent: Speaker;
  text: string;
  stage: string;
  tone: Tone;
  evidenceId?: string;
}

export interface Exhibit {
  id: string;
  stage: string;
  round: number;
  side: Side;
  claim: string;
  quote: string;
  url: string;
  title: string;
  status: EvidenceStatus | null; // null = not fact-checked yet
  factcheck: FactCheck | null;
  reason: string;
}

export type Spot = "home" | "floor";

export interface SceneState {
  lastSeq: number;
  stage: string;
  round: number;
  onTrial: string; // premise or current cause text
  speaker: Speaker | null;
  bubble: Utterance | null;
  spots: Record<AgentName, Spot>;
  podium: Record<"bull" | "bear", "left" | "right">; // which podium each debater stands at (switch moves it)
  conceded: Record<"bull" | "bear", boolean>;
  shake: { agent: AgentName; seq: number } | null;
  exhibits: Exhibit[];
  transcript: Utterance[];
  ruling: { stage: string; verdict: Verdict; seq: number } | null;
  argAgent: Record<string, "bull" | "bear">;
}

const HOME: Record<AgentName, Spot> = { researcher: "home", bull: "home", bear: "home", factchecker: "home", judge: "home" };

export const emptyScene = (): SceneState => ({
  lastSeq: 0,
  stage: "premise",
  round: 0,
  onTrial: "",
  speaker: null,
  bubble: null,
  spots: { ...HOME },
  podium: { bull: "left", bear: "right" },
  conceded: { bull: false, bear: false },
  shake: null,
  exhibits: [],
  transcript: [],
  ruling: null,
  argAgent: {},
});

const AGENTS = new Set<string>(["researcher", "bull", "bear", "factchecker", "judge"]);
const short = (t: string, n = 70) => (t.length > n ? `${t.slice(0, n - 1)}…` : t);

function say(s: SceneState, ev: GraphEvent, agent: Speaker, text: string, tone: Tone = "neutral", evidenceId?: string) {
  const u: Utterance = { id: `u${ev.seq}`, seq: ev.seq, agent, text, stage: s.stage, tone, evidenceId };
  s.transcript = [...s.transcript, u];
  s.bubble = u;
  s.speaker = agent;
  s.spots = { ...HOME };
  if (agent !== "court" && agent !== "judge") s.spots[agent] = "floor";
}

function newStage(s: SceneState, stage: string, onTrial: string) {
  s.stage = stage;
  s.onTrial = onTrial;
  s.round = 0;
  s.podium = { bull: "left", bear: "right" };
  s.conceded = { bull: false, bear: false };
  s.ruling = null;
}

export function applySceneEvent(prev: SceneState, ev: GraphEvent): SceneState {
  if (ev.seq <= prev.lastSeq) return prev;
  const s: SceneState = { ...prev, lastSeq: ev.seq };

  switch (ev.type) {
    case "node_add": {
      const p = ev.payload as unknown as NodeAddPayload;
      if (p.kind === "claim") {
        newStage(s, "premise", p.label);
        say(s, ev, "court", `On trial: “${p.label}”`);
      } else if (p.kind === "cause") {
        newStage(s, p.stage, p.label);
        say(s, ev, "court", `Next on trial, a candidate cause: “${p.label}”`);
      } else if (p.kind === "argument" && p.agent) {
        s.round = p.round ?? s.round;
        s.argAgent = { ...s.argAgent, [p.id]: p.agent };
        say(s, ev, p.agent, p.label, p.side === "bull" ? "good" : "bad");
      } else if (p.kind === "evidence") {
        s.exhibits = [
          ...s.exhibits,
          {
            id: p.id, stage: p.stage, round: p.round ?? s.round, side: p.side ?? "neutral", claim: p.label,
            quote: p.quote ?? "", url: p.url ?? "", title: p.title ?? "", status: null, factcheck: null, reason: "",
          },
        ];
      }
      break;
    }
    case "edge_add": {
      const p = ev.payload as unknown as EdgeAddPayload;
      const target = s.argAgent[p.target];
      if (p.kind === "rebuts" && target) s.shake = { agent: target, seq: ev.seq };
      break;
    }
    case "status": {
      const p = ev.payload as unknown as StatusPayload & { reason?: string };
      if (p.evidence_id) {
        const ex = s.exhibits.find((e) => e.id === p.evidence_id);
        s.exhibits = s.exhibits.map((e) =>
          e.id === p.evidence_id
            ? { ...e, status: p.status ?? null, factcheck: p.factcheck ?? null, reason: p.reason ?? "" }
            : e,
        );
        const ok = p.status === "VERIFIED";
        const what = ex ? `“${short(ex.claim)}”` : "that exhibit";
        const text = ok
          ? `Exhibit ${what}: the quote supports it. Admitted ✓`
          : `Exhibit ${what}: ${p.factcheck}. Not admitted ✗${p.reason ? ` (${p.reason})` : ""}`;
        say(s, ev, "factchecker", text, ok ? "good" : "bad", p.evidence_id);
      } else if (p.message) {
        const agent: Speaker = p.agent && AGENTS.has(p.agent) ? (p.agent as AgentName) : "court";
        // Debaters announce their round via their argument itself; skip the redundant status line.
        if (agent === "bull" || agent === "bear") break;
        if (p.stage === "final") {
          // Housekeeping after the last ruling: log it, but keep the ruling on stage.
          s.transcript = [...s.transcript, { id: `u${ev.seq}`, seq: ev.seq, agent, text: p.message, stage: s.stage, tone: "neutral" }];
          break;
        }
        say(s, ev, agent, p.message, p.retrieval_failed ? "bad" : "neutral");
      }
      break;
    }
    case "stance": {
      const p = ev.payload as unknown as StancePayload;
      if (p.stance === "concede") {
        s.conceded = { ...s.conceded, [p.agent]: true };
        say(s, ev, p.agent, `I concede. ${p.reason}`, "bad");
        s.spots = { ...HOME };
      } else if (p.stance === "switch") {
        s.podium = { ...s.podium, [p.agent]: s.podium[p.agent] === "left" ? "right" : "left" };
        say(s, ev, p.agent, `I'm switching sides. ${p.reason}`, "neutral");
      }
      break;
    }
    case "verdict": {
      const p = ev.payload as unknown as VerdictPayload;
      s.ruling = { stage: p.stage, verdict: p.verdict, seq: ev.seq };
      say(s, ev, "judge", `${p.verdict.label}. ${p.verdict.rationale}`,
        p.verdict.label === "SUPPORTED" ? "good" : p.verdict.label === "REFUTED" ? "bad" : "neutral");
      break;
    }
  }
  return s;
}

/** How long the stage should dwell on this event before playing the next one (ms, at 1x). */
export function dwellMs(ev: GraphEvent): number {
  const p = ev.payload as Record<string, unknown>;
  const talky =
    (ev.type === "node_add" && ["argument", "claim", "cause"].includes(p.kind as string)) ||
    (ev.type === "status" && p.stage !== "final" && (!!p.evidence_id || (!!p.message && p.agent !== "bull" && p.agent !== "bear"))) ||
    (ev.type === "stance" && p.stance !== "hold") ||
    ev.type === "verdict";
  if (!talky) return 90;
  const text = String(p.label ?? p.message ?? p.reason ?? (p.verdict as Verdict | undefined)?.rationale ?? "");
  const base = ev.type === "verdict" ? 2600 : 900;
  return Math.min(5200, base + text.length * 22);
}
