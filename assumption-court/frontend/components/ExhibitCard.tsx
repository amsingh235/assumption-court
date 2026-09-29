import type { Exhibit } from "@/lib/scene";

const sideBorder = { bull: "border-l-green-500", bear: "border-l-red-500", neutral: "border-l-slate-400" } as const;

export function Stamp({ status }: { status: Exhibit["status"] }) {
  if (!status) return null;
  const ok = status === "VERIFIED";
  return (
    <span
      className={`stamp-in font-pixel pointer-events-none absolute -right-2 -top-2.5 rotate-[-8deg] rounded border-2 bg-cream px-1 text-[8px] ${
        ok ? "border-green-700 text-green-700" : "border-slate-500 text-slate-500"
      }`}
    >
      {ok ? "ADMITTED" : "UNVERIFIED"}
    </span>
  );
}

export default function ExhibitCard({ ex, onOpen }: { ex: Exhibit; onOpen: (ex: Exhibit) => void }) {
  const out = ex.status === "UNVERIFIED";
  return (
    <button
      onClick={() => onOpen(ex)}
      title="Show the verbatim quote"
      className={`exhibit-in relative mt-2 w-[128px] shrink-0 rounded-md border-l-4 bg-cream p-2 pr-3 text-left text-[10px] leading-tight shadow-[0_3px_0_#b9a58f] transition hover:-translate-y-0.5 sm:w-[150px] ${
        sideBorder[ex.side]
      } ${out ? "opacity-60 grayscale" : ""} ${ex.status ? "" : "animate-pulse"}`}
    >
      <Stamp status={ex.status} />
      <span className={`line-clamp-3 text-ink ${out ? "line-through decoration-slate-500" : ""}`}>{ex.claim}</span>
    </button>
  );
}

export function ExhibitDetail({ ex, onClose }: { ex: Exhibit; onClose: () => void }) {
  return (
    <div className="absolute inset-x-3 bottom-3 z-30 rounded-xl border-4 border-ink bg-cream p-4 text-ink shadow-2xl sm:inset-x-auto sm:right-4 sm:w-[420px]">
      <div className="mb-2 flex items-start justify-between gap-2">
        <span className="font-pixel text-[10px] uppercase text-clay-dark">
          Exhibit {ex.id} · {ex.side} · {ex.status ?? "awaiting fact-check"}
        </span>
        <button onClick={onClose} aria-label="Close exhibit" className="font-pixel text-xs text-ink/60 hover:text-ink">
          ✕
        </button>
      </div>
      <p className="text-sm font-medium">{ex.claim}</p>
      <blockquote className="mt-2 border-l-4 border-clay pl-3 text-sm italic text-ink/80">“{ex.quote}”</blockquote>
      {ex.url && (
        <a href={ex.url} target="_blank" rel="noopener noreferrer" className="mt-2 block truncate text-xs text-clay-dark underline">
          {ex.title || ex.url}
        </a>
      )}
      {ex.factcheck && (
        <p className="mt-1 text-xs text-ink/60">
          Fact-check: {ex.factcheck}
          {ex.reason ? `: ${ex.reason}` : ""}
        </p>
      )}
    </div>
  );
}
