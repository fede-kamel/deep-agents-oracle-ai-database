import clsx from "clsx";
import { Maximize2, Minimize2, Monitor } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

export type MaxControls = { maximized: boolean; toggle: () => void; fullscreen: () => void };

/**
 * Any panel can grow to fill the window (Esc to return) or go true full screen.
 * Children receive the controls so each panel keeps its own header.
 */
export function Maximizable({ children, className }: { children: (c: MaxControls) => ReactNode; className?: string }) {
  const [maximized, setMaximized] = useState(false);
  const overlay = useRef<HTMLDivElement>(null);
  const toggle = useCallback(() => setMaximized((m) => !m), []);
  const fullscreen = useCallback(() => {
    setMaximized(true);
    requestAnimationFrame(() => overlay.current?.requestFullscreen?.().catch(() => undefined));
  }, []);

  useEffect(() => {
    if (!maximized) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !document.fullscreenElement && setMaximized(false);
    const onFs = () => !document.fullscreenElement && setMaximized(false);
    window.addEventListener("keydown", onKey);
    document.addEventListener("fullscreenchange", onFs);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("fullscreenchange", onFs);
    };
  }, [maximized]);

  const controls = { maximized, toggle, fullscreen };
  if (!maximized) return <div className={className}>{children(controls)}</div>;
  return (
    <>
      <div className={clsx(className, "grid place-items-center rounded-xl border border-dashed border-line text-[12px] text-ink-3")}>
        shown full screen · Esc to return
      </div>
      {createPortal(
        <div ref={overlay} className="fixed inset-0 z-50 flex flex-col bg-paper p-4">
          {children(controls)}
        </div>,
        document.body,
      )}
    </>
  );
}

export function MaxButtons({ c, dark = false }: { c: MaxControls; dark?: boolean }) {
  const cls = dark
    ? "rounded-md border border-[#30363d] px-1.5 py-1 text-[#8b949e] hover:text-white"
    : "rounded-md border border-line bg-panel px-1.5 py-1 text-ink-3 hover:text-ink";
  return (
    <div className="flex gap-1">
      {!c.maximized && (
        <button title="True full screen" onClick={c.fullscreen} className={cls}>
          <Monitor className="size-3.5" />
        </button>
      )}
      <button title={c.maximized ? "Restore (Esc)" : "Maximise"} onClick={c.toggle} className={cls}>
        {c.maximized ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}
      </button>
    </div>
  );
}
