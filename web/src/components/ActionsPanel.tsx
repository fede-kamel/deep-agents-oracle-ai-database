import clsx from "clsx";
import { CalendarPlus, Check, CircleCheck, FlaskConical, Loader2, MessageSquareText, Pill, ShieldAlert, ShieldCheck, Stethoscope, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { PolicyChain } from "./PolicyChain";

export type CareAction = {
  id: number;
  kind: "lab_request" | "patient_message" | "follow_up" | "medication_change";
  status: "proposed" | "needs_physician" | "approved" | "executed" | "rejected";
  policy_code?: string | null;
  required_role?: "clinician" | "physician" | null;
  proposed_agent?: string | null;
  escalation_id?: number | null;
  title: string;
  rationale: string;
  citations: string;
  payload: Record<string, unknown>;
  proposed_by: string;
  created_at: string;
  events: { status: string; actor: string; at: string; note?: string | null }[];
  result?: { table: string; id: number; summary: string } | null;
};

const KIND = {
  lab_request: { label: "Lab request", icon: FlaskConical, tone: "text-teal bg-teal-soft" },
  patient_message: { label: "Message to the patient", icon: MessageSquareText, tone: "text-violet bg-violet-soft" },
  follow_up: { label: "Follow-up visit", icon: CalendarPlus, tone: "text-oracle bg-oracle-soft" },
  medication_change: { label: "Medication change", icon: Pill, tone: "text-oracle bg-oracle-soft" },
} as const;
const STEPS = ["proposed", "approved", "executed"] as const;
const DOCTOR_STEPS = ["proposed", "needs doctor", "approved", "executed"] as const;

function Stepper({ a }: { a: CareAction }) {
  if (a.status === "rejected")
    return <span className="rounded-full bg-sand px-2.5 py-0.5 text-[11px] font-semibold text-ink-3">rejected</span>;
  const doctor = a.required_role === "physician";
  const steps: readonly string[] = doctor ? DOCTOR_STEPS : STEPS;
  const at = steps.indexOf(a.status === "needs_physician" ? "needs doctor" : a.status);
  return (
    <div className="flex items-center gap-1.5">
      {steps.map((s, i) => (
        <div key={s} className="flex items-center gap-1.5">
          <span className={clsx("flex items-center gap-1 rounded-full px-2 py-0.5 text-[10.5px] font-semibold",
            i < at || (i === at && s === "executed") ? "bg-moss-soft text-moss" : i === at ? "bg-ochre-soft text-ochre" : "bg-sand text-ink-3")}>
            {i < at || (i === at && s === "executed") ? <Check className="size-3" /> : null}{s}
          </span>
          {i < steps.length - 1 && <span className="h-px w-4 bg-line" />}
        </div>
      ))}
    </div>
  );
}

function Payload({ a, draft, setDraft }: { a: CareAction; draft: Record<string, unknown>; setDraft: (d: Record<string, unknown>) => void }) {
  const editable = a.status === "proposed";
  if (a.kind === "lab_request") {
    const tests = (draft.tests as string[]) ?? [];
    return (
      <div className="space-y-1.5 text-[12.5px]">
        <div className="flex flex-wrap gap-1.5">
          {tests.map((t) => <span key={t} className="rounded-md border border-teal/25 bg-teal-soft px-2 py-0.5 font-medium text-teal">{t}</span>)}
        </div>
        <div className="text-ink-3">urgency: <span className="font-medium text-ink">{String(draft.urgency ?? "routine")}</span> · before: <span className="font-medium text-ink">{String(draft.before_visit ? "the visit" : "—")}</span></div>
      </div>
    );
  }
  if (a.kind === "patient_message") {
    return (
      <div className="rounded-xl border border-violet/20 bg-violet-soft/40 p-3">
        <div className="text-[11px] text-ink-3">Patient portal · to {String(draft.to ?? "the patient")}</div>
        {editable ? (
          <>
            <input value={String(draft.subject ?? "")} onChange={(e) => setDraft({ ...draft, subject: e.target.value })}
              className="mt-1 w-full rounded-md border border-line bg-panel px-2 py-1 text-[13px] font-semibold outline-none" />
            <textarea value={String(draft.body ?? "")} onChange={(e) => setDraft({ ...draft, body: e.target.value })} rows={5}
              className="mt-1.5 w-full resize-y rounded-md border border-line bg-panel px-2 py-1.5 text-[12.5px] leading-relaxed outline-none" />
          </>
        ) : (
          <>
            <div className="mt-1 text-[13px] font-semibold">{String(draft.subject ?? "")}</div>
            <p className="mt-1 whitespace-pre-wrap text-[12.5px] leading-relaxed text-ink-2">{String(draft.body ?? "")}</p>
          </>
        )}
      </div>
    );
  }
  if (a.kind === "medication_change") {
    return (
      <div className="flex items-center gap-2 text-[12.5px]">
        <span className="rounded-md border border-oracle/30 bg-oracle-soft px-2 py-0.5 font-semibold uppercase tracking-wide text-oracle">{String(draft.change ?? "")}</span>
        <span className="font-medium text-ink">{String(draft.medication ?? "")}</span>
      </div>
    );
  }
  return (
    <div className="text-[12.5px] text-ink-3">
      <span className="font-medium text-ink">{String(draft.visit_type ?? "Follow-up visit")}</span> within{" "}
      <span className="font-medium text-ink">{String(draft.within_days ?? "?")} days</span>
    </div>
  );
}

type Decide = (id: number, decision: "approve" | "reject", role: "clinician" | "physician", payload?: Record<string, unknown>) => void;

function ActionCard({ a, onDecide, busy, locked, refusal }: { a: CareAction; onDecide: Decide; busy: boolean; locked: boolean; refusal?: string }) {
  const meta = KIND[a.kind];
  const Icon = meta.icon;
  const [draft, setDraft] = useState(a.payload);
  useEffect(() => setDraft(a.payload), [a.payload]);
  return (
    <div className={clsx("rounded-xl border bg-panel p-4", a.status === "needs_physician" ? "border-oracle/50 ring-1 ring-oracle/20" : a.status === "proposed" ? "border-ochre/40" : "border-line")}>
      {a.status === "needs_physician" && (
        <div className="-mx-4 -mt-4 mb-3 flex items-center gap-2 rounded-t-xl border-b border-oracle/25 bg-oracle-soft px-4 py-2 text-[12px] text-oracle">
          <ShieldAlert className="size-4 shrink-0" />
          <span><b>Waiting for a doctor (policy {a.policy_code}).</b>{" "}
            {a.escalation_id ? `Proposed by the ${a.proposed_agent} agent on escalation #${a.escalation_id}. ` : ""}No agent and no clinician can approve a medication change.</span>
        </div>
      )}
      <div className="flex items-start gap-3">
        <div className={clsx("grid size-9 shrink-0 place-items-center rounded-lg", meta.tone)}><Icon className="size-4" /></div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-ink-3">{meta.label}</span>
            <Stepper a={a} />
          </div>
          <div className="mt-0.5 text-[14px] font-semibold">{a.title}</div>
          {a.proposed_agent && <div className="text-[10.5px] text-ink-3">proposed by the {a.proposed_agent} agent</div>}
          <p className="mt-1 text-[12.5px] leading-snug text-ink-3">{a.rationale} <span className="font-mono text-[10.5px]">{a.citations}</span></p>
        </div>
      </div>
      <div className="mt-3"><Payload a={a} draft={draft} setDraft={setDraft} /></div>
      {refusal && (
        <div className="mt-3 flex items-center gap-1.5 rounded-lg border border-oracle/30 bg-oracle-soft px-3 py-2 text-[12px] text-oracle">
          <ShieldAlert className="size-3.5 shrink-0" /> Refused by the database: {refusal}
        </div>
      )}
      {a.result && (
        <div className="mt-3 flex items-center gap-1.5 rounded-lg bg-moss-soft px-3 py-2 text-[12px] text-moss">
          <CircleCheck className="size-3.5" /> executed by the database: {a.result.summary}
        </div>
      )}
      <div className="mt-3 flex items-center gap-2 border-t border-line/70 pt-2.5">
        <span className="text-[10.5px] text-ink-3">
          {a.events.map((e) => `${e.status} by ${e.actor} ${e.at.slice(11, 19)}`).join("  ·  ")}
        </span>
        {(a.status === "proposed" || a.status === "needs_physician") && (
          <div className="ml-auto flex gap-1.5">
            <button disabled={locked} onClick={() => onDecide(a.id, "reject", a.status === "needs_physician" ? "physician" : "clinician")} className="flex items-center gap-1 rounded-md border border-line px-2.5 py-1 text-[12px] text-ink-2 hover:border-oracle/50 hover:text-oracle">
              <X className="size-3.5" /> Reject
            </button>
            <button disabled={locked} onClick={() => onDecide(a.id, "approve", "clinician", draft)}
              className={clsx("flex items-center gap-1 rounded-md px-3 py-1 text-[12px] font-semibold",
                a.status === "needs_physician" ? "border border-line text-ink-3 hover:border-oracle/40" : "bg-moss text-white hover:bg-[#4f6a41]")}>
              {busy ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />} Approve as clinician
            </button>
            {a.status === "needs_physician" && (
              <button disabled={locked} onClick={() => onDecide(a.id, "approve", "physician", draft)} className="flex items-center gap-1 rounded-md bg-oracle px-3 py-1 text-[12px] font-semibold text-white hover:bg-[#b23d2d]">
                <Stethoscope className="size-3.5" /> Approve as doctor
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function ActionsPanel({ patientKey, refreshKey, onDecided, onLoaded }: {
  patientKey: string; refreshKey: unknown; onDecided?: () => void; onLoaded?: (actions: CareAction[]) => void;
}) {
  const [actions, setActions] = useState<CareAction[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const [refusals, setRefusals] = useState<Record<number, string>>({});
  const shown = useRef(patientKey);
  shown.current = patientKey;
  const load = useCallback(() => {
    const key = patientKey; // drop an answer that arrives after the patient changed
    fetch(`/api/patients/${key}/actions`).then((r) => (r.ok ? r.json() : [])).then((a: CareAction[]) => {
      if (shown.current !== key) return;
      setActions(a);
      onLoaded?.(a); // the step counts come from the same list the cards show
      // A refusal belongs to a card still awaiting a decision; drop it once decided.
      setRefusals((m) => Object.fromEntries(Object.entries(m).filter(([id]) => a.some((x) => x.id === Number(id) && (x.status === "proposed" || x.status === "needs_physician")))));
    })
      .catch(() => shown.current === key && setActions([]));
  }, [patientKey, onLoaded]);
  useEffect(() => { setActions([]); setRefusals({}); }, [patientKey]);
  useEffect(load, [load, refreshKey]);

  const decide: Decide = async (id, decision, role, payload) => {
    if (busy !== null) return; // one decision at a time; the list reloads in between
    setBusy(id);
    const r = await fetch(`/api/actions/${id}/${decision}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ payload, role }) });
    if (!r.ok) {
      const body = await r.json().catch(() => ({ detail: r.statusText }));
      setRefusals((m) => ({ ...m, [id]: String(body.detail ?? "").replace(/^ORA-\d+: /, "") }));
    } else {
      setRefusals((m) => { const n = { ...m }; delete n[id]; return n; });
    }
    setBusy(null);
    load();
    onDecided?.();
  };

  const pending = actions.filter((a) => a.status === "proposed" || a.status === "needs_physician").length;
  const doctor = actions.filter((a) => a.status === "needs_physician").length;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-xl border border-moss/25 bg-moss-soft/50 px-4 py-2.5 text-[12px] text-ink-2">
        <ShieldCheck className="size-4 shrink-0 text-moss" />
        <span>The agent can only <b>propose</b>, and only for this patient. You approve as the clinician; the database executes, and every step is audited.</span>
        <span className="ml-auto shrink-0 whitespace-nowrap font-semibold text-ochre">{pending} awaiting a decision{doctor ? ` · ${doctor} need a doctor` : ""}</span>
      </div>
      <PolicyChain patientKey={patientKey} actions={actions} refreshKey={refreshKey} />
      {actions.length === 0 && <div className="rounded-xl border border-dashed border-line p-6 text-center text-[13px] text-ink-3">No proposals yet. Run a brief: the care coordinator drafts lab requests, a patient message and a follow-up, and escalates a medication concern to the medication-safety agent.</div>}
      {actions.map((a) => <ActionCard key={a.id} a={a} onDecide={decide} busy={busy === a.id} locked={busy !== null} refusal={refusals[a.id]} />)}
    </div>
  );
}
