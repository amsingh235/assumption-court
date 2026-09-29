# Assumption Court: frontend

Next.js (App Router) + React Flow + Tailwind v4. See the project README for the full picture.

```bash
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev   # http://localhost:3000
npm run build && npm run lint
```

- `lib/usePlayback.ts`: the single paced queue. Live polling (`GET /trial/{id}` every 1.5 s) and example replay both
  enqueue backend `GraphEvent`s here, and each dequeued event updates:
  - `lib/scene.ts`: courtroom scene (who speaks, walks, concedes; exhibits and stamps; transcript; ruling)
  - `lib/graphState.ts`: React Flow nodes/edges for the evidence graph
- `lib/types.ts` mirrors `backend/app/models.py` and the event payloads in `backend/app/graph_events.py`.
- `components/pixel/`: 16×16 pixel sprites drawn as SVG rects (no image assets); animation is CSS in `app/globals.css`.
- `public/examples/`: static copies of the cached trials, so replay works with the backend down
  (regenerate with `backend/scripts/generate_cached_cases.py`).
