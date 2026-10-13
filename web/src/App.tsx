import clsx from "clsx";
import { Component, Suspense, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { emptyRun, getJSON, reduce, startRun, type Patient, type RunView, type Safety, type StreamItem } from "./api";
import { ActionsPage } from "./components/ActionsPage";
import { AgentsPage } from "./components/AgentsPage";
import { ConfirmReset, Toast } from "./components/Dialog";
import { Header, Tabs, type RunStatus, type TabInfo, type TabKey } from "./components/Header";
import { MemoryPage } from "./components/MemoryPage";
import { PatientPage } from "./components/PatientPage";
import { SafetySheet } from "./components/SafetyPanel";
import { fmtSeconds } from "./hooks";
import { lazyPage, prefetch } from "./lazy";

// react-markdown is the heaviest dependency; it is split off, fetched right
// after the first paint, and reloads the page once if a redeploy removed it.
const BriefPage = lazyPage(() => import("./components/BriefPage"));

type RunSummary = { id: string; patient: string; status: string };

/** A page that fails to render shows a way back instead of blanking the
 * application; the other tabs keep working (the boundary is keyed by tab). */
class PageBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="rounded-lg border border-warn/40 bg-warn-soft p-5 text-sm text-ink-2">
        This page could not load. <button onClick={() => window.location.reload()} className="font-semibold text-oracle underline">Reload</button>; runs and results are kept on the server.
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
  const [tab, setTab] = useState<TabKey>("patient");
  const [showSafety, setShowSafety] = useState(false);
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
  const advanced = useRef<string | undefined>(undefined); // the run whose brief already moved the view forward
  const toastTimer = useRef<number | undefined>(undefined);
  const running = view.status === "starting" || view.status === "running";
  // The run on screen belongs to its own patient, whoever is selected now.
  const runPatient = patients.find((p) => p.key === view.patient) ?? selected;

  const notify = useCallback((text: string) => {
    setToast(text);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(undefined), 7000);
  }, []);

  // Every lazily loaded page is fetched up front, so a redeploy during a talk
  // never leaves a tab without its code.
  useEffect(() => prefetch([() => import("./components/BriefPage"), () => import("./components/Markdown")]), []);

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

  const listen = useCallback((id: string) => {
    source.current?.close();
    const es = new EventSource(`/api/runs/${id}/stream`);
    source.current = es;
    es.onmessage = (m) => setView((v) => reduce(v, JSON.parse(m.data) as StreamItem));
    es.addEventListener("end", () => es.close());
    // A dropped connection is retried by the browser, which sends the last event
    // id it saw; the server continues from there, so nothing shows twice. A
    // source the browser gave up on means the server refused the run: it is
    // gone, reset from elsewhere.
    es.onerror = () => {
      if (es.readyState !== EventSource.CLOSED) return;
      setView((v) => v.id === id && (v.status === "running" || v.status === "starting")
        ? { ...v, status: "failed", error: "This run is no longer on the server (the demo was reset elsewhere). Pick the patient again." }
        : v);
    };
  }, []);

  const resetDemo = useCallback(async () => {
    setResetting(true);
    try {
      const r = await fetch("/api/demo/reset", { method: "POST" });
      const body = await r.json();
      if (!r.ok) throw new Error(body.detail ?? r.statusText);
      source.current?.close();
      advanced.current = undefined;
      setView(emptyRun());
      setTab("patient");
      setNotice(undefined);
      setMemory("");
      setActionCounts({ pending: 0, decided: 0 });
      setEpoch((e) => e + 1);
      notify(`Demo reset${body["runs stopped"] ? `, ${body["runs stopped"]} run stopped` : ""}: ${body["care actions"] ?? 0} actions, ${body["checkpoints"] ?? 0} checkpoints and all memory cleared.`);
    } catch (err) {
      notify(`Reset refused: ${String(err).replace(/^Error: /, "")}`);
    } finally {
      setResetting(false);
      setConfirmReset(false);
    }
  }, [notify]);

  // Runs started elsewhere (another tab, the command line) are listed every few seconds.
  useEffect(() => {
    const poll = () => getJSON<RunSummary[]>("/api/runs")
      .then((rs) => setActive(rs.find((r) => r.status === "running") ?? null)).catch(() => undefined);
    poll();
    const t = setInterval(poll, 4000);
    return () => clearInterval(t);
  }, []);

  // A run in progress for the selected patient is followed as soon as the page
  // knows about it, on the tab the presenter is already looking at.
  useEffect(() => {
    if (!active || !selected || active.patient !== selected.key || view.status !== "idle") return;
    advanced.current = active.id;
    setView({ ...emptyRun(), status: "running", patient: active.patient, id: active.id });
    listen(active.id);
  }, [active, selected, view.status, listen]);

  // Opening a patient replays its latest finished run, so every tab is populated
  // even when the run was started elsewhere or the server was restarted.
  useEffect(() => {
    if (!selected || running) return;
    getJSON<RunSummary[]>("/api/runs").then((rs) => {
      if (rs.some((r) => r.patient === selected.key && r.status === "running")) return; // the effect above follows it
      const last = rs.find((r) => r.patient === selected.key && r.status === "succeeded");
      if (!last || last.id === view.id) return;
      advanced.current = last.id; // a replay stays on the current tab
      setView({ ...emptyRun(), status: "running", patient: selected.key, id: last.id });
      listen(last.id);
    }).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.key, epoch]);

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
  }, [selected, proposals, view.status, tab, epoch, decisions]);

  const countActions = useCallback((as: { status: string }[]) => {
    const open = (s: string) => s === "proposed" || s === "needs_physician";
    setActionCounts({ pending: as.filter((a) => open(a.status)).length, decided: as.filter((a) => !open(a.status)).length });
  }, []);

  const run = useCallback(async () => {
    if (!selected || !question.trim()) return;
    if (active && active.id !== view.id) {
      setNotice(`The sandbox is busy with a run for Patient ${active.patient}. Watch it, or try again when it finishes.`);
      return;
    }
    setNotice(undefined);
    setView({ ...emptyRun(), status: "starting", patient: selected.key });
    setTab("agents");
    try {
      const { id } = await startRun(selected.key, question);
      setView((v) => ({ ...v, id }));
      listen(id);
    } catch (err) {
      setNotice(String(err).replace(/^Error: /, ""));
      setView(emptyRun());
      setTab("patient");
    }
  }, [selected, question, active, view.id, listen]);

  const watch = useCallback(() => {
    if (!active) return;
    const p = patients.find((x) => x.key === active.patient);
    if (p) { setSelected(p); setQuestion(p.question); }
    setNotice(undefined);
    setView({ ...emptyRun(), status: "running", patient: active.patient, id: active.id });
    setTab("agents");
    listen(active.id);
  }, [active, patients, listen]);

  // When the brief of a run the presenter started lands, open it once.
  useEffect(() => {
    if (view.brief && view.id && advanced.current !== view.id) {
      advanced.current = view.id;
      setTab("brief");
    }
  }, [view.brief, view.id]);

  const pick = (p: Patient) => {
    if (p.key === selected?.key) return; // already on this patient: the run on screen stays
    setSelected(p);
    setQuestion(p.question);
    if (!running) { source.current?.close(); setView(emptyRun()); setTab("patient"); }
  };

  const memoryEntries = (memory ?? "").split("\n## ").length - 1;
  const status: RunStatus = running ? { text: "Agents running", tone: "live" }
    : view.verified?.passed ? { text: `Brief verified · ${view.verified.citations} citations`, tone: "ok" }
    : view.status === "rejected" ? { text: "Brief rejected by the gate", tone: "bad" } : null;
  const tabs: TabInfo[] = useMemo(() => [
    { key: "patient", label: "Patient" },
    { key: "agents", label: "Agents", status: running ? "running" : view.done ? fmtSeconds(view.done.seconds) : view.status === "failed" ? "failed" : undefined, tone: running ? "live" : "muted" },
    { key: "brief", label: "Brief", status: view.verified?.passed ? "verified" : view.status === "rejected" ? "rejected" : undefined, tone: view.verified?.passed ? "ok" : view.status === "rejected" ? "warn" : "muted" },
    { key: "actions", label: "Actions", status: actionCounts.pending ? `${actionCounts.pending} to review` : actionCounts.decided ? `${actionCounts.decided} decided` : undefined, tone: actionCounts.pending ? "warn" : "muted" },
    { key: "memory", label: "Memory", status: memoryEntries ? `${memoryEntries} ${memoryEntries === 1 ? "entry" : "entries"}` : undefined },
  ], [running, view.done, view.status, view.verified, actionCounts, memoryEntries]);

  return (
    <div className="flex h-full flex-col">
      <Header patients={patients} selected={selected} onSelect={pick} disabled={resetting} status={status}
        onSafety={() => setShowSafety(true)} onReset={() => setConfirmReset(true)} />
      <Tabs tabs={tabs} current={tab} onGo={setTab} />

      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className={clsx("mx-auto h-full px-5 py-4", tab === "agents" ? "max-w-[1680px]" : "max-w-[1240px]")}>
          <PageBoundary key={tab}>
            {tab === "patient" && selected && (
              <PatientPage key={selected.key} patient={selected} question={question} setQuestion={setQuestion} onRun={run} running={running}
                notice={notice} active={active && active.id !== view.id ? active : null} onWatch={watch} refresh={epoch}
                memoryEntries={memoryEntries} onMemory={() => setTab("memory")} />
            )}
            {tab === "agents" && (
              <AgentsPage view={view} running={running} question={view.meta?.question ?? question} patientName={runPatient?.display_name ?? ""}
                onBrief={() => setTab("brief")} onPatient={() => setTab("patient")} />
            )}
            {tab === "brief" && (
              <Suspense fallback={null}>
                <BriefPage view={view} patientName={runPatient?.display_name ?? ""} running={running} pending={actionCounts.pending}
                  onActions={() => setTab("actions")} onPatient={() => setTab("patient")} notify={notify} />
              </Suspense>
            )}
            {tab === "actions" && selected && (
              <ActionsPage key={selected.key} patientKey={selected.key} refreshKey={`${view.status}:${proposals}`}
                onDecided={() => setDecisions((d) => d + 1)} onLoaded={countActions} onMemory={() => setTab("memory")} />
            )}
            {tab === "memory" && selected && (
              <MemoryPage patient={selected} memory={memory} entries={memoryEntries} checkpoints={view.checkpoints} onPatient={() => setTab("patient")} />
            )}
          </PageBoundary>
        </div>
      </main>

      {confirmReset && <ConfirmReset busy={resetting} runInProgress={running || active !== null} onCancel={() => setConfirmReset(false)} onConfirm={resetDemo} />}
      {toast && <Toast text={toast} />}
      {showSafety && <SafetySheet safety={safety} onClose={() => setShowSafety(false)} />}
    </div>
  );
}
