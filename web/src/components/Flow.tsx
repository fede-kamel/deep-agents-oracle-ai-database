import clsx from "clsx";
import { ArrowRight, Check } from "lucide-react";
import type { ReactNode } from "react";

export type Step = "patient" | "work" | "brief" | "actions" | "memory";

export type StepInfo = { key: Step; title: string; hint: string; state: "done" | "active" | "ready" | "waiting" };

export const STEP_ORDER: Step[] = ["patient", "work", "brief", "actions", "memory"];

/** The main navigation: the story of one run, left to right. */
export function FlowStepper({ steps, current, onGo }: { steps: StepInfo[]; current: Step; onGo: (s: Step) => void }) {
  return (
    <div className="flex shrink-0 items-stretch gap-1 border-b border-line bg-panel px-5 py-2.5">
      {steps.map((s, i) => {
        const on = s.key === current;
        const clickable = s.state !== "waiting";
        return (
          <div key={s.key} className="flex min-w-0 flex-1 items-center gap-1">
            <button disabled={!clickable} onClick={() => onGo(s.key)}
              className={clsx("flex min-w-0 flex-1 items-center gap-3 rounded-xl px-3 py-2 text-left transition",
                on ? "bg-oracle-soft ring-1 ring-oracle/30" : clickable ? "hover:bg-sand" : "opacity-45")}>
              <span className={clsx("grid size-7 shrink-0 place-items-center rounded-full text-[12px] font-semibold",
                s.state === "done" ? "bg-moss text-white" : on ? "bg-oracle text-white" : s.state === "active" ? "bg-oracle/80 text-white" : "bg-sand text-ink-3")}>
                {s.state === "done" && !on ? <Check className="size-4" /> : s.state === "active" ? <span className="live-dot size-2 rounded-full bg-white" /> : i + 1}
              </span>
              <span className="min-w-0">
                <span className={clsx("block text-[13px] font-semibold", on ? "text-oracle" : "text-ink")}>{s.title}</span>
                <span className="block truncate text-[11px] text-ink-3">{s.hint}</span>
              </span>
            </button>
            {i < steps.length - 1 && <ArrowRight className="size-3.5 shrink-0 text-line" />}
          </div>
        );
      })}
    </div>
  );
}

/** A step's page: a short explanation on top, the content, one primary action at the bottom. */
export function StepPage({ eyebrow, title, lead, children, primary, secondary }: {
  eyebrow: string; title: string; lead: ReactNode; children: ReactNode;
  primary?: { label: string; onClick: () => void; disabled?: boolean }; secondary?: ReactNode;
}) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 px-6 pt-5 pb-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-oracle">{eyebrow}</div>
        <h1 className="mt-0.5 text-[21px] font-semibold tracking-tight">{title}</h1>
        <p className="mt-1 max-w-[920px] text-[13px] leading-relaxed text-ink-3">{lead}</p>
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-6 pb-4">{children}</div>
      {(primary || secondary) && (
        <div className="flex shrink-0 items-center gap-3 border-t border-line bg-panel px-6 py-3">
          <div className="min-w-0 flex-1 text-[12px] text-ink-3">{secondary}</div>
          {primary && (
            <button disabled={primary.disabled} onClick={primary.onClick}
              className="flex items-center gap-2 rounded-xl bg-oracle px-5 py-2.5 text-[13px] font-semibold text-white shadow-sm transition hover:bg-[#b23d2d] disabled:bg-ink-3/60">
              {primary.label} <ArrowRight className="size-4" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
