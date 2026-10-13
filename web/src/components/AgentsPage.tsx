import clsx from "clsx";
import { Brain, CheckCircle2, Circle, CircleDashed, FileText, LayoutList, ListTree, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { agentMeta } from "../agents";
import type { Lane, RunView } from "../api";
import { fmtSeconds, useNow } from "../hooks";
import { AgentTrace } from "./AgentTrace";
import { LaneCard } from "./LaneCard";
import { Panel } from "./Panel";
import { SandboxConsole } from "./SandboxConsole";
import { SplitRows } from "./Split";
import { Button, Empty, Label, NextLink, PageHeader } from "./ui";

const TITLES: Record<string, string> = {
  starting: "Starting the sandbox", running: "Agents at work", succeeded: "Run finished", failed: "Run failed",
  blocked: "Blocked by the input guard", rejected: "Brief rejected by the gate", cancelled: "Run stopped",
};

/** The run, laid out like an IDE: the lead and the specialists on top, the
 * sandbox console below as the terminal, with a sash to drag between them. */
export function AgentsPage({ view, running, question, patientName, onBrief, onPatient }: {
  view: RunView; running: boolean; question: string; patientName: string; onBrief: () => void; onPatient: () => void;
}) {
  const now = useNow(running);
  if (view.status === "idle") {
    return <Empty action={<Button variant="accent" onClick={onPatient}>Ask for a brief</Button>}>No run yet. Pick a patient and ask the agents for a pre-visit brief; their work shows here as it happens.</Empty>;
  }
  const subtitle = [
    patientName,
    view.meta?.model && `${view.meta.model} lead`,
    view.meta?.worker_model && `${view.meta.worker_model} specialists`,
    view.done ? `${fmtSeconds(view.done.seconds)} · ${view.done.tool_calls} tool calls · ${view.done.sql} SQL · ${view.done.searches} searches`
      : running && view.started ? fmtSeconds(now - view.started) : null,
  ].filter(Boolean).join(" · ");
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <PageHeader title={TITLES[view.status] ?? "Run"} subtitle={subtitle}>
        {view.brief && <NextLink onClick={onBrief}>Read the brief</NextLink>}
      </PageHeader>
      <div className="min-h-0 flex-1">
        <SplitRows top={<RunTabs view={view} question={question} patientName={patientName} now={now} />}
          bottom={<SandboxConsole lines={view.console} live={running} />} />
      </div>
    </div>
  );
}

type Agent = { name: string; lanes: Lane[]; running: boolean; calls: number };

/** Overview, one tab per specialist as the lead delegates, and the timeline.
 * The view follows the specialist that started last until the user picks a tab. */
function RunTabs({ view, question, patientName, now }: { view: RunView; question: string; patientName: string; now: number }) {
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
  const live = view.lanes.filter((l) => l.status === "running");
  const following = live.length ? live[live.length - 1].name : "overview";
  const tab = chosen && chosen.run === view.id ? chosen.tab : following;
  const pick = (t: string) => setChosen({ run: view.id, tab: t });
  const current = agents.find((a) => a.name === tab);

  const tabs = (
    <div role="tablist" className="scroll-thin flex items-center gap-0.5 overflow-x-auto font-normal">
      <Tab on={tab === "overview"} onClick={() => pick("overview")} icon={<LayoutList className="size-3.5 text-ink-3" />} label="Overview" />
      {agents.map((a) => {
        const m = agentMeta(a.name);
        const Icon = m.icon;
        return <Tab key={a.name} on={tab === a.name} onClick={() => pick(a.name)} label={m.label} count={a.calls} live={a.running}
          icon={<Icon className="size-3.5" style={{ color: m.color }} strokeWidth={2.2} />} />;
      })}
      <Tab on={tab === "timeline"} onClick={() => pick("timeline")} icon={<ListTree className="size-3.5 text-ink-3" />} label="Timeline" count={view.events.length} />
    </div>
  );
  const follow = chosen?.run === view.id && live.length > 0 && (
    <button onClick={() => setChosen(null)} className="text-xs font-medium text-oracle hover:underline">Follow live</button>
  );
  const timeline = tab === "timeline";
  return (
    <Panel title={tabs} actions={follow} className="h-full" bodyClassName={clsx("bg-paper p-4", timeline ? "flex flex-col" : "scroll-thin overflow-y-auto")}>
      {timeline ? (
        <AgentTrace events={view.events} />
      ) : tab === "overview" || !current ? (
        <Overview view={view} question={question} patientName={patientName} />
      ) : (
        <div className="space-y-3">
          {current.lanes.map((l, i) => <LaneCard key={`${l.name}-${l.started}-${i}`} lane={l} thought={view.thoughts[l.name]} now={now} />)}
        </div>
      )}
    </Panel>
  );
}

