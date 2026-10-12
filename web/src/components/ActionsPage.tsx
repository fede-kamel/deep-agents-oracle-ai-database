import clsx from "clsx";
import { CalendarPlus, Check, ClipboardCheck, FlaskConical, MessageSquareText, Pill, Stethoscope, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Citations, Cited } from "./cite";
import { Panel } from "./Panel";
import { PolicyChain } from "./PolicyChain";
import { Badge, Button, Empty, Label, NextLink, PageHeader } from "./ui";

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
  lab_request: { label: "Lab request", icon: FlaskConical, color: "#2c5967", soft: "#e6eff1" },
  patient_message: { label: "Message to the patient", icon: MessageSquareText, color: "#6b4fa0", soft: "#f0ecf7" },
  follow_up: { label: "Follow-up visit", icon: CalendarPlus, color: "#a8701a", soft: "#fbf3e2" },
  medication_change: { label: "Medication change", icon: Pill, color: "#c74634", soft: "#fbeae7" },
} as const;

const open = (s: CareAction["status"]) => s === "proposed" || s === "needs_physician";

function Status({ a }: { a: CareAction }) {
  if (a.status === "proposed") return <Badge tone="warn">Awaiting the clinician</Badge>;
  if (a.status === "needs_physician") return <Badge tone="bad">Awaiting the doctor</Badge>;
  if (a.status === "approved") return <Badge tone="ok">Approved</Badge>;
  if (a.status === "executed") return <Badge tone="ok"><Check className="size-3" /> Executed</Badge>;
  return <Badge>Rejected</Badge>;
}

function Payload({ a, draft, setDraft }: { a: CareAction; draft: Record<string, unknown>; setDraft: (d: Record<string, unknown>) => void }) {
  const editable = a.status === "proposed";
  if (a.kind === "lab_request") {
    const tests = (draft.tests as string[]) ?? [];
    return (
      <div className="space-y-1.5 text-sm">
        <div className="flex flex-wrap gap-1.5">{tests.map((t) => <span key={t} className="rounded-md border border-teal/25 bg-teal-soft px-2 py-0.5 font-medium text-teal">{t}</span>)}</div>
        <div className="text-ink-3">urgency <span className="font-medium text-ink">{String(draft.urgency ?? "routine")}</span> · before <span className="font-medium text-ink">{draft.before_visit ? "the visit" : "—"}</span></div>
      </div>
    );
  }
  if (a.kind === "patient_message") {
    return (
      <div className="rounded-md border border-line bg-sand/50 p-3">
        <div className="text-xs text-ink-3">Patient portal · to {String(draft.to ?? "the patient")}{editable && " · you may edit before approving"}</div>
        {editable ? (
          <>
            <input value={String(draft.subject ?? "")} onChange={(e) => setDraft({ ...draft, subject: e.target.value })}
              className="mt-1.5 w-full rounded-md border border-line bg-panel px-2 py-1 text-base font-semibold outline-none focus:border-ink-3/60" />
            <textarea value={String(draft.body ?? "")} onChange={(e) => setDraft({ ...draft, body: e.target.value })} rows={6}
              className="mt-1.5 w-full resize-y rounded-md border border-line bg-panel px-2 py-1.5 text-sm outline-none focus:border-ink-3/60" />
          </>
        ) : (
          <>
            <div className="mt-1 text-base font-semibold">{String(draft.subject ?? "")}</div>
            <p className="mt-1 whitespace-pre-wrap text-sm text-ink-2">{String(draft.body ?? "")}</p>
          </>
        )}
      </div>
    );
  }
  if (a.kind === "medication_change") {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span className="rounded-md border border-oracle/30 bg-oracle-soft px-2 py-0.5 font-semibold uppercase tracking-wide text-oracle">{String(draft.change ?? "")}</span>
        <span className="font-medium text-ink">{String(draft.medication ?? "")}</span>
      </div>
    );
  }
  return (
    <div className="text-sm text-ink-3">
      <span className="font-medium text-ink">{String(draft.visit_type ?? "Follow-up visit")}</span> within <span className="font-medium text-ink">{String(draft.within_days ?? "?")} days</span>
    </div>
  );
}

type Decide = (id: number, decision: "approve" | "reject", role: "clinician" | "physician", payload?: Record<string, unknown>) => void;

