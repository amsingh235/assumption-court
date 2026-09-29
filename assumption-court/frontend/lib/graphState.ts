import type { Edge, Node } from "@xyflow/react";
import type {
  AgentName,
  EdgeAddPayload,
  GraphEvent,
  NodeAddPayload,
  StancePayload,
  StatusPayload,
  Verdict,
  VerdictPayload,
} from "./types";

export interface CourtNodeData extends Record<string, unknown> {
  payload: NodeAddPayload;
  stance?: StancePayload;
}

export interface CourtState {
  nodes: Node<CourtNodeData>[];
  edges: Edge[];
  lastSeq: number;
  activeAgent: AgentName | null;
  statusLine: string;
  verdicts: Record<string, Verdict>;
  retrievalFailed: boolean;
  stances: StancePayload[];
  // layout bookkeeping
  slots: Record<string, number>;
  maxRound: Record<string, number>;
}

export const emptyState = (): CourtState => ({
  nodes: [],
  edges: [],
  lastSeq: 0,
  activeAgent: null,
  statusLine: "",
  verdicts: {},
  retrievalFailed: false,
  stances: [],
  slots: {},
  maxRound: {},
});

const ROUND_H = 330;
const AGENTS: AgentName[] = ["researcher", "bull", "bear", "factchecker", "judge"];

// Each stage (premise, cause:1..3) is shown on its own tab, so every stage is laid out from y=0.
function stageBase(): number {
  return 0;
}

export function stageLabel(stage: string): string {
  return stage === "premise" ? "Premise" : `Cause ${stage.split(":")[1]}`;
}

export function stagesOf(state: CourtState): string[] {
  const seen: string[] = [];
  for (const n of state.nodes) if (!seen.includes(n.data.payload.stage)) seen.push(n.data.payload.stage);
  return seen;
}

function nextSlot(state: CourtState, key: string): number {
  const n = state.slots[key] ?? 0;
  state.slots[key] = n + 1;
  return n;
}

function position(state: CourtState, p: NodeAddPayload): { x: number; y: number } {
  const base = stageBase();
  const round = p.round ?? state.maxRound[p.stage] ?? 1;
  const bull = p.side === "bull";
  switch (p.kind) {
    case "claim":
    case "cause":
      return { x: -130, y: base };
    case "argument": {
      state.maxRound[p.stage] = Math.max(state.maxRound[p.stage] ?? 0, round);
      const n = nextSlot(state, `${p.stage}|arg|${round}|${p.side}`);
      return { x: (bull ? -520 : 260) + n * 40, y: base + 170 + (round - 1) * ROUND_H + n * 30 };
    }
    case "evidence": {
      const n = nextSlot(state, `${p.stage}|ev|${round}|${p.side}`);
      return { x: bull ? -780 + n * 235 : 40 + n * 235, y: base + 330 + (round - 1) * ROUND_H };
    }
    case "verdict":
      return { x: -150, y: base + 170 + (state.maxRound[p.stage] ?? 1) * ROUND_H + 60 };
  }
}

function edgeStyle(kind: EdgeAddPayload["kind"]): Partial<Edge> {
  switch (kind) {
    case "supports":
      return { style: { stroke: "#78716c" } };
    case "rebuts":
      return { style: { stroke: "#f59e0b" }, animated: true, label: "rebuts" };
    case "stance":
      return { style: { stroke: "#d97757", strokeDasharray: "6 4" }, label: "stance" };
    case "verdict":
      return { style: { stroke: "#d97757", strokeWidth: 2 } };
    default:
      return { style: { stroke: "#57534e" } };
  }
}

function isAgent(name: string | undefined): name is AgentName {
  return !!name && (AGENTS as string[]).includes(name);
}

/** Apply one event. Returns a new state object (arrays are copied where changed). */
export function applyEvent(prev: CourtState, event: GraphEvent): CourtState {
  if (event.seq <= prev.lastSeq) return prev;
  const state: CourtState = { ...prev, lastSeq: event.seq, slots: { ...prev.slots }, maxRound: { ...prev.maxRound } };

  if (event.type === "node_add") {
    const p = event.payload as unknown as NodeAddPayload;
    if (state.nodes.some((n) => n.id === p.id)) return state;
    state.nodes = [...state.nodes, { id: p.id, type: p.kind, position: position(state, p), data: { payload: p } }];
    if (p.kind === "argument" && isAgent(p.agent)) state.activeAgent = p.agent;
  } else if (event.type === "edge_add") {
    const p = event.payload as unknown as EdgeAddPayload;
    state.edges = [...state.edges, { id: p.id, source: p.source, target: p.target, ...edgeStyle(p.kind) }];
  } else if (event.type === "status") {
    const p = event.payload as unknown as StatusPayload;
    if (p.evidence_id) {
      state.nodes = state.nodes.map((n) =>
        n.id === p.evidence_id
          ? { ...n, data: { ...n.data, payload: { ...n.data.payload, status: p.status, factcheck: p.factcheck } } }
          : n,
      );
      state.activeAgent = "factchecker";
    } else {
      if (isAgent(p.agent)) state.activeAgent = p.agent;
      if (p.message) state.statusLine = p.message;
      if (p.retrieval_failed) state.retrievalFailed = true;
    }
  } else if (event.type === "stance") {
    const p = event.payload as unknown as StancePayload;
    state.stances = [...state.stances, p];
    state.nodes = state.nodes.map((n) => (n.id === p.argument_id ? { ...n, data: { ...n.data, stance: p } } : n));
  } else if (event.type === "verdict") {
    const p = event.payload as unknown as VerdictPayload;
    state.verdicts = { ...state.verdicts, [p.stage]: p.verdict };
    state.activeAgent = "judge";
  }
  return state;
}

export function applyEvents(state: CourtState, events: GraphEvent[]): CourtState {
  return [...events].sort((a, b) => a.seq - b.seq).reduce(applyEvent, state);
}
