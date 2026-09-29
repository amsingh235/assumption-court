import type { AgentName } from "./types";

export const AGENT_INFO: Record<AgentName, { name: string; role: string }> = {
  researcher: { name: "Researcher", role: "finds sources" },
  bull: { name: "Bull", role: "argues it holds" },
  judge: { name: "Judge", role: "scores & rules" },
  bear: { name: "Bear", role: "argues it fails" },
  factchecker: { name: "Fact-checker", role: "checks quotes" },
};

// Header order: debaters flank the judge.
export const AGENT_ORDER: AgentName[] = ["researcher", "bull", "judge", "bear", "factchecker"];
