"use client";

import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import type { CourtNodeData } from "@/lib/graphState";

type CourtNode = Node<CourtNodeData>;

const sideClass = {
  bull: "border-green-600 bg-green-50",
  bear: "border-red-600 bg-red-50",
  neutral: "border-slate-400 bg-white",
} as const;

function Handles() {
  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-slate-400" />
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400" />
    </>
  );
}

export function ClaimNode({ data }: NodeProps<CourtNode>) {
  const p = data.payload;
  return (
    <div className="w-[260px] rounded-lg border-2 border-accent bg-white px-3 py-2 text-sm shadow">
      <Handles />
      <div className="text-[10px] font-semibold uppercase tracking-wide text-accent">
        On trial{p.input_type === "why-question" ? " · premise" : ""}
      </div>
      <div className="font-medium text-navy">{p.label}</div>
    </div>
  );
}

export function CauseNode({ data }: NodeProps<CourtNode>) {
  return (
    <div className="w-[260px] rounded-lg border-2 border-dashed border-accent bg-white px-3 py-2 text-sm shadow">
      <Handles />
      <div className="text-[10px] font-semibold uppercase tracking-wide text-accent">Candidate cause</div>
      <div className="text-navy">{data.payload.label}</div>
    </div>
  );
}

export function ArgumentNode({ data }: NodeProps<CourtNode>) {
  const p = data.payload;
  const side = p.side ?? "neutral";
  const stance = data.stance;
  return (
    <div className={`w-[240px] rounded-lg border-2 px-3 py-2 text-xs shadow-sm ${sideClass[side]}`}>
      <Handles />
      <div className="mb-1 flex items-center justify-between text-[10px] font-semibold uppercase">
        <span className={side === "bull" ? "text-green-700" : "text-red-700"}>
          {p.agent === "bull" ? "📈 Bull" : "📉 Bear"} · round {p.round}
          {p.agent && p.side !== p.agent ? " · switched" : ""}
        </span>
        {stance && stance.stance !== "hold" && (
          <span className="rounded bg-navy px-1.5 py-0.5 text-white" title={stance.reason}>
            {stance.stance}
          </span>
        )}
      </div>
      <div className="line-clamp-4 text-slate-800">{p.label}</div>
    </div>
  );
}

export function EvidenceNode({ data }: NodeProps<CourtNode>) {
  const p = data.payload;
  const pending = !p.status; // not fact-checked yet
  const unverified = p.status === "UNVERIFIED";
  const cls = unverified ? "border-slate-400 bg-slate-100 text-slate-500" : sideClass[p.side ?? "neutral"];
  return (
    <div className={`group relative w-[220px] rounded-md border px-2.5 py-2 text-[11px] shadow-sm ${cls}`}>
      <Handles />
      <div className="mb-1 flex items-center justify-between gap-1">
        <span className="truncate text-[10px] text-slate-500">{p.title}</span>
        {unverified ? (
          <span className="shrink-0 rounded bg-slate-500 px-1.5 py-0.5 text-[9px] font-bold text-white">UNVERIFIED</span>
        ) : (
          !pending && <span className="shrink-0 rounded bg-green-700 px-1.5 py-0.5 text-[9px] font-bold text-white">VERIFIED</span>
        )}
      </div>
      <div className={`line-clamp-3 ${unverified ? "line-through decoration-slate-400" : ""}`}>{p.label}</div>
      <div className="pointer-events-none absolute left-0 top-full z-50 mt-1 hidden w-[300px] rounded-md bg-navy p-3 text-[11px] text-white shadow-lg group-hover:block">
        <div className="mb-1 font-semibold">Verbatim quote</div>
        <div className="italic">“{p.quote}”</div>
        <div className="mt-2 truncate text-blue-200">{p.url}</div>
        {p.factcheck && <div className="mt-1 text-blue-200">Fact-check: {p.factcheck}</div>}
      </div>
    </div>
  );
}

export function VerdictNode({ data }: NodeProps<CourtNode>) {
  return (
    <div className="w-[280px] rounded-lg bg-navy px-4 py-3 text-center text-sm font-semibold text-white shadow-lg">
      <Handles />
      ⚖️ {data.payload.label}
    </div>
  );
}

export const nodeTypes = {
  claim: ClaimNode,
  cause: CauseNode,
  argument: ArgumentNode,
  evidence: EvidenceNode,
  verdict: VerdictNode,
};
