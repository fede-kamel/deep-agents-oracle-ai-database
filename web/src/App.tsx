import clsx from "clsx";
import { Brain, Database, ListTree, Play, ShieldCheck, Sparkles, SquareTerminal, X } from "lucide-react";
import { Component, lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { emptyRun, getJSON, reduce, startRun, type Patient, type RunView, type Safety, type StreamItem } from "./api";
import { ActionsPanel } from "./components/ActionsPanel";
import { AgentTrace } from "./components/AgentTrace";
import { FlowStepper, StepPage, type Step, type StepInfo } from "./components/Flow";
import { PatientView } from "./components/PatientView";
import { RunTimeline } from "./components/RunTimeline";
import { SandboxConsole } from "./components/SandboxConsole";
import { SafetyView, TopBar } from "./components/Shell";

// react-markdown is the heaviest dependency; load it with the first brief.
const BriefViewer = lazy(() => import("./components/BriefViewer"));

type Inspect = "trace" | "console" | "safety" | null;

/** A panel that fails to render (for example a chunk that no longer exists
 * after a redeploy) shows a way back instead of blanking the whole page. */
class PanelBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="rounded-xl border border-ochre/40 bg-ochre-soft p-5 text-[13px] text-ink-2">
        This panel could not load. <button onClick={() => window.location.reload()} className="font-semibold text-oracle underline">Reload the page</button>; the run and its results are kept on the server.
      </div>
    );
  }
}

