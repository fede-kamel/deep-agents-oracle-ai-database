import clsx from "clsx";
import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";

const KEY = "deepagents.console-height";
const MIN = 40; // the console's title row: dragged all the way down, the terminal is a bar
const KEEP = 160; // what always stays visible of the work above
const STEP = 24; // one arrow key

/**
 * Two rows like an IDE: the work on top, a terminal below, a sash between
 * them. Drag the sash to resize, double-click it to collapse the terminal to
 * its title row and back, or use the arrow keys when it has focus. The height
 * is remembered across reloads.
 */
export function SplitRows({ top, bottom, defaultFraction = 0.42 }: { top: ReactNode; bottom: ReactNode; defaultFraction?: number }) {
  const box = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | null>(() => {
    const v = Number(localStorage.getItem(KEY));
    return v > 0 ? v : null;
  });
  const [dragging, setDragging] = useState(false);
  const open = useRef(0); // the last open height, restored by a double-click

  const clamp = useCallback((h: number) => {
    const room = (box.current?.clientHeight ?? 0) - KEEP;
    return Math.round(Math.min(Math.max(h, MIN), Math.max(MIN, room)));
  }, []);
  const current = useCallback(() => height ?? Math.round((box.current?.clientHeight ?? 0) * defaultFraction), [height, defaultFraction]);
  const apply = useCallback((h: number) => {
    const c = clamp(h);
    setHeight(c);
    localStorage.setItem(KEY, String(c));
    if (c > MIN) open.current = c;
  }, [clamp]);

  // A smaller window must not leave the terminal covering everything.
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setHeight((h) => (h === null ? h : clamp(h))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [clamp]);

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    const el = e.currentTarget;
    const startY = e.clientY;
    const from = current();
    el.setPointerCapture(e.pointerId);
    setDragging(true);
    const move = (ev: globalThis.PointerEvent) => apply(from + (startY - ev.clientY));
    const stop = () => {
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerup", stop);
      el.removeEventListener("pointercancel", stop);
      setDragging(false);
    };
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerup", stop);
    el.addEventListener("pointercancel", stop);
  };
  const toggle = () => apply(current() > MIN ? MIN : open.current || Math.round((box.current?.clientHeight ?? 0) * defaultFraction));
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "ArrowUp") apply(current() + STEP);
    else if (e.key === "ArrowDown") apply(current() - STEP);
    else if (e.key === "Enter") toggle();
    else return;
    e.preventDefault();
  };

  return (
    <div ref={box} className={clsx("flex h-full min-h-0 flex-col", dragging && "cursor-row-resize select-none")}>
      <div className="min-h-0 flex-1">{top}</div>
      <div role="separator" aria-orientation="horizontal" aria-label="Resize the console" tabIndex={0}
        title="Drag to resize · double-click to collapse or restore"
        onPointerDown={onPointerDown} onDoubleClick={toggle} onKeyDown={onKeyDown}
        className="group flex h-3 shrink-0 cursor-row-resize items-center justify-center outline-none">
        <div className={clsx("h-1 w-16 rounded-full transition", dragging ? "bg-oracle" : "bg-line group-hover:bg-ink-3/60 group-focus-visible:bg-oracle")} />
      </div>
      <div className="min-h-0 shrink-0" style={{ height: height ?? `${defaultFraction * 100}%` }}>{bottom}</div>
    </div>
  );
}
