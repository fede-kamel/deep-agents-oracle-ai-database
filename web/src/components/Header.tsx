import clsx from "clsx";
import { RotateCcw, ShieldCheck } from "lucide-react";
import type { Patient } from "../api";
import { Badge } from "./ui";

export type TabKey = "patient" | "agents" | "brief" | "actions" | "memory";
export type TabInfo = { key: TabKey; label: string; status?: string; tone?: "live" | "ok" | "warn" | "muted" };
export type RunStatus = { text: string; tone: "live" | "ok" | "bad" } | null;

/** One row: the product, the patient, the run's state, two quiet controls. */
export function Header({ patients, selected, onSelect, disabled, status, onSafety, onReset }: {
  patients: Patient[]; selected?: Patient; onSelect: (p: Patient) => void; disabled: boolean; status: RunStatus;
  onSafety: () => void; onReset: () => void;
}) {
  return (
    <header className="flex h-[52px] shrink-0 items-center gap-5 border-b border-line bg-panel px-5">
      <div className="flex items-center gap-2.5">
        <span className="grid size-7 place-items-center rounded-md bg-oracle"><span className="h-2.5 w-4 rounded-full border-2 border-white" /></span>
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight">Deep Agents</div>
          <div className="text-xs text-ink-3">Oracle AI Database · NVIDIA OpenShell · synthetic data</div>
        </div>
      </div>

      <div className="flex items-center rounded-lg bg-sand p-0.5">
        {patients.map((p) => {
          const on = selected?.key === p.key;
          return (
            <button key={p.key} aria-pressed={on} disabled={disabled} onClick={() => onSelect(p)} title={p.situation}
              className={clsx("rounded-md px-3 py-1.5 text-sm transition", on ? "bg-panel font-semibold text-ink shadow-sm" : "text-ink-2 hover:text-ink", disabled && !on && "opacity-50")}>
              {p.display_name}
            </button>
          );
        })}
      </div>

      <div className="ml-auto flex items-center gap-2">
        {status && <Badge tone={status.tone}>{status.text}</Badge>}
        <button onClick={onSafety} className="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-sm text-ink-2 hover:bg-sand hover:text-ink">
          <ShieldCheck className="size-3.5" /> Safety
        </button>
        <button onClick={onReset} className="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-sm text-ink-2 hover:bg-sand hover:text-ink">
          <RotateCcw className="size-3.5" /> Reset demo
        </button>
      </div>
    </header>
  );
}

/** The five areas of the demo, always reachable; a small status beside each. */
export function Tabs({ tabs, current, onGo }: { tabs: TabInfo[]; current: TabKey; onGo: (t: TabKey) => void }) {
  return (
    <nav role="tablist" className="flex h-11 shrink-0 items-stretch gap-7 border-b border-line bg-panel px-5">
      {tabs.map((t) => {
        const on = t.key === current;
        return (
          <button key={t.key} role="tab" aria-selected={on} onClick={() => onGo(t.key)}
            className={clsx("relative flex items-center gap-2 text-sm transition", on ? "font-semibold text-ink" : "text-ink-3 hover:text-ink")}>
            {t.label}
            {t.status && (
              <span className={clsx("flex items-center gap-1 text-xs font-medium",
                t.tone === "live" ? "text-oracle" : t.tone === "ok" ? "text-ok" : t.tone === "warn" ? "text-warn" : "text-ink-3")}>
                {t.tone === "live" && <span className="live-dot size-1.5 rounded-full bg-oracle" />}
                {t.status}
              </span>
            )}
            {on && <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-oracle" />}
          </button>
        );
      })}
    </nav>
  );
}