export default function App() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [safety, setSafety] = useState<Safety>();
  const [selected, setSelected] = useState<Patient>();
  const [question, setQuestion] = useState("");
  const [view, setView] = useState<RunView>(emptyRun());
  const [step, setStep] = useState<Step>("patient");
  const [inspect, setInspect] = useState<Inspect>(null);
  const [notice, setNotice] = useState<string>();
  const [active, setActive] = useState<{ id: string; patient: string } | null>(null);
  const [actionCounts, setActionCounts] = useState({ pending: 0, decided: 0 });
  const [memory, setMemory] = useState<string>();
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [toast, setToast] = useState<string>();
  const [epoch, setEpoch] = useState(0); // bumps after a reset to refetch everything
  const [decisions, setDecisions] = useState(0); // bumps after each decision: counts and memory change
  const source = useRef<EventSource | null>(null);
  const advanced = useRef<string | undefined>(undefined);
  const running = view.status === "starting" || view.status === "running";
  // The run on screen belongs to its own patient, whoever is selected now.
  const runPatient = patients.find((p) => p.key === view.patient) ?? selected;

  useEffect(() => {
    getJSON<Patient[]>("/api/patients").then((ps) => {
      setPatients(ps);
      // Keep the patient the presenter picked; the list refreshes after a reset
      // and may arrive after they have already switched.
      setSelected((cur) => {
        const keep = ps.find((p) => p.key === cur?.key);
        if (!keep && ps[0]) setQuestion(ps[0].question);
        return keep ?? ps[0];
      });
    });
    getJSON<Safety>("/api/safety").then(setSafety);
  }, [epoch]);

  const resetDemo = useCallback(async () => {
    setResetting(true);
    try {
      const r = await fetch("/api/demo/reset", { method: "POST" });
      const body = await r.json();
      if (!r.ok) throw new Error(body.detail ?? r.statusText);
      source.current?.close();
      advanced.current = undefined;
      setView(emptyRun());
      setStep("patient");
      setNotice(undefined);
      setMemory("");
      setActionCounts({ pending: 0, decided: 0 });
      setEpoch((e) => e + 1);
      setToast(`Demo reset${body["runs stopped"] ? `, ${body["runs stopped"]} run stopped` : ""}: ${body["care actions"] ?? 0} actions, ${body["checkpoints"] ?? 0} checkpoints and all memory cleared. Start with step 1.`);
    } catch (err) {
      setToast(`Reset refused: ${String(err).replace(/^Error: /, "")}`);
    } finally {
      setResetting(false);
      setConfirmReset(false);
      setTimeout(() => setToast(undefined), 7000);
    }
  }, []);

  // Runs started elsewhere (another tab, Codex, the evidence flow) can be watched.
  useEffect(() => {
    const poll = () => getJSON<{ id: string; patient: string; status: string }[]>("/api/runs")
      .then((rs) => setActive(rs.find((r) => r.status === "running") ?? null)).catch(() => undefined);
    poll();
    const t = setInterval(poll, 4000);
    return () => clearInterval(t);
  }, []);

  // The workflow and memory belong to the patient; refresh them as the run moves.
  const proposals = view.events.filter((e) => e.type === "tool_result" && /^(propose|draft)_/.test(String(e.name))).length;
  useEffect(() => {
    if (!selected) return;
    let current = true; // ignore answers for a patient or a state we have left
    getJSON<{ status: string }[]>(`/api/patients/${selected.key}/actions`)
      .then((as) => current && setActionCounts({ pending: as.filter((a) => a.status === "proposed" || a.status === "needs_physician").length, decided: as.filter((a) => a.status !== "proposed" && a.status !== "needs_physician").length }))
      .catch(() => undefined);
    getJSON<{ text: string }>(`/api/patients/${selected.key}/memory`).then((m) => current && setMemory(m.text)).catch(() => current && setMemory(""));
    return () => { current = false; };
  }, [selected, proposals, view.status, step, epoch, decisions]);

  const countActions = useCallback((as: { status: string }[]) => {
    const open = (s: string) => s === "proposed" || s === "needs_physician";
    setActionCounts({ pending: as.filter((a) => open(a.status)).length, decided: as.filter((a) => !open(a.status)).length });
  }, []);

  const listen = useCallback((id: string) => {
    source.current?.close();
    const es = new EventSource(`/api/runs/${id}/stream`);
    source.current = es;
    es.onmessage = (m) => setView((v) => reduce(v, JSON.parse(m.data) as StreamItem));
    es.addEventListener("end", () => es.close());
  }, []);

  const run = useCallback(async () => {
    if (!selected || !question.trim()) return;
    if (active && active.id !== view.id) {
      setNotice(`The sandbox is busy with a run for Patient ${active.patient}. Watch it, or try again when it finishes.`);
      return;
    }
    setNotice(undefined);
    setView({ ...emptyRun(), status: "starting", patient: selected.key });
    setStep("work");
    try {
      const { id } = await startRun(selected.key, question);
      setView((v) => ({ ...v, id }));
      listen(id);
    } catch (err) {
      setNotice(String(err).replace(/^Error: /, ""));
      setView(emptyRun());
      setStep("patient");
    }
  }, [selected, question, active, view.id, listen]);

  const watch = useCallback(() => {
    if (!active) return;
    const p = patients.find((x) => x.key === active.patient);
    if (p) { setSelected(p); setQuestion(p.question); }
    setNotice(undefined);
    setView({ ...emptyRun(), status: "running", patient: active.patient, id: active.id });
    setStep("work");
    listen(active.id);
  }, [active, patients, listen]);

  // Opening a patient replays its latest finished run, so every step of the
  // story is populated even when the run was started elsewhere.
  useEffect(() => {
    if (!selected || running) return;
    getJSON<{ id: string; patient: string; status: string }[]>("/api/runs").then((rs) => {
      const last = rs.find((r) => r.patient === selected.key && r.status === "succeeded");
      if (!last || last.id === view.id) return;
      advanced.current = last.id; // replaying: stay on the current step
      setView({ ...emptyRun(), status: "running", patient: selected.key, id: last.id });
      listen(last.id);
    }).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.key, epoch]);

  // When the brief lands, move the story forward once.
  useEffect(() => {
    if (view.brief && view.id && advanced.current !== view.id) {
      advanced.current = view.id;
      setStep("brief");
    }
  }, [view.brief, view.id]);

  const pick = (p: Patient) => {
    setSelected(p);
    setQuestion(p.question);
    if (!running) { source.current?.close(); setView(emptyRun()); setStep("patient"); }
  };

  const memoryEntries = (memory ?? "").split("\n## ").length - 1;
  const steps: StepInfo[] = useMemo(() => [
    { key: "patient", title: "Patient", hint: selected ? selected.situation : "pick a patient", state: view.status === "idle" ? "ready" : "done" },
    { key: "work", title: "Agents at work",
      hint: running ? `${view.todos.filter((t) => t.status === "completed").length}/${view.todos.length || "…"} planned · ${view.lanes.length} specialists`
        : view.done ? `${view.done.tool_calls} tool calls in ${Math.round(view.done.seconds)} s` : "in the OpenShell sandbox",
      state: running ? "active" : view.status === "idle" ? "waiting" : "done" },
    { key: "brief", title: "Brief", hint: view.verified?.passed ? `verified · ${view.verified.citations} citations` : running ? "being written…" : "the cited document",
      state: view.brief ? "done" : "waiting" },
    { key: "actions", title: "Actions", hint: actionCounts.pending ? `${actionCounts.pending} to review` : actionCounts.decided ? `${actionCounts.decided} decided` : "agent proposals",
      state: actionCounts.pending ? "ready" : actionCounts.decided ? "done" : "waiting" },
    { key: "memory", title: "Memory", hint: memoryEntries ? `${memoryEntries} ${memoryEntries === 1 ? "entry" : "entries"} in OracleStore` : "what it will remember",
      state: memoryEntries ? "done" : "ready" },
  ], [selected, view, running, actionCounts, memoryEntries]);

  return (
    <div className="flex h-full flex-col">
      <TopBar patients={patients} selected={selected} onSelect={pick} disabled={resetting} view={view} safety={safety}
        onReset={() => setConfirmReset(true)} />
      <div className="flex items-stretch border-b border-line bg-panel">
        <div className="min-w-0 flex-1"><FlowStepper steps={steps} current={step} onGo={setStep} /></div>
        <div className="flex shrink-0 items-center gap-1 border-l border-line px-3">
          <span className="mr-1 text-[10.5px] font-semibold uppercase tracking-wide text-ink-3">Inspect</span>
          <InspectButton icon={ListTree} label="Trace" count={view.events.length} onClick={() => setInspect("trace")} />
          <InspectButton icon={SquareTerminal} label="Console" count={view.console.filter((l) => l.startsWith("[agent:")).length} onClick={() => setInspect("console")} />
          <InspectButton icon={ShieldCheck} label="Safety" onClick={() => setInspect("safety")} />
        </div>
      </div>

      <main className="min-h-0 flex-1 bg-paper">
        {step === "patient" && selected && (
          <StepPage eyebrow="Step 1 · the patient" title={selected.situation}
            lead={<>Read the situation, then ask the agents for a pre-visit brief. They run in an NVIDIA OpenShell sandbox with the database login of {selected.display_name} alone, and nothing is sent anywhere without your approval.</>}>
            <div className="mx-auto max-w-[1180px] space-y-4">
              <AskCard question={question} setQuestion={setQuestion} onRun={run} running={running} notice={notice}
                active={active && active.id !== view.id ? active : null} onWatch={watch} onReset={() => setQuestion(selected.question)} />
              <PatientView patient={selected} refresh={epoch} />
            </div>
          </StepPage>
        )}

        {step === "work" && (
          <StepPage eyebrow="Step 2 · agents at work, inside the sandbox"
            title={running ? "The agents are researching" : view.done ? "The agents have finished" : "No run yet"}
            lead={<>The lead plans, then hands the work to specialists: one reads the chart with SQL, two search the reference and PubMed stores, one proposes actions. On the right, the sandbox console: each agent's step, written from inside the sandbox, next to the network decision it caused.</>}
            primary={view.brief ? { label: "Read the brief", onClick: () => setStep("brief") } : undefined}
            secondary={running ? "Keep watching; the brief opens when the gate accepts it." : view.error ? <span className="text-oracle">{view.error}</span> : null}>
            <div className="grid h-full min-h-[560px] grid-cols-1 gap-4 xl:grid-cols-[1.1fr_1fr] 2xl:grid-cols-[1.25fr_1fr]">
              <div className="scroll-thin min-h-0 overflow-y-auto pr-1">
                <RunTimeline view={view} question={view.meta?.question ?? question} patientName={runPatient?.display_name ?? ""} />
              </div>
              <div className="min-h-[520px]"><SandboxConsole lines={view.console} live={running} defaultFilter="agents" /></div>
            </div>
          </StepPage>
        )}

        {step === "brief" && (
          <StepPage eyebrow="Step 3 · the brief" title={view.brief ? "A brief you can check line by line" : "The brief appears here"}
            lead={<>Every claim carries a chip: a table row, a chart note, the NIH reference, or a PubMed abstract. The gate accepted it only after finding every one of those ids in the database, as this patient's own user.</>}
            primary={{ label: actionCounts.pending ? `Review ${actionCounts.pending} proposed actions` : "Go to actions", onClick: () => setStep("actions") }}
            secondary={view.verified?.passed ? <span className="flex items-center gap-1.5 text-moss"><ShieldCheck className="size-3.5" /> verified · {view.verified.citations} citations · Word and Markdown export above the document</span> : null}>
            <div className="h-full min-h-[600px]">
              <PanelBoundary><Suspense fallback={null}>
                <BriefViewer brief={view.brief} runId={view.id} running={running} patientName={runPatient?.display_name} wide />
              </Suspense></PanelBoundary>
            </div>
          </StepPage>
        )}

        {step === "actions" && selected && (
          <StepPage eyebrow="Step 4 · actions, with you in the loop" title="Review what the agent proposes"
            lead={<>The agents can only propose. You approve or reject each card; on approval the database executes it (a lab order, a portal message, an appointment request) and audits every step. Policy decides who may do what: the database refuses a medication change from the care coordinator, so it escalates to the medication-safety agent, and only the doctor can approve that agent's proposal. Nothing real is sent: every patient is synthetic.</>}
            primary={{ label: "See what the agent will remember", onClick: () => setStep("memory") }}
            secondary={`${actionCounts.pending} awaiting you · ${actionCounts.decided} decided`}>
            <div className="mx-auto max-w-[980px]"><ActionsPanel patientKey={selected.key} refreshKey={`${view.status}:${proposals}:${step}`} onDecided={() => setDecisions((d) => d + 1)} onLoaded={countActions} /></div>
          </StepPage>
        )}

        {step === "memory" && selected && (
          <StepPage eyebrow="Step 5 · memory" title="What the agent will remember about this patient"
            lead={<>The system, not the model, writes this memory: each accepted brief and each of your decisions. The next brief loads it from Oracle (OracleStore), says what changed, and never proposes again what you approved, executed or rejected.</>}
            primary={{ label: "Run again with this memory", onClick: () => setStep("patient") }}
            secondary={view.checkpoints ? `${view.checkpoints.count} checkpoints for the last run in OracleSaver · thread ${view.checkpoints.thread_id}` : null}>
            <div className="mx-auto max-w-[980px] space-y-3">
              <div className="flex items-center gap-2 rounded-xl border border-teal/25 bg-teal-soft/40 px-4 py-2.5 text-[12.5px] text-ink-2">
                <Brain className="size-4 shrink-0 text-teal" /> /memories/patient-history.md · OracleStore (langgraph-oracledb), IVF vector index · in {selected.db_user}'s own schema · read-only to the agent
              </div>
              <pre className="whitespace-pre-wrap rounded-2xl border border-line bg-panel p-6 font-sans text-[13px] leading-relaxed text-ink-2">
                {memory ? memory : "Nothing yet. Run a brief and decide on its actions; both are recorded here."}
              </pre>
            </div>
          </StepPage>
        )}
      </main>

      {confirmReset && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-ink/30 backdrop-blur-[2px]" onClick={() => !resetting && setConfirmReset(false)}>
          <div className="w-[520px] rounded-2xl border border-line bg-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-oracle">Reset the demo</div>
            <h2 className="mt-1 text-[18px] font-semibold">Clear everything and start again?</h2>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-[13px] text-ink-2">
              <li>every proposed and decided care action, and its audit trail</li>
              <li>the lab orders, portal messages and appointment requests they created</li>
              <li>each patient's memory (OracleStore) and the agents' checkpoints (OracleSaver)</li>
              <li>physician orders from approved medication changes (the medications return to active)</li>
              <li>the runs this application remembers, stopping any run in progress</li>
            </ul>
            {(running || active) && (
              <p className="mt-3 rounded-lg border border-ochre/30 bg-ochre-soft px-3 py-2 text-[12.5px] text-ink-2">A run is in progress: it will be stopped and its sandbox deleted first.</p>
            )}
            <p className="mt-3 text-[12.5px] text-ink-3">The synthetic charts, the reference stores and every configuration stay as they are.</p>
            <div className="mt-5 flex justify-end gap-2">
              <button disabled={resetting} onClick={() => setConfirmReset(false)} className="rounded-lg border border-line px-3.5 py-2 text-[13px] text-ink-2 hover:text-ink">Cancel</button>
              <button disabled={resetting} onClick={resetDemo} className="flex items-center gap-2 rounded-lg bg-oracle px-4 py-2 text-[13px] font-semibold text-white hover:bg-[#b23d2d]">
                {resetting ? <Sparkles className="size-4 animate-pulse" /> : null}{resetting ? "Resetting…" : "Reset the demo"}
              </button>
            </div>
          </div>
        </div>
      )}
      {toast && (
        <div className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-ink px-4 py-2.5 text-[12.5px] text-white shadow-xl">{toast}</div>
      )}
      {inspect && (
        <Overlay title={inspect === "trace" ? "Agent trace" : inspect === "console" ? "OpenShell sandbox console" : "Safety"} onClose={() => setInspect(null)}>
          {inspect === "trace" && <AgentTrace events={view.events} />}
          {inspect === "console" && <SandboxConsole lines={view.console} live={running} />}
          {inspect === "safety" && <div className="scroll-thin h-full overflow-y-auto"><SafetyView safety={safety} /></div>}
        </Overlay>
      )}
    </div>
  );
}

function InspectButton({ icon: Icon, label, count, onClick }: { icon: typeof Database; label: string; count?: number; onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex items-center gap-1.5 rounded-lg border border-line bg-panel px-2.5 py-1.5 text-[12px] text-ink-2 hover:border-ink-3/40 hover:text-ink">
      <Icon className="size-3.5" /> {label}
      {count ? <span className="rounded-full bg-sand px-1.5 font-mono text-[10px] text-ink-3">{count}</span> : null}
    </button>
  );
}

function Overlay({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-ink/30 p-6 backdrop-blur-[2px]" onClick={onClose}>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-line bg-paper shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex shrink-0 items-center border-b border-line bg-panel px-5 py-3">
          <span className="text-[14px] font-semibold">{title}</span>
          <span className="ml-3 text-[11.5px] text-ink-3">Esc to close</span>
          <button onClick={onClose} className="ml-auto rounded-md p-1 text-ink-3 hover:bg-sand hover:text-ink"><X className="size-4" /></button>
        </div>
        <div className="min-h-0 flex-1 p-4">{children}</div>
      </div>
    </div>
  );
}

function AskCard({ question, setQuestion, onRun, running, notice, active, onWatch, onReset }: {
  question: string; setQuestion: (q: string) => void; onRun: () => void; running: boolean; notice?: string;
  active: { id: string; patient: string } | null; onWatch: () => void; onReset: () => void;
}) {
  return (
    <div className="rounded-2xl border border-oracle/30 bg-panel p-5 shadow-[0_12px_32px_-24px_rgb(199_70_52/.6)]">
      <div className="text-[12.5px] font-semibold text-ink">What should the agents prepare?</div>
      <div className="mt-2 flex items-stretch gap-3">
        <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} disabled={running}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onRun(); } }}
          className="flex-1 resize-none rounded-xl border border-line bg-paper px-3.5 py-2.5 text-[13.5px] leading-relaxed outline-none focus:border-ink-3/50 focus:ring-4 focus:ring-sand" />
        <button onClick={onRun} disabled={running || !question.trim()}
          className={clsx("flex w-[190px] shrink-0 flex-col items-center justify-center gap-1 rounded-xl text-[13.5px] font-semibold text-white shadow-sm transition",
            running ? "bg-ink-3" : "bg-oracle hover:bg-[#b23d2d]")}>
          {running ? <Sparkles className="size-5 animate-pulse" /> : <Play className="size-5" />}
          {running ? "Agents running…" : "Run in sandbox"}
          <span className="text-[10.5px] font-normal opacity-75">or press Enter</span>
        </button>
      </div>
      <div className="mt-2 flex items-center gap-3 text-[11px] text-ink-3">
        <span>Shift+Enter for a new line · the input guard blocks real-looking identifiers and other patients' ids</span>
        <button onClick={onReset} disabled={running} className="ml-auto hover:text-ink">reset the question</button>
      </div>
      {(notice || active) && (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-ochre/30 bg-ochre-soft px-3 py-2 text-[12.5px] text-ink-2">
          <Sparkles className="size-3.5 shrink-0 text-ochre" />
          <span>{notice ?? `A run for Patient ${active?.patient} is in progress in the sandbox.`}</span>
          {active && <button onClick={onWatch} className="ml-auto shrink-0 rounded-md bg-ink px-2.5 py-1 text-[12px] font-semibold text-white">Watch live</button>}
        </div>
      )}
    </div>
  );
}
