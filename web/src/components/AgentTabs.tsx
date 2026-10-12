import clsx from "clsx";
import { Bot, CheckCircle2, LayoutList, Loader2 } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import type { Lane, RunView } from "../api";
import { LANES } from "./lanes";
import { LaneCard, RunTimeline } from "./RunTimeline";

type Agent = { name: string; lanes: Lane[]; running: boolean; calls: number };

/**
 * The run below the console: an Overview tab (question, memory, plan,
 * verifier) and one tab per specialist, added the moment the lead delegates
 * to it. The view follows the newest running specialist until the user picks
 * a tab; repeat delegations to one specialist stack in its tab, newest first.
 */
export function AgentTabs({ view, question, patientName }: { view: RunView; question: string; patientName: string }) {
  const agents = useMemo(() => {
    const byName = new Map<string, Agent>();
    for (const l of view.lanes) {
      const a = byName.get(l.name) ?? { name: l.name, lanes: [], running: false, calls: 0 };
      a.lanes.unshift(l);
      a.running ||= l.status === "running";
      a.calls += l.calls.length;
      byName.set(l.name, a);
    }
    return [...byName.values()];
  }, [view.lanes]);

  // Follow the newest running specialist until the user picks a tab; the
  // pick holds for this run only.
  const [chosen, setChosen] = useState<{ run: string | undefined; tab: string } | null>(null);
  const latest = view.lanes.length ? view.lanes[view.lanes.length - 1] : undefined;
  const following = latest?.status === "running" ? latest.name : "overview";
  const tab = chosen && chosen.run === view.id ? chosen.tab : following;
  const pick = (t: string) => setChosen({ run: view.id, tab: t });
  const current = agents.find((a) => a.name === tab);

  return (
    <section className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-line bg-paper">
      <div role="tablist" className="scroll-thin flex shrink-0 gap-1 overflow-x-auto border-b border-line bg-panel px-2 pt-2">
        <TabButton active={tab === "overview"} onClick={() => pick("overview")}>
          <LayoutList className="size-3.5" /> Overview
          {view.todos.length > 0 && (
            <span className="font-mono text-[10.5px] text-ink-3">
              {view.todos.filter((t) => t.status === "completed").length}/{view.todos.length}
            </span>
          )}
        </TabButton>
        {agents.map((a) => {
          const meta = LANES[a.name];
          const Icon = meta?.icon ?? Bot;
          return (
            <TabButton key={a.name} active={tab === a.name} onClick={() => pick(a.name)}>
              <span className={clsx("grid size-5 place-items-center rounded", meta?.tone ?? "bg-sand text-ink-2")}>
                <Icon className="size-3" strokeWidth={2.2} />
              </span>
              {meta?.label ?? a.name}
              {a.running ? <Loader2 className="size-3 animate-spin text-oracle" /> : <CheckCircle2 className="size-3 text-moss" />}
              <span className="font-mono text-[10.5px] text-ink-3">{a.calls}</span>
            </TabButton>
          );
        })}
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto p-4">
        {tab === "overview" || !current ? (
          <RunTimeline view={view} question={question} patientName={patientName} showLanes={false} />
        ) : (
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            {current.lanes.map((l, i) => (
              <LaneCard key={`${l.name}-${l.started}-${i}`} lane={l} thought={view.thoughts[l.name]} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={clsx(
        "-mb-px flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-t-lg border px-3 py-1.5 text-[12.5px]",
        active ? "border-line border-b-paper bg-paper font-semibold text-ink" : "border-transparent text-ink-3 hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}
