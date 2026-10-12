import clsx from "clsx";
import { Bot, Brain, CheckCircle2, Circle, CircleDashed, FileText, LayoutList, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import type { Lane, RunView } from "../api";
import { LANES } from "./lanes";
import { LaneCard } from "./RunTimeline";

type Agent = { name: string; lanes: Lane[]; running: boolean; calls: number };

/**
 * The run below the console: an Overview tab (plan first, then context) and
 * one tab per specialist, added the moment the lead delegates to it. The view
 * follows the most recently started running specialist until the user picks a
 * tab; repeat delegations to one specialist stack in its tab, newest first.
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

  const [chosen, setChosen] = useState<{ run: string | undefined; tab: string } | null>(null);
  const running = view.lanes.filter((l) => l.status === "running");
  const following = running.length ? running[running.length - 1].name : "overview";
  const tab = chosen && chosen.run === view.id ? chosen.tab : following;
  const pick = (t: string) => setChosen({ run: view.id, tab: t });
  const current = agents.find((a) => a.name === tab);

  return (
    <section className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-line bg-panel">
      <div role="tablist" className="scroll-thin flex shrink-0 items-end gap-0.5 overflow-x-auto border-b border-line px-2 pt-1.5">
        <Tab active={tab === "overview"} onClick={() => pick("overview")}
          icon={<LayoutList className="size-3.5 text-ink-3" />} label="Overview"
          status={view.todos.length ? `${view.todos.filter((t) => t.status === "completed").length} of ${view.todos.length} steps` : "planning"} />
        {agents.map((a) => {
          const meta = LANES[a.name];
          const Icon = meta?.icon ?? Bot;
          return (
            <Tab key={a.name} active={tab === a.name} onClick={() => pick(a.name)}
              icon={<span className={clsx("grid size-5 place-items-center rounded", meta?.tone ?? "bg-sand text-ink-2")}><Icon className="size-3" strokeWidth={2.2} /></span>}
              label={meta?.label ?? a.name}
              live={a.running}
              status={`${a.running ? "working" : "done"} · ${a.calls} ${a.calls === 1 ? "call" : "calls"}`} />
          );
        })}
        {chosen?.run === view.id && running.length > 0 && (
          <button onClick={() => setChosen(null)} className="mb-1.5 ml-auto shrink-0 rounded-md px-2 py-1 text-[11.5px] text-oracle hover:bg-oracle-soft">
            Follow live
          </button>
        )}
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto bg-paper p-4">
        {tab === "overview" || !current ? (
          <Overview view={view} question={question} patientName={patientName} />
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

function Tab({ active, onClick, icon, label, status, live = false }: {
  active: boolean; onClick: () => void; icon: ReactNode; label: string; status: string; live?: boolean;
}) {
  return (
    <button role="tab" aria-selected={active} onClick={onClick}
      className={clsx("relative flex shrink-0 items-center gap-2 rounded-t-lg px-3 pt-1.5 pb-2 text-left transition",
        active ? "bg-paper" : "hover:bg-sand/60")}>
      {icon}
      <span className="leading-tight">
        <span className={clsx("block whitespace-nowrap text-[12.5px]", active ? "font-semibold text-ink" : "text-ink-2")}>{label}</span>
        <span className={clsx("flex items-center gap-1 whitespace-nowrap text-[10.5px]", live ? "text-oracle" : "text-ink-3")}>
          {live && <span className="live-dot size-1.5 rounded-full bg-oracle" />}
          {status}
        </span>
      </span>
      {active && <span className="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-oracle" />}
    </button>
  );
}

/** The lead's view of the run: the plan, then what it worked from and what it produced. */
function Overview({ view, question, patientName }: { view: RunView; question: string; patientName: string }) {
  const writing = view.leadCalls.some((c) => c.name === "write_file");
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div className="rounded-xl border border-line bg-panel p-4">
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-[13px] font-semibold">Plan</h3>
          <span className="font-mono text-[10.5px] text-ink-3">write_todos · {view.meta?.model ?? "lead"}</span>
        </div>
        {view.todos.length === 0 ? (
          <div className="flex items-center gap-2 text-[12.5px] text-ink-3"><Loader2 className="size-3.5 animate-spin" /> The lead is planning…</div>
        ) : (
          <ol className="space-y-2">
            {view.todos.map((t, i) => (
              <li key={i} className="flex items-start gap-2.5 text-[13px] leading-snug">
                {t.status === "completed" ? <CheckCircle2 className="mt-px size-4 shrink-0 text-moss" />
                  : t.status === "in_progress" ? <CircleDashed className="mt-px size-4 shrink-0 animate-spin text-oracle [animation-duration:3s]" />
                  : <Circle className="mt-px size-4 shrink-0 text-line" />}
                <span className={clsx(t.status === "completed" ? "text-ink-3" : t.status === "in_progress" ? "font-medium text-ink" : "text-ink-2")}>{t.content}</span>
              </li>
            ))}
          </ol>
        )}
        {view.thoughts.lead && view.status === "running" && (
          <p className="mt-3 whitespace-pre-wrap border-l-2 border-line pl-3 text-[12px] italic leading-snug text-ink-3">{view.thoughts.lead}</p>
        )}
      </div>

      <div className="space-y-3">
        <Fact label={`Question · ${patientName}`}>{question}</Fact>
        {view.memory && (
          <Fact label="Memory from Oracle" icon={<Brain className="size-3.5 text-teal" />}>
            {view.memory.entries === 0 ? "First brief for this patient." : `${view.memory.entries} entries from earlier briefs and decisions.`}
            {view.memory.written && <span className="ml-1 font-medium text-moss">This brief was added.</span>}
          </Fact>
        )}
        {view.repairs.map((r, i) => (
          <Fact key={i} label="Verifier sent the draft back" icon={<ShieldAlert className="size-3.5 text-ochre" />}>
            <ul className="list-disc space-y-0.5 pl-4">{r.map((p) => <li key={p}>{p}</li>)}</ul>
          </Fact>
        ))}
        {(writing || view.brief) && (
          <Fact label="Brief" icon={<FileText className="size-3.5 text-oracle" />}>
            {view.verified ? (
              <span className={clsx("inline-flex items-center gap-1 font-medium", view.verified.passed ? "text-moss" : "text-oracle")}>
                <ShieldCheck className="size-3.5" /> {view.verified.passed ? `Verified · ${view.verified.citations} citations` : "Not verified"}
              </span>
            ) : "Being written from the structured PreVisitBrief…"}
          </Fact>
        )}
        {view.done && (
          <div className="grid grid-cols-3 gap-2">
            {[
              ["time", `${Math.round(view.done.seconds)} s`],
              ["tool calls", view.done.tool_calls],
              ["delegations", view.done.delegations],
              ["SQL", view.done.sql],
              ["searches", view.done.searches],
              ["checkpoints", view.checkpoints?.count ?? "–"],
            ].map(([k, v]) => (
              <div key={k} className="rounded-lg border border-line bg-panel px-3 py-2">
                <div className="font-mono text-[15px] font-semibold text-ink">{v}</div>
                <div className="text-[10.5px] uppercase tracking-wide text-ink-3">{k}</div>
              </div>
            ))}
          </div>
        )}
        {view.error && (
          <div className="rounded-lg border border-oracle/40 bg-oracle-soft px-3 py-2 text-[12.5px] text-oracle">
            <span className="font-semibold">{view.status === "blocked" ? "Blocked by the input guard: " : view.status === "rejected" ? "Rejected by the gate: " : "Run failed: "}</span>
            {view.error}
          </div>
        )}
      </div>
    </div>
  );
}

function Fact({ label, icon, children }: { label: string; icon?: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3">
      <div className="mb-1 flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-ink-3">{icon}{label}</div>
      <div className="text-[12.5px] leading-snug text-ink-2">{children}</div>
    </div>
  );
}
