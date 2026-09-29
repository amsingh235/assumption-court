import type { CourtNodeData } from "@/lib/graphState";

/** Tap-friendly details for the selected node (hover tooltips don't exist on phones). */
export default function DetailsPanel({ data, onClose }: { data: CourtNodeData | null; onClose: () => void }) {
  if (!data) return null;
  const p = data.payload;
  return (
    <div className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm shadow-sm">
      <div className="mb-1 flex items-start justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {p.kind}{p.side ? ` · ${p.side}` : ""}{p.status ? ` · ${p.status}` : p.kind === "evidence" ? " · pending check" : ""}
        </span>
        <button onClick={onClose} className="text-xs text-slate-500 hover:text-navy" aria-label="Close details">✕</button>
      </div>
      <p className="text-slate-800">{p.label}</p>
      {p.quote && (
        <blockquote className="mt-2 border-l-4 border-accent pl-3 italic text-slate-700">“{p.quote}”</blockquote>
      )}
      {p.url && (
        <a href={p.url} target="_blank" rel="noopener noreferrer" className="mt-1 block truncate text-xs text-accent underline">
          {p.title || p.url}
        </a>
      )}
      {p.factcheck && <p className="mt-1 text-xs text-slate-500">Fact-check: {p.factcheck}</p>}
      {data.stance && data.stance.stance !== "hold" && (
        <p className="mt-1 text-xs text-slate-600">Stance: {data.stance.stance} ({data.stance.reason})</p>
      )}
    </div>
  );
}
