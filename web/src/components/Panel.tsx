import clsx from "clsx";
import { Maximize2, Minimize2 } from "lucide-react";
import type { ReactNode } from "react";
import { useFullscreen } from "../hooks";

/**
 * Every area of the application is a panel: a title row with its few controls
 * and a full-screen button, then the content. `dark` is the console's theme.
 */
export function Panel({ title, meta, actions, children, dark = false, className, bodyClassName }: {
  title: ReactNode; meta?: ReactNode; actions?: ReactNode; children: ReactNode; dark?: boolean; className?: string; bodyClassName?: string;
}) {
  const fs = useFullscreen<HTMLElement>();
  return (
    <section ref={fs.ref}
      className={clsx("flex min-h-0 flex-col overflow-hidden border", dark ? "border-[#2a2a2a] bg-term text-[#c9d1d9]" : "border-line bg-panel",
        fs.on ? "rounded-none border-0" : "rounded-lg", className)}>
      <header className={clsx("flex h-10 shrink-0 items-center gap-3 border-b px-3.5", dark ? "border-[#262626] bg-term-2" : "border-line")}>
        <div className={clsx("flex min-w-0 items-center gap-2", dark ? "font-mono text-xs text-[#c9d1d9]" : "text-sm font-semibold text-ink")}>{title}</div>
        {meta && <div className={clsx("min-w-0 text-xs", dark ? "font-mono text-[#8b949e]" : "text-ink-3")}>{meta}</div>}
        <div className="ml-auto flex shrink-0 items-center gap-2">
          {actions}
          <button onClick={fs.toggle} title={fs.on ? "Exit full screen (Esc)" : "Full screen"}
            className={clsx("rounded-md p-1 transition", dark ? "text-[#8b949e] hover:bg-[#2a2a2a] hover:text-white" : "text-ink-3 hover:bg-sand hover:text-ink")}>
            {fs.on ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}
          </button>
        </div>
      </header>
      <div className={clsx("min-h-0 flex-1", bodyClassName)}>{children}</div>
    </section>
  );
}
