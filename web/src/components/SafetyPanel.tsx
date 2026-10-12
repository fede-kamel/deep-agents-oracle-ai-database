import clsx from "clsx";
import { ShieldCheck, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import type { Safety } from "../api";
import { Label } from "./ui";

type Policy = { code: string; kind: string; required_role: string; allowed_proposer: string; rule: string };

const DB: [string, string, string][] = [
  ["Agent user reads one patient", "row-level security (VPD) on every chart table and the note vectors", "verify.py: 0 rows of another patient"],
  ["Agent user proposes, never acts", "INSERT on care_action only; a trigger forces 'proposed'; update_check refuses other patients", "ORA-28115 · ORA-41900 · ORA-06550"],
  ["Policy names the agent, too", "each tool stamps its session with the agent's name; CP-03 refuses a medication change from any agent but medication-safety", "ORA-20014 · logged in policy_event"],
  ["Clinician approves, database executes", "DA_CLINICIAN holds EXECUTE on DECIDE_CARE_ACTION; every step is audited", "proposed > approved > executed"],
  ["Synthetic only", "CHECK is_synthetic = 'Y'; ids must start with SYN-", "ORA-02290"],
  ["Agent state in its own schema", "OracleSaver checkpoints, OracleStore memory; 64 MB quota", "memory read-only to the agent"],
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-line bg-panel p-4">
      <Label className="mb-3">{title}</Label>
      {children}
    </section>
  );
}

/** What keeps the agent in bounds, layer by layer, each one measured. */
export function SafetySheet({ safety, onClose }: { safety?: Safety; onClose: () => void }) {
  const [policies, setPolicies] = useState<Policy[]>([]);
  useEffect(() => { fetch("/api/policies").then((r) => r.json()).then(setPolicies).catch(() => undefined); }, []);
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-ink/20" onClick={onClose}>
      <aside className="flex h-full w-[min(860px,100vw)] flex-col border-l border-line bg-paper shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <header className="flex h-[52px] shrink-0 items-center gap-3 border-b border-line bg-panel px-5">
          <ShieldCheck className="size-4 text-ok" />
          <span className="text-sm font-semibold">Safety</span>
          <span className="text-xs text-ink-3">Four layers, each measured; none asks the agent to behave. Esc to close.</span>
          <button onClick={onClose} className="ml-auto rounded-md p-1 text-ink-3 hover:bg-sand hover:text-ink"><X className="size-4" /></button>
        </header>
        <div className="scroll-thin min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
          <p className="text-sm text-ink-2">The sandbox decides what the agent can reach, the database decides what it can read and write, the guards decide what it can be asked, and the gate decides what it can say.</p>

          <Section title="NVIDIA OpenShell sandbox · network">
            <table className="w-full text-sm">
              <tbody>
                {(safety?.egress ?? []).map((e) => (
                  <tr key={e.rule} className="border-b border-line/60 align-top last:border-0">
                    <td className="py-2 pr-3"><span className="rounded bg-ok-soft px-1.5 py-0.5 text-xs font-semibold text-ok">ALLOWED</span></td>
                    <td className="py-2 pr-3"><div className="font-mono text-xs text-ink">{e.target}</div><div className="text-ink-3">{e.allow}</div></td>
                    <td className="py-2 text-ink-3">{e.credential}</td>
                  </tr>
                ))}
                <tr>
                  <td className="py-2 pr-3"><span className="rounded bg-oracle-soft px-1.5 py-0.5 text-xs font-semibold text-oracle">REFUSED</span></td>
                  <td className="py-2" colSpan={2}><span className="text-ink-2">everything else</span> <span className="text-ink-3">· {safety?.everything_else}; only {safety?.binary} may connect</span></td>
                </tr>
              </tbody>
            </table>
            <div className="mt-3 text-xs text-ink-3">Measured from inside a sandbox by <span className="font-mono">scripts/safety_probe.sh</span>: 7 of 7. Image <span className="font-mono">{safety?.sandbox_image}</span>, provider <span className="font-mono">{safety?.provider}</span>.</div>
          </Section>

          <Section title="Oracle AI Database">
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {DB.map(([t, how, proof]) => (
                <div key={t} className="rounded-md bg-sand/60 px-3 py-2">
                  <div className="text-sm font-semibold text-ink">{t}</div>
                  <div className="text-sm text-ink-3">{how}</div>
                  <div className="mt-0.5 font-mono text-xs text-ok">{proof}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs text-ink-3"><span className="font-mono">scripts/verify.py --rls-only</span>: 25 of 25.</div>
          </Section>

          <Section title="Care policies · which agent may propose, who may approve">
            <table className="w-full text-sm">
              <tbody>
                {policies.map((p) => (
                  <tr key={p.code} className="border-b border-line/60 align-top last:border-0">
                    <td className="py-2 pr-3 font-mono text-xs font-semibold text-ink">{p.code}</td>
                    <td className="py-2 pr-3 font-mono text-xs text-ink-2">{p.kind}</td>
                    <td className="py-2 pr-3 font-mono text-xs text-ink-3">{p.allowed_proposer === "any" ? "any agent" : `${p.allowed_proposer} only`}</td>
                    <td className="py-2 pr-3"><span className={clsx("rounded px-1.5 py-0.5 text-xs font-semibold", p.required_role === "physician" ? "bg-oracle-soft text-oracle" : "bg-teal-soft text-teal")}>{p.required_role}</span></td>
                    <td className="py-2 text-ink-3">{p.rule}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-3 text-xs text-ink-3">Enforced in the database: the proposal trigger refuses the care coordinator's medication change (CP-03, ORA-20014), so it escalates to the medication-safety agent; DECIDE_CARE_ACTION refuses a clinician on a CP-02 action (ORA-20012); only the doctor's approval executes it.</div>
          </Section>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Section title="Input guard">
              <p className="text-sm text-ink-2">LangChain <span className="font-mono text-xs">PIIMiddleware</span> blocks SSN, phone, email, MRN and date-of-birth shapes and any other patient's id before the model sees them, and redacts the same shapes from model output.</p>
            </Section>
            <Section title="Brief gate">
              <p className="text-sm text-ink-2">The runner renders the structured <span className="font-mono text-xs">PreVisitBrief</span> and accepts it only with every section, enough citations of every kind, and every cited id found in the database as the patient's own user. Otherwise the draft goes back to the lead, twice at most.</p>
            </Section>
          </div>

          <div className="text-xs text-ink-3">Models: {safety?.chat_model} (lead), {safety?.worker_model} (specialists), through OCI Generative AI.</div>
        </div>
      </aside>
    </div>
  );
}
