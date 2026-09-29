"use client";

// One paced queue for every GraphEvent (live polling and example replay alike).
// The stage, transcript and evidence graph all advance together when an event is dequeued.
import { useCallback, useEffect, useRef, useState } from "react";
import { applyEvent, emptyState, type CourtState } from "./graphState";
import { applySceneEvent, dwellMs, emptyScene, type SceneState } from "./scene";
import type { GraphEvent } from "./types";

export type Speed = 1 | 2;

export function usePlayback() {
  const [court, setCourt] = useState<CourtState>(emptyState);
  const [scene, setScene] = useState<SceneState>(emptyScene);
  const [pending, setPending] = useState(0);
  const [speed, setSpeedState] = useState<Speed>(1);
  const [playing, setPlaying] = useState(false); // true until the last event's dwell has elapsed
  const queue = useRef<GraphEvent[]>([]);
  const lastQueued = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const speedRef = useRef<Speed>(1);

  const stop = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  };

  const pump = useCallback(() => {
    const tick = () => {
      const ev = queue.current.shift();
      setPending(queue.current.length);
      if (!ev) {
        timer.current = null;
        setPlaying(false);
        return;
      }
      setPlaying(true);
      setCourt((c) => applyEvent(c, ev));
      setScene((s) => applySceneEvent(s, ev));
      timer.current = setTimeout(tick, dwellMs(ev) / speedRef.current);
    };
    tick();
  }, []);

  const enqueue = useCallback(
    (events: GraphEvent[]) => {
      const fresh = events.filter((e) => e.seq > lastQueued.current).sort((a, b) => a.seq - b.seq);
      if (!fresh.length) return;
      lastQueued.current = fresh[fresh.length - 1].seq;
      queue.current.push(...fresh);
      setPending(queue.current.length);
      if (!timer.current) pump();
    },
    [pump],
  );

  /** Apply everything still queued immediately. */
  const skip = useCallback(() => {
    stop();
    const rest = queue.current.splice(0);
    setCourt((c) => rest.reduce(applyEvent, c));
    setScene((s) => rest.reduce(applySceneEvent, s));
    setPending(0);
    setPlaying(false);
  }, []);

  const reset = useCallback(() => {
    stop();
    queue.current = [];
    lastQueued.current = 0;
    setPending(0);
    setPlaying(false);
    setCourt(emptyState());
    setScene(emptyScene());
  }, []);

  const setSpeed = useCallback((s: Speed) => {
    speedRef.current = s;
    setSpeedState(s);
  }, []);

  useEffect(() => stop, []);

  return { court, scene, pending, playing, speed, setSpeed, enqueue, skip, reset };
}