function ActionCard({ a, onDecide, busy, locked, refusal }: { a: CareAction; onDecide: Decide; busy: boolean; locked: boolean; refusal?: string }) {
  const meta = KIND[a.kind];
  const Icon = meta.icon;
  const [draft, setDraft] = useState(a.payload); // the card is keyed by id and status, so a decided card starts afresh
  const doctor = a.status === "needs_physician";
  return (
    <article data-card="action" className={clsx("rounded-lg border bg-panel p-4", doctor ? "border-oracle/40" : a.status === "proposed" ? "border-warn/40" : "border-line")}>
      <div className="flex items-start gap-3">
        <span className="grid size-8 shrink-0 place-items-center rounded-md" style={{ background: meta.soft, color: meta.color }}><Icon className="size-4" /></span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2"><Label>{meta.label}</Label><Status a={a} /></div>
          <h3 className="mt-0.5 text-base font-semibold">{a.title}</h3>
          <div className="text-xs text-ink-3">
            proposed by the {a.proposed_agent ?? a.proposed_by} agent
            {a.escalation_id ? ` on escalation #${a.escalation_id}` : ""}{a.policy_code ? ` · policy ${a.policy_code}` : ""}
          </div>
        </div>
      </div>
      {doctor && (
        <div className="mt-3 rounded-md bg-oracle-soft px-3 py-2 text-sm text-oracle">
          <span className="font-semibold">Waiting for a doctor (policy {a.policy_code}).</span> No agent and no clinician can approve a medication change; the database refuses them.
        </div>
      )}
      <p className="mt-3 text-sm text-ink-2"><Cited text={a.rationale} /></p>
      <Citations text={a.citations} except={a.rationale} className="mt-1.5" />
      <div className="mt-3"><Payload a={a} draft={draft} setDraft={setDraft} /></div>
      {refusal && <div className="mt-3 rounded-md bg-oracle-soft px-3 py-2 text-sm text-oracle"><span className="font-semibold">Refused by the database:</span> {refusal}</div>}
      {a.result && <div className="mt-3 rounded-md bg-ok-soft px-3 py-2 text-sm text-ok"><span className="font-semibold">Executed by the database:</span> {a.result.summary}</div>}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
        <span className="text-xs text-ink-3">{a.events.map((e) => `${e.status} by ${e.actor} ${e.at.slice(11, 19)}`).join("  ·  ")}</span>
        {open(a.status) && (
          <div className="ml-auto flex gap-1.5">
            <Button disabled={locked} onClick={() => onDecide(a.id, "reject", doctor ? "physician" : "clinician")}><X className="size-3.5" /> Reject</Button>
            <Button variant={doctor ? "quiet" : "primary"} disabled={locked} busy={busy} onClick={() => onDecide(a.id, "approve", "clinician", draft)}>
              {!busy && <Check className="size-3.5" />} Approve as clinician
            </Button>
            {doctor && (
              <Button variant="accent" disabled={locked} onClick={() => onDecide(a.id, "approve", "physician", draft)}><Stethoscope className="size-3.5" /> Approve as doctor</Button>
            )}
          </div>
        )}
      </div>
    </article>
  );
}

/** The proposals: the agents propose, you decide, the database executes and audits. */
export function ActionsPage({ patientKey, refreshKey, onDecided, onLoaded, onMemory }: {
  patientKey: string; refreshKey: unknown; onDecided?: () => void; onLoaded?: (actions: CareAction[]) => void; onMemory: () => void;
}) {
  const [actions, setActions] = useState<CareAction[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const [refusals, setRefusals] = useState<Record<number, string>>({});
  const load = useCallback(() => {
    fetch(`/api/patients/${patientKey}/actions`).then((r) => (r.ok ? r.json() : [])).then((a: CareAction[]) => {
      setActions(a);
      onLoaded?.(a);
      // A refusal belongs to a card still awaiting a decision; drop it once decided.
      setRefusals((m) => Object.fromEntries(Object.entries(m).filter(([id]) => a.some((x) => x.id === Number(id) && open(x.status)))));
    }).catch(() => setActions([]));
  }, [patientKey, onLoaded]);
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

  const pending = actions.filter((a) => open(a.status)).length;
  const doctor = actions.filter((a) => a.status === "needs_physician").length;
  const decided = actions.length - pending;
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <PageHeader title="Proposed actions" subtitle={`${pending} awaiting a decision${doctor ? ` · ${doctor} ${doctor === 1 ? "needs" : "need"} a doctor` : ""} · ${decided} decided`}>
        <NextLink onClick={onMemory}>What the agent will remember</NextLink>
      </PageHeader>
      <Panel title={<><ClipboardCheck className="size-3.5 text-ink-3" /> Actions</>} meta="the agents only propose; you decide; the database executes and audits every step" className="min-h-0 flex-1" bodyClassName="scroll-thin overflow-y-auto bg-paper p-4">
        <div className="mx-auto max-w-[980px] space-y-3">
          <PolicyChain patientKey={patientKey} actions={actions} refreshKey={refreshKey} />
          {actions.length === 0 && <Empty>No proposals yet. Run a brief: the care coordinator drafts lab requests, a patient message and a follow-up, and escalates a medication concern to the medication-safety agent.</Empty>}
          {actions.map((a) => <ActionCard key={`${a.id}:${a.status}`} a={a} onDecide={decide} busy={busy === a.id} locked={busy !== null} refusal={refusals[a.id]} />)}
        </div>
      </Panel>
    </div>
  );
}
