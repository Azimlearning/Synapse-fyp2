"use client";

// Inside the Synapse workspace this app is embedded (`?embed=1`): the workspace's header owns branding and settings, and a
// question can be handed over (`?q=`) to be turned into an Environment at once (the workspace's Simulate button).
import { useEffect, useState } from "react";

export function useEmbedParams(): { embedded: boolean; q: string | null } {
  const [state, setState] = useState<{ embedded: boolean; q: string | null }>({ embedded: false, q: null });
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const q = p.get("q")?.trim();
    setState({ embedded: p.get("embed") === "1", q: q ? q.slice(0, 500) : null });
  }, []);
  return state;
}