function Tab({ on, onClick, icon, label, count, live = false }: { on: boolean; onClick: () => void; icon: ReactNode; label: string; count?: number; live?: boolean }) {
  return (
    <button role="tab" aria-selected={on} onClick={onClick}
      className={clsx("flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 text-sm transition", on ? "bg-sand font-semibold text-ink" : "text-ink-3 hover:text-ink")}>
      {icon}{label}
      {live && <span className="live-dot size-1.5 rounded-full bg-oracle" />}
      {count !== undefined && <span className="font-mono text-xs text-ink-3">{count}</span>}
    </button>
  );
}

/** The lead's view: the plan, then what it worked from and what it produced. */
function Overview({ view, question, patientName }: { view: RunView; question: string; patientName: string }) {
  const running = view.status === "running" || view.status === "starting";
  const writing = view.leadCalls.some((c) => c.name === "write_file");
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <section className="rounded-lg border border-line bg-panel p-4">
        <div className="mb-3 flex items-baseline justify-between">
          <Label>Plan</Label>
          <span className="font-mono text-xs text-ink-3">write_todos · {view.meta?.model ?? "lead"}</span>
        </div>
        {view.todos.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-ink-3"><Loader2 className="size-3.5 animate-spin" /> The lead is planning…</div>
        ) : (
          <ol className="space-y-2">
            {view.todos.map((t, i) => (
              <li key={i} className="flex items-start gap-2.5 text-base leading-snug">
                {t.status === "completed" ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-ok" />
                  : t.status === "in_progress" ? <CircleDashed className="mt-0.5 size-4 shrink-0 animate-spin text-oracle [animation-duration:3s]" />
                  : <Circle className="mt-0.5 size-4 shrink-0 text-line" />}
                <span className={clsx(t.status === "completed" ? "text-ink-3" : t.status === "in_progress" ? "font-medium text-ink" : "text-ink-2")}>{t.content}</span>
              </li>
            ))}
          </ol>
        )}
        {view.thoughts.lead && running && <p className="mt-3 whitespace-pre-wrap border-l-2 border-line pl-3 text-sm italic text-ink-3">{view.thoughts.lead}</p>}
      </section>

      <div className="space-y-3">
        <Fact label={`Clinician · ${patientName}`}>{question}</Fact>
        {view.memory && (
          <Fact label="Memory from Oracle" icon={<Brain className="size-3.5 text-teal" />}>
            {view.memory.entries === 0 ? "First brief for this patient; nothing remembered yet." : `${view.memory.entries} entries from earlier briefs and decisions, loaded before planning.`}
            {view.memory.written && <span className="ml-1 font-medium text-ok">This brief has been added.</span>}
          </Fact>
        )}
        {view.repairs.map((r, i) => (
          <Fact key={i} label="The verifier sent the draft back" icon={<ShieldAlert className="size-3.5 text-warn" />}>
            <ul className="list-disc space-y-0.5 pl-4">{r.map((p) => <li key={p}>{p}</li>)}</ul>
          </Fact>
        ))}
        {(writing || view.brief) && (
          <Fact label="Brief" icon={<FileText className="size-3.5 text-oracle" />}>
            {view.verified ? (
              <span className={clsx("inline-flex items-center gap-1 font-medium", view.verified.passed ? "text-ok" : "text-oracle")}>
                <ShieldCheck className="size-3.5" /> {view.verified.passed ? `Verified · ${view.verified.citations} citations, every id found in the database` : `Not verified · ${view.verified.problems[0] ?? ""}`}
              </span>
            ) : "Being written from the structured PreVisitBrief…"}
          </Fact>
        )}
        {view.done && (
          <div className="grid grid-cols-3 gap-2">
            {[["time", fmtSeconds(view.done.seconds)], ["tool calls", view.done.tool_calls], ["delegations", view.done.delegations], ["SQL queries", view.done.sql], ["searches", view.done.searches], ["checkpoints", view.checkpoints?.count ?? "–"]].map(([k, v]) => (
              <div key={k} className="rounded-lg border border-line bg-panel px-3 py-2">
                <div className="font-mono text-lg font-semibold text-ink">{v}</div>
                <div className="text-xs uppercase tracking-wide text-ink-3">{k}</div>
              </div>
            ))}
          </div>
        )}
        {view.error && (
          <div className="rounded-lg border border-oracle/40 bg-oracle-soft px-3 py-2 text-sm text-oracle">
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
    <div className="rounded-lg border border-line bg-panel px-4 py-3">
      <Label className="mb-1 flex items-center gap-1.5">{icon}{label}</Label>
      <div className="text-sm text-ink-2">{children}</div>
    </div>
  );
}
