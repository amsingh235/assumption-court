// Mirrors backend/app/models.py and backend/app/graph_events.py — change both together.

export type Side = "bull" | "bear" | "neutral";
export type FactCheck = "verified" | "mismatched" | "unverifiable";
export type EvidenceStatus = "VERIFIED" | "UNVERIFIED";
export type Stance = "hold" | "concede" | "switch";
export type VerdictLabel = "SUPPORTED" | "REFUTED" | "INCONCLUSIVE";
export type InputType = "assumption" | "why-question";
export type EventType = "node_add" | "edge_add" | "status" | "stance" | "verdict";
export type JobStatus = "queued" | "running" | "done" | "error";
export type AgentName = "researcher" | "bull" | "bear" | "factchecker" | "judge";

export interface Evidence {
  id: string;
  side: Side;
  claim_text: string;
  source_url: string;
  source_title: string;
  retrieved_quote: string;
  retrieved_at: string;
  factcheck: FactCheck;
  status: EvidenceStatus;
  source_tier: number | null;
  recency: number | null;
}

export interface Argument {
  id: string;
  agent: "bull" | "bear";
  round: number;
  text: string;
  evidence_ids: string[];
  stance: Stance;
  stance_reason: string;
}

export interface Verdict {
  label: VerdictLabel;
  bull_total: number;
  bear_total: number;
  gap: number;
  confidence: number;
  rationale: string;
  verdict_changers: string[];
  override: boolean;
}

export interface CauseResult {
  cause_text: string;
  verdict: Verdict;
  evidence_ids: string[];
}

export interface Report {
  input_text: string;
  input_type: InputType;
  premise_verdict: Verdict;
  causes: CauseResult[];
  evidence: Evidence[];
  arguments: Argument[];
  questions_to_ask: string[];
  cost: {
    llm_calls: number;
    tokens: number | null;
    seconds: number;
    retrieval_queries?: number;
    llm_provider?: string;
    retrieval_provider?: string;
    [key: string]: unknown;
  };
}

// Event payloads (see graph_events.py docstring).
export interface NodeAddPayload {
  id: string;
  kind: "claim" | "argument" | "evidence" | "cause" | "verdict";
  label: string;
  stage: string;
  side?: Side;
  round?: number;
  agent?: "bull" | "bear";
  status?: EvidenceStatus | null; // null = pending fact-check
  factcheck?: FactCheck | null;
  quote?: string;
  url?: string;
  title?: string;
  input_type?: InputType;
}

export interface EdgeAddPayload {
  id: string;
  source: string;
  target: string;
  kind: "supports" | "rebuts" | "stance" | "about" | "verdict";
}

export interface StatusPayload {
  agent?: string;
  message?: string;
  stage: string;
  evidence_id?: string;
  factcheck?: FactCheck;
  status?: EvidenceStatus;
  retrieval_failed?: boolean;
}

export interface StancePayload {
  agent: "bull" | "bear";
  stance: Stance;
  reason: string;
  round: number;
  argument_id: string;
  stage: string;
  side_now: string;
}

export interface VerdictPayload {
  stage: string;
  node_id: string;
  verdict: Verdict;
}

export interface GraphEvent {
  seq: number;
  type: EventType;
  payload: Record<string, unknown>;
  ts: string;
}

export interface TrialJob {
  job_id: string;
  status: JobStatus;
  events: GraphEvent[];
  report: Report | null;
  error: string | null;
}

export interface CachedCase {
  id: string;
  title: string;
  generated_at?: string;
  llm_provider?: string;
  retrieval_provider?: string;
  events: GraphEvent[];
  report: Report;
}
