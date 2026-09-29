import { spriteLayers, type Cell, type SpriteId } from "./sprites";

export type Pose = "idle" | "talk" | "walk" | "flag" | "gavel";

function Cells({ cells, className }: { cells: Cell[]; className?: string }) {
  return (
    <g className={className}>
      {cells.map((c) => (
        <rect key={`${c.x}-${c.y}`} x={c.x} y={c.y} width={1.02} height={1.02} fill={c.color} />
      ))}
    </g>
  );
}

/** Pixel creature rendered as crisp SVG rects. Animation is pure CSS (see globals.css `px-*`). */
export default function PixelAgent({
  id,
  pose = "idle",
  size = 80,
  flip = false,
  className = "",
  title,
}: {
  id: SpriteId;
  pose?: Pose;
  size?: number;
  flip?: boolean;
  className?: string;
  title?: string;
}) {
  const s = spriteLayers(id);
  const walking = pose === "walk";
  return (
    <svg
      viewBox="0 0 16 16"
      width={size}
      height={size}
      shapeRendering="crispEdges"
      role="img"
      aria-label={title ?? id}
      className={`${walking ? "px-walk" : pose === "gavel" ? "px-gavel" : "px-bob"} ${className}`}
    >
      <g transform={flip ? "matrix(-1 0 0 1 16 0)" : undefined}>
      <Cells cells={s.bodyNoLegs} />
      {walking ? (
        <>
          <Cells cells={s.legsIdle} className="px-frame-a" />
          <Cells cells={s.legsWalk} className="px-frame-b" />
        </>
      ) : (
        <Cells cells={s.legsIdle} />
      )}
      {pose === "talk" && <Cells cells={s.mouth} className="px-talk" />}
      {pose === "flag" && <Cells cells={s.flag} className="px-flag" />}
      </g>
    </svg>
  );
}
