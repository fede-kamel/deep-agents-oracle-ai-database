import clsx from "clsx";
import {
  Activity, Boxes, ClipboardCheck, Cpu, Database, FileText, HeartPulse, ListTree, Play, ShieldCheck, Sparkles,
  RotateCcw, SquareTerminal, UserRound, Wind,
} from "lucide-react";
import { useEffect, useState } from "react";
import type { Patient, RunView, Safety } from "../api";

export type Workspace = "patient" | "live" | "trace" | "sandbox" | "actions" | "brief" | "safety";

const PATIENT_ICON = { X: Activity, Y: HeartPulse, Z: Wind } as const;
const PATIENT_TONE = { X: "text-teal", Y: "text-oracle", Z: "text-violet" } as const;

export function TopBar({ patients, selected, onSelect, disabled, view, safety, onReset }: {
  patients: Patient[]; selected?: Patient; onSelect: (p: Patient) => void; disabled: boolean; view: RunView; safety?: Safety;
  onReset: () => void;
}) {
  const running = view.status === "running" || view.status === "starting";
  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-line bg-panel px-4">
      <div className="flex items-center gap-2.5">
        <div className="grid size-8 place-items-center rounded-lg bg-oracle shadow-sm"><div className="h-3 w-5 rounded-full border-[2.5px] border-white" /></div>
        <div className="leading-tight">
          <div className="text-[14px] font-semibold tracking-tight">Deep Agents on Your Own Data</div>
          <div className="text-[10.5px] text-ink-3">langchain-oracle · Oracle AI Database 26ai · NVIDIA OpenShell</div>
        </div>
      </div>

      <div className="ml-4 flex items-center gap-1 rounded-xl bg-sand p-1">
        {patients.map((p) => {
          const Icon = PATIENT_ICON[p.key];
          const on = selected?.key === p.key;
          return (
            <button key={p.key} disabled={disabled} onClick={() => onSelect(p)} title={`${p.situation} · ${p.visit_reason}`}
              className={clsx("flex items-center gap-2 rounded-lg px-3 py-1.5 text-left transition",
                on ? "bg-panel shadow-sm" : "hover:bg-panel/60", disabled && !on && "opacity-50")}>
              <Icon className={clsx("size-4", PATIENT_TONE[p.key])} strokeWidth={2.3} />
              <div className="leading-tight">
                <div className="text-[12.5px] font-semibold">{p.display_name}</div>
                <div className="max-w-[170px] truncate text-[10.5px] text-ink-3">{p.situation}</div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="ml-auto flex items-center gap-2 text-[11px]">
        {running ? (
          <span className="flex items-center gap-1.5 rounded-full bg-oracle px-2.5 py-1 font-semibold text-white"><span className="live-dot size-1.5 rounded-full bg-white" /> agents running</span>
        ) : view.verified?.passed ? (
          <span className="flex items-center gap-1.5 rounded-full bg-moss-soft px-2.5 py-1 font-semibold text-moss"><ShieldCheck className="size-3.5" /> brief verified · {view.verified.citations} citations</span>
        ) : null}
        <span className="flex items-center gap-1.5 rounded-full bg-teal-soft px-2.5 py-1 font-medium text-teal"><Cpu className="size-3.5" /> {safety ? `${safety.chat_model.replace("openai.", "")} + ${safety.worker_model.replace("google.", "")}` : "OCI Generative AI"}</span>
        <span className="rounded-full bg-ink px-2.5 py-1 font-semibold tracking-wide text-white">SYNTHETIC DATA</span>
        <button onClick={onReset} disabled={disabled && false} title="Clear every run, action, memory and checkpoint, and start the demo again"
          className="flex items-center gap-1.5 rounded-full border border-line bg-panel px-3 py-1 font-semibold text-ink-2 transition hover:border-oracle/50 hover:text-oracle disabled:opacity-40">
          <RotateCcw className="size-3.5" /> Reset demo
        </button>
      </div>
    </header>
  );
}

export function NavRail({ ws, setWs, view }: { ws: Workspace; setWs: (w: Workspace) => void; view: RunView }) {
  const running = view.status === "running" || view.status === "starting";
  const proposals = view.events.filter((e) => e.type === "tool" && /^(propose|draft)_/.test(String(e.name))).length;
  const steps = view.console.filter((l) => l.startsWith("[agent:")).length;
  const items: { key: Workspace; label: string; icon: typeof Activity; badge?: string | number | null; tone?: string }[] = [
    { key: "patient", label: "Patient", icon: UserRound },
    { key: "live", label: "Live run", icon: Sparkles, badge: running ? "live" : view.done ? "done" : null, tone: running ? "bg-oracle text-white" : "bg-moss-soft text-moss" },
    { key: "trace", label: "Trace", icon: ListTree, badge: view.events.length || null },
    { key: "sandbox", label: "Sandbox", icon: SquareTerminal, badge: steps || null },
    { key: "actions", label: "Actions", icon: ClipboardCheck, badge: proposals || null, tone: "bg-ochre-soft text-ochre" },
    { key: "brief", label: "Brief", icon: FileText, badge: view.brief ? "✓" : null, tone: "bg-moss-soft text-moss" },
    { key: "safety", label: "Safety", icon: ShieldCheck },
  ];
  return (
    <nav className="flex w-[84px] shrink-0 flex-col items-center gap-1 border-r border-line bg-panel py-3">
      {items.map((it) => {
        const Icon = it.icon;
        const on = ws === it.key;
        return (
          <button key={it.key} onClick={() => setWs(it.key)}
            className={clsx("relative flex w-[68px] flex-col items-center gap-1 rounded-xl py-2.5 text-[10.5px] font-medium transition",
              on ? "bg-oracle-soft text-oracle" : "text-ink-3 hover:bg-sand hover:text-ink")}>
            <Icon className="size-[18px]" strokeWidth={on ? 2.4 : 2} />
            {it.label}
            {it.badge ? (
              <span className={clsx("absolute right-1 top-1 min-w-[18px] rounded-full px-1 text-center text-[9.5px] font-semibold leading-[16px]", it.tone ?? "bg-sand text-ink-2")}>{it.badge}</span>
            ) : null}
          </button>
        );
      })}
    </nav>
  );
}

const KEY_LABS: Record<Patient["key"], string[]> = { X: ["eGFR", "HbA1c", "UACR"], Y: ["BNP", "Potassium", "eGFR"], Z: ["FEV1", "Sodium", "Eosinophils"] };

export function PatientBar({ patient, question, setQuestion, onRun, running, notice, active, onWatch, onReset }: {
  patient?: Patient; question: string; setQuestion: (q: string) => void; onRun: () => void; running: boolean;
  notice?: string; active?: { id: string; patient: string } | null; onWatch: () => void; onReset: () => void;
}) {
  if (!patient) return null;
  const labs = (patient.latest_labs ?? []).filter((l) => KEY_LABS[patient.key].includes(l.test));
  return (
    <div className="shrink-0 border-b border-line bg-panel px-5 py-3">
      <div className="flex items-center gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[15px] font-semibold">{patient.display_name}</span>
            <span className="rounded bg-sand px-1.5 py-0.5 font-mono text-[10px] text-ink-3">{patient.id}</span>
            <span className="text-[12px] text-ink-3">{patient.age} · {patient.sex}</span>
          </div>
          <div className="truncate text-[12.5px] text-ink-2">{patient.situation} · <span className="text-ink-3">{patient.visit_reason}</span></div>
        </div>
        <div className="flex gap-1.5">
          {labs.map((l) => (
            <div key={l.test} className="rounded-lg bg-sand/80 px-2.5 py-1 text-center">
              <div className="text-[9.5px] uppercase tracking-wide text-ink-3">{l.test}</div>
              <div className="font-mono text-[13px] font-semibold">{Number.isInteger(l.value) ? l.value : l.value.toFixed(1)}</div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-ink-3">
          <Database className="size-3.5" /><span className="font-mono">{patient.db_user}</span> · sees {patient.visible_patients ?? 1} patient
        </div>
      </div>
      <div className="mt-2.5 flex items-stretch gap-2">
        <div className="flex flex-1 items-center rounded-xl border border-line bg-paper px-3 focus-within:border-ink-3/50 focus-within:ring-4 focus-within:ring-sand">
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={1} disabled={running}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onRun(); } }}
            placeholder="Ask for a pre-visit brief…"
            className="max-h-24 min-h-[40px] w-full resize-none bg-transparent py-2.5 text-[13px] leading-snug outline-none placeholder:text-ink-3" />
          <button onClick={onReset} disabled={running} className="ml-2 shrink-0 text-[11px] text-ink-3 hover:text-ink">reset</button>
        </div>
        <button onClick={onRun} disabled={running || !question.trim()}
          className={clsx("flex shrink-0 items-center gap-2 rounded-xl px-5 text-[13px] font-semibold text-white shadow-sm transition",
            running ? "bg-ink-3" : "bg-oracle hover:bg-[#b23d2d]")}>
          {running ? <Sparkles className="size-4 animate-pulse" /> : <Play className="size-4" />}
          {running ? "Agents running…" : "Run in sandbox"}
        </button>
      </div>
      {(notice || active) && (
        <div className="mt-2 flex items-center gap-2 rounded-lg border border-ochre/30 bg-ochre-soft px-3 py-1.5 text-[12px] text-ink-2">
          <Boxes className="size-3.5 shrink-0 text-ochre" />
          <span>{notice ?? `A run for Patient ${active?.patient} is in progress in the sandbox.`}</span>
          {active && <button onClick={onWatch} className="ml-auto shrink-0 rounded-md bg-ink px-2.5 py-1 text-[11.5px] font-semibold text-white">Watch live</button>}
        </div>
      )}
      <div className="mt-1.5 text-[10.5px] text-ink-3">Enter to run · Shift+Enter for a new line · the input guard blocks real-looking identifiers and other patients' ids</div>
    </div>
  );
}

export function SafetyView({ safety }: { safety?: Safety }) {
  const [policies, setPolicies] = useState<{ code: string; kind: string; required_role: string; allowed_proposer: string; rule: string }[]>([]);
  useEffect(() => { fetch("/api/policies").then((r) => r.json()).then(setPolicies).catch(() => undefined); }, []);
  const db = [
    ["Agent user reads one patient", "row-level security (VPD) on every chart table and the note vectors", "verify.py: 0 rows of another patient"],
    ["Agent user proposes, never acts", "INSERT on care_action only; trigger forces 'proposed'; update_check refuses other patients", "ORA-28115 · ORA-41900 · ORA-06550"],
    ["Policy names the agent, too", "each tool stamps its session with the agent's name; CP-03 refuses a medication change from any agent but medication-safety", "ORA-20014 · logged in policy_event"],
    ["Clinician approves, database executes", "DA_CLINICIAN holds EXECUTE on DECIDE_CARE_ACTION; every step audited", "proposed > approved > executed"],
    ["Synthetic only", "CHECK is_synthetic = 'Y', ids must start with SYN-", "ORA-02290"],
    ["Agent state in its own schema", "OracleSaver checkpoints, OracleStore memory; 64 MB quota", "memory read-only to the agent"],
  ];
  return (
    <div className="mx-auto max-w-[1100px] space-y-4">
      <div className="rounded-2xl border border-line bg-panel p-6">
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-moss">Safe by construction</div>
        <h1 className="mt-1 text-[22px] font-semibold tracking-tight">Four layers, each measured, none asks the agent to behave</h1>
        <p className="mt-1 text-[13.5px] text-ink-3">The sandbox decides what the agent can reach, the database decides what it can read and write, the guards decide what it can be asked, and the gate decides what it can say.</p>
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <section className="rounded-2xl border border-line bg-panel p-5">
          <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">NVIDIA OpenShell sandbox</h3>
          <table className="w-full text-[12.5px]">
            <tbody>
              {(safety?.egress ?? []).map((e) => (
                <tr key={e.rule} className="border-b border-line/60 align-top last:border-0">
                  <td className="py-2 pr-3"><span className="rounded bg-moss-soft px-1.5 py-0.5 text-[10.5px] font-semibold text-moss">ALLOWED</span></td>
                  <td className="py-2 pr-3"><div className="font-mono text-[11.5px] text-ink">{e.target}</div><div className="text-ink-3">{e.allow}</div></td>
                  <td className="py-2 text-ink-3">{e.credential}</td>
                </tr>
              ))}
              <tr><td className="py-2 pr-3"><span className="rounded bg-oracle-soft px-1.5 py-0.5 text-[10.5px] font-semibold text-oracle">REFUSED</span></td>
                <td className="py-2" colSpan={2}><span className="text-ink-2">everything else</span> <span className="text-ink-3">— {safety?.everything_else}; only {safety?.binary} may connect</span></td></tr>
            </tbody>
          </table>
          <div className="mt-3 text-[11.5px] text-ink-3">Measured from inside a sandbox by <span className="font-mono">scripts/safety_probe.sh</span>: 7 of 7.</div>
        </section>
        <section className="rounded-2xl border border-line bg-panel p-5">
          <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">Oracle AI Database</h3>
          <div className="space-y-2">
            {db.map(([t, how, proof]) => (
              <div key={t} className="rounded-lg bg-sand/60 px-3 py-2">
                <div className="text-[12.5px] font-semibold text-ink">{t}</div>
                <div className="text-[12px] text-ink-3">{how}</div>
                <div className="mt-0.5 font-mono text-[10.5px] text-moss">{proof}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 text-[11.5px] text-ink-3"><span className="font-mono">scripts/verify.py --rls-only</span>: 25 of 25.</div>
        </section>
        <section className="rounded-2xl border border-oracle/25 bg-panel p-5 xl:col-span-2">
          <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-oracle">Care policies · which agent may propose, who may approve (DA_OWNER.care_policy)</h3>
          <table className="w-full text-[12.5px]">
            <tbody>
              {policies.map((p) => (
                <tr key={p.code} className="border-b border-line/60 last:border-0">
                  <td className="py-2 pr-3 font-mono text-[11.5px] font-semibold text-ink">{p.code}</td>
                  <td className="py-2 pr-3 font-mono text-[11.5px] text-ink-2">{p.kind}</td>
                  <td className="py-2 pr-3 font-mono text-[11px] text-ink-3">{p.allowed_proposer === "any" ? "any agent" : `${p.allowed_proposer} only`}</td>
                  <td className="py-2 pr-3"><span className={p.required_role === "physician" ? "rounded bg-oracle-soft px-1.5 py-0.5 text-[10.5px] font-semibold text-oracle" : "rounded bg-teal-soft px-1.5 py-0.5 text-[10.5px] font-semibold text-teal"}>{p.required_role}</span></td>
                  <td className="py-2 text-ink-3">{p.rule}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-2 text-[11.5px] text-ink-3">Enforced in the database: the proposal trigger refuses the care coordinator's medication change (CP-03, ORA-20014) so it escalates to the medication-safety agent; DECIDE_CARE_ACTION refuses a clinician on a CP-02 action (ORA-20012); only the doctor's approval executes it.</div>
        </section>
        <section className="rounded-2xl border border-line bg-panel p-5">
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">Input guard</h3>
          <p className="text-[12.5px] text-ink-2">LangChain <span className="font-mono">PIIMiddleware</span> blocks SSN, phone, email, MRN and date-of-birth shapes and any other patient's id before the model sees them, and redacts the same shapes from model output.</p>
        </section>
        <section className="rounded-2xl border border-line bg-panel p-5">
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">Brief gate</h3>
          <p className="text-[12.5px] text-ink-2">The runner renders the structured <span className="font-mono">PreVisitBrief</span> and accepts it only with every section, enough citations of every kind, and every cited id found in the database as the patient's own user. Otherwise the draft goes back to the lead, twice at most.</p>
        </section>
      </div>
    </div>
  );
}
