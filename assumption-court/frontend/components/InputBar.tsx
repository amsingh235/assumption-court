"use client";

import { useState } from "react";
import type { CachedCase } from "@/lib/types";

interface Props {
  busy: boolean;
  examples: CachedCase[];
  onSubmit: (text: string) => void;
  onExample: (c: CachedCase) => void;
}

export default function InputBar({ busy, examples, onSubmit, onExample }: Props) {
  const [text, setText] = useState("");
  const submit = () => {
    const t = text.trim();
    if (t.length >= 3 && !busy) onSubmit(t);
  };
  return (
    <div className="sticky bottom-0 w-full border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-4xl flex-col gap-2 sm:flex-row">
        <select
          aria-label="Examples"
          className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm text-navy sm:w-56"
          value=""
          disabled={busy || examples.length === 0}
          onChange={(e) => {
            const c = examples.find((x) => x.id === e.target.value);
            if (c) onExample(c);
          }}
        >
          <option value="">{examples.length ? "▶ Replay an example…" : "No examples loaded"}</option>
          {examples.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
        <form
          className="flex flex-1 gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <input
            aria-label="Assumption or why-question"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            placeholder='Put an assumption on trial, e.g. "D2C brands fail because of ads"'
            maxLength={500}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button
            type="submit"
            disabled={busy || text.trim().length < 3}
            className="rounded-lg bg-navy px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {busy ? "In session…" : "Start trial"}
          </button>
        </form>
      </div>
    </div>
  );
}
