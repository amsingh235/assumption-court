import type { Speed } from "@/lib/usePlayback";

export default function PlaybackControls({ speed, onSpeed, onSkip, pending, disabled }: {
  speed: Speed; onSpeed: (s: Speed) => void; onSkip: () => void; pending: number; disabled: boolean;
}) {
  const btn = "font-pixel rounded-md px-2 py-1 text-[10px] transition disabled:opacity-30";
  return (
    <div className="flex items-center gap-1" aria-label="Playback">
      {([1, 2] as Speed[]).map((s) => (
        <button
          key={s}
          onClick={() => onSpeed(s)}
          aria-pressed={speed === s}
          className={`${btn} ${speed === s ? "bg-clay text-ink" : "bg-white/10 text-cream/70 hover:bg-white/20"}`}
        >
          {s}×
        </button>
      ))}
      <button onClick={onSkip} disabled={disabled || pending === 0} className={`${btn} bg-white/10 text-cream/70 hover:bg-white/20`}>
        Skip ⏭
      </button>
    </div>
  );
}
