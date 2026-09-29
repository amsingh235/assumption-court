// 16x16 pixel sprites. One shared Claude-style blob body + a per-agent accessory overlay.
// Map characters: "." = transparent / no change, other letters index PALETTE.

export type SpriteId = "researcher" | "bull" | "bear" | "factchecker" | "judge";

export const PALETTE: Record<string, string> = {
  o: "#d97757", // clay body
  d: "#b35a3a", // body shade
  k: "#1a1918", // ink
  w: "#f7f3ee", // white
  c: "#f0e6da", // cream
  g: "#4ade80", // green
  r: "#f87171", // red
  s: "#9ca3af", // slate
  b: "#7c4a2d", // wood
  y: "#eab308", // gold
};

const BODY = [
  "................",
  "................",
  "................",
  "....oooooooo....",
  "...oooooooooo...",
  "...oooooooooo...",
  "...ookooookoo...",
  ".ooookooookoooo.",
  ".oooooooooooooo.",
  "...oooooooooo...",
  "...oooooooooo...",
  "...oooooooooo...",
  "...dddddddddd...",
  "....oo....oo....",
  "....oo....oo....",
  "................",
].map((r) => r.slice(0, 16).padEnd(16, "."));

const LEGS_WALK = [
  "................", "................", "................", "................", "................",
  "................", "................", "................", "................", "................",
  "................", "................", "................",
  "...oo......oo...",
  "..oo........oo..",
  "................",
];
// Row 13-14 must also clear the idle legs, so walk frames are drawn over a "cleared" leg area.
export const LEG_ROWS = [13, 14];

const MOUTH = { row: 8, cells: [7, 8], color: "k" };

const ACCESSORIES: Record<SpriteId, string[]> = {
  researcher: [
    "................",
    "................",
    "................",
    "................",
    "................",
    "....kkkk.kkkk...",
    "....kkck.kkck...",
    "....kkckkkkck...",
    "....kkkk.kkkk.kk",
    ".............kck",
    ".............kkk",
    "............b...",
    "...........b....",
    "................",
    "................",
    "................",
  ],
  bull: [
    "................",
    ".cc..........cc.",
    "..cc........cc..",
    "...cc......cc...",
    "................",
    "................",
    "................",
    "................",
    "................",
    ".......gg.......",
    "......gggg......",
    ".......gg.......",
    ".......gg.......",
    "................",
    "................",
    "................",
  ],
  bear: [
    "................",
    "................",
    "..ddd......ddd..",
    "..ddd......ddd..",
    "................",
    "................",
    "................",
    "................",
    "................",
    ".......rr.......",
    ".......rr.......",
    "......rrrr......",
    ".......rr.......",
    "................",
    "................",
    "................",
  ],
  factchecker: [
    "..............g.",
    ".............g..",
    "..........g.g...",
    "...........g....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "...wswswswswsw..",
    "...swswswswsws..",
    "...wswswswswsw..",
    "...swswswswsws..",
    "................",
    "................",
    "................",
  ],
  judge: [
    "................",
    "....wwwwwwww....",
    "...wwwwwwwwww...",
    "..ww........ww..",
    "..ww........ww..",
    "..ww........ww..",
    "..w..........w..",
    ".............bbb",
    ".............bbb",
    "..............y.",
    "..............y.",
    "................",
    "................",
    "................",
    "................",
    "................",
  ],
};

export const FLAG = [
  "................",
  ".bwww...........",
  ".bwww...........",
  ".bww............",
  ".b..............",
  ".b..............",
  ".b..............",
  "................",
];

export interface Cell {
  x: number;
  y: number;
  color: string;
}

function overlay(base: string[][], layer: string[]): void {
  layer.forEach((row, y) =>
    [...row.padEnd(16, ".")].slice(0, 16).forEach((ch, x) => {
      if (ch !== ".") base[y][x] = ch;
    }),
  );
}

function toCells(grid: string[][]): Cell[] {
  const cells: Cell[] = [];
  grid.forEach((row, y) => row.forEach((ch, x) => ch !== "." && PALETTE[ch] && cells.push({ x, y, color: PALETTE[ch] })));
  return cells;
}

export interface SpriteLayers {
  body: Cell[]; // body + accessory, idle legs
  bodyNoLegs: Cell[]; // same, legs removed (walk frames are drawn separately)
  legsIdle: Cell[];
  legsWalk: Cell[];
  mouth: Cell[];
  flag: Cell[];
}

const cache = new Map<SpriteId, SpriteLayers>();

export function spriteLayers(id: SpriteId): SpriteLayers {
  const hit = cache.get(id);
  if (hit) return hit;
  const grid = BODY.map((r) => [...r]);
  overlay(grid, ACCESSORIES[id]);
  const noLegs = grid.map((row, y) => (LEG_ROWS.includes(y) ? row.map(() => ".") : [...row]));
  const legsIdle = grid.map((row, y) => (LEG_ROWS.includes(y) ? [...row] : row.map(() => ".")));
  const layers: SpriteLayers = {
    body: toCells(grid),
    bodyNoLegs: toCells(noLegs),
    legsIdle: toCells(legsIdle),
    legsWalk: toCells(LEGS_WALK.map((r) => [...r])),
    mouth: MOUTH.cells.map((x) => ({ x, y: MOUTH.row, color: PALETTE[MOUTH.color] })),
    flag: toCells(FLAG.map((r) => [...r.padEnd(16, ".")])),
  };
  cache.set(id, layers);
  return layers;
}
