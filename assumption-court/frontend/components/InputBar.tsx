"use client";

import { useState } from "react";
import type { CachedCase } from "@/lib/types";

interface Props {
  busy: boolean;
  examples: CachedCase[];
  onSubmit: (text: string) => void;
  onExample: (c: CachedCase) => void;
}

/** Claude-style composer pinned to the bottom. */
export default function InputBar({ busy, examples, onSubmit, onExample }: Props) {
  const [text, setText] = useState("");
  const submit = () => {
    const t = text.trim();
    if (t.length >= 3 && !busy) onSubmit(t);
  };
  return (
    <div className="sticky bottom-0 z-40 w-full bg-gradient-to-t from-ink via-ink/95 to-transparent px-4 pb-4 pt-6">
      <form
        className="mx-auto flex max-w-3xl flex-col gap-2 rounded-2xl border border-white/15 bg-coal p-2 shadow-2xl sm:flex-row sm:items-center"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          aria-label="Assumption or why-question"
          className="min-w-0 flex-1 bg-transparent px-3 py-2 text-[15px] text-cream placeholder:text-cream/35 focus:outline-none"
          placeholder='Put an assumption on trial, e.g. "D2C brands fail because of ads"'
          maxLength={500}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="flex gap-2">
          <select
            aria-label="Examples"
            className="min-w-0 flex-1 rounded-xl border border-white/15 bg-ink px-2 py-2 text-xs text-cream/80 sm:w-48 sm:flex-none"
            value=""
            disabled={busy || examples.length === 0}
            onChange={(e) => {
              const c = examples.find((x) => x.id === e.target.value);
              if (c) onExample(c);
            }}
          >
            <option value="">{examples.length ? "▶ Replay an example…" : "No examples"}</option>
            {examples.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
          <button
            type="submit"
            disabled={busy || text.trim().length < 3}
            className="font-pixel rounded-xl bg-clay px-4 py-2 text-xs text-ink shadow-[0_3px_0_#7a3a22] transition hover:brightness-110 disabled:opacity-35"
          >
            {busy ? "In session" : "Start trial"}
          </button>
        </div>
      </form>
    </div>
  );
}
