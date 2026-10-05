import clsx from "clsx";
import { CalendarPlus, Check, CircleCheck, FlaskConical, Loader2, MessageSquareText, ShieldCheck, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

export type CareAction = {
  id: number;
  kind: "lab_request" | "patient_message" | "follow_up";
  status: "proposed" | "approved" | "executed" | "rejected";
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
} as const;
const STEPS = ["proposed", "approved", "executed"] as const;

function Stepper({ a }: { a: CareAction }) {
  if (a.status === "rejected")
    return <span className="rounded-full bg-sand px-2.5 py-0.5 text-[11px] font-semibold text-ink-3">rejected by the clinician</span>;
  const at = STEPS.indexOf(a.status as (typeof STEPS)[number]);
  return (
    <div className="flex items-center gap-1.5">
      {STEPS.map((s, i) => (
        <div key={s} className="flex items-center gap-1.5">
          <span className={clsx("flex items-center gap-1 rounded-full px-2 py-0.5 text-[10.5px] font-semibold",
            i < at || (i === at && s === "executed") ? "bg-moss-soft text-moss" : i === at ? "bg-ochre-soft text-ochre" : "bg-sand text-ink-3")}>
            {i < at || (i === at && s === "executed") ? <Check className="size-3" /> : null}{s}
          </span>
          {i < STEPS.length - 1 && <span className="h-px w-4 bg-line" />}
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
  return (
    <div className="text-[12.5px] text-ink-3">
      <span className="font-medium text-ink">{String(draft.visit_type ?? "Follow-up visit")}</span> within{" "}
      <span className="font-medium text-ink">{String(draft.within_days ?? "?")} days</span>
    </div>
  );
}

function ActionCard({ a, onDecide, busy }: { a: CareAction; onDecide: (id: number, decision: "approve" | "reject", payload?: Record<string, unknown>) => void; busy: boolean }) {
  const meta = KIND[a.kind];
  const Icon = meta.icon;
  const [draft, setDraft] = useState(a.payload);
  useEffect(() => setDraft(a.payload), [a.payload]);
  return (
    <div className={clsx("rounded-xl border bg-panel p-4", a.status === "proposed" ? "border-ochre/40" : "border-line")}>
      <div className="flex items-start gap-3">
        <div className={clsx("grid size-9 shrink-0 place-items-center rounded-lg", meta.tone)}><Icon className="size-4" /></div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-ink-3">{meta.label}</span>
            <Stepper a={a} />
          </div>
          <div className="mt-0.5 text-[14px] font-semibold">{a.title}</div>
          <p className="mt-1 text-[12.5px] leading-snug text-ink-3">{a.rationale} <span className="font-mono text-[10.5px]">{a.citations}</span></p>
        </div>
      </div>
      <div className="mt-3"><Payload a={a} draft={draft} setDraft={setDraft} /></div>
      {a.result && (
        <div className="mt-3 flex items-center gap-1.5 rounded-lg bg-moss-soft px-3 py-2 text-[12px] text-moss">
          <CircleCheck className="size-3.5" /> executed by the database: {a.result.summary}
        </div>
      )}
      <div className="mt-3 flex items-center gap-2 border-t border-line/70 pt-2.5">
        <span className="text-[10.5px] text-ink-3">
          {a.events.map((e) => `${e.status} by ${e.actor} ${e.at.slice(11, 19)}`).join("  ·  ")}
        </span>
        {a.status === "proposed" && (
          <div className="ml-auto flex gap-1.5">
            <button disabled={busy} onClick={() => onDecide(a.id, "reject")} className="flex items-center gap-1 rounded-md border border-line px-2.5 py-1 text-[12px] text-ink-2 hover:border-oracle/50 hover:text-oracle">
              <X className="size-3.5" /> Reject
            </button>
            <button disabled={busy} onClick={() => onDecide(a.id, "approve", draft)} className="flex items-center gap-1 rounded-md bg-moss px-3 py-1 text-[12px] font-semibold text-white hover:bg-[#4f6a41]">
              {busy ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />} Approve and execute
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export function ActionsPanel({ patientKey, refreshKey }: { patientKey: string; refreshKey: unknown }) {
  const [actions, setActions] = useState<CareAction[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const load = useCallback(() => {
    fetch(`/api/patients/${patientKey}/actions`).then((r) => (r.ok ? r.json() : [])).then(setActions).catch(() => setActions([]));
  }, [patientKey]);
  useEffect(load, [load, refreshKey]);

  const decide = async (id: number, decision: "approve" | "reject", payload?: Record<string, unknown>) => {
    setBusy(id);
    await fetch(`/api/actions/${id}/${decision}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ payload }) });
    setBusy(null);
    load();
  };

  const pending = actions.filter((a) => a.status === "proposed").length;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-xl border border-moss/25 bg-moss-soft/50 px-4 py-2.5 text-[12px] text-ink-2">
        <ShieldCheck className="size-4 shrink-0 text-moss" />
        <span>The agent can only <b>propose</b>, and only for this patient. You approve as the clinician; the database executes, and every step is audited.</span>
        <span className="ml-auto shrink-0 whitespace-nowrap font-semibold text-ochre">{pending} awaiting you</span>
      </div>
      {actions.length === 0 && <div className="rounded-xl border border-dashed border-line p-6 text-center text-[13px] text-ink-3">No proposals yet. Run a brief: the care coordinator drafts lab requests, a patient message, and a follow-up for you to review.</div>}
      {actions.map((a) => <ActionCard key={a.id} a={a} onDecide={decide} busy={busy === a.id} />)}
    </div>
  );
}
