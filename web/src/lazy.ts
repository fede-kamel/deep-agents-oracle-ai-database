import { lazy, type ComponentType } from "react";

const KEY = "deepagents.reloaded-at";
const AGAIN_AFTER = 60_000; // one reload a minute at most: never a loop

function lastReload(): number {
  try { return Number(sessionStorage.getItem(KEY) ?? 0); } catch { return 0; }
}

/**
 * A page whose code arrives with its first use. Every build renames the
 * chunks, so after a redeploy an open tab may ask for a file that no longer
 * exists. Then the application reloads once and picks up the new index
 * instead of failing; a second failure within a minute reaches the page
 * boundary, which offers a reload by hand.
 */
export function lazyPage<P extends object>(load: () => Promise<{ default: ComponentType<P> }>) {
  return lazy(() => load().catch((err: unknown) => {
    if (Date.now() - lastReload() > AGAIN_AFTER) {
      try { sessionStorage.setItem(KEY, String(Date.now())); } catch { /* reload anyway */ }
      window.location.reload();
      return new Promise<{ default: ComponentType<P> }>(() => undefined); // the page is going away
    }
    throw err;
  }));
}

/** Fetch the code of every lazy page soon after the first paint, so a redeploy
 * during a talk never leaves a page without its code. Returns the cleanup. */
export function prefetch(loaders: (() => Promise<unknown>)[], delayMs = 1500): () => void {
  const t = window.setTimeout(() => { for (const load of loaders) load().catch(() => undefined); }, delayMs);
  return () => window.clearTimeout(t);
}
