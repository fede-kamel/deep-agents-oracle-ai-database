import clsx from "clsx";
import { ArrowRight, Ban, ShieldAlert, Stethoscope, UserRoundCheck } from "lucide-react";
import { useEffect, useState } from "react";
import type { CareAction } from "./ActionsPanel";

type Escalation = {
  id: number; run_id: string; from_agent: string; to_agent: string; policy_code: string;
  subject: string; reason: string; status: "open" | "accepted" | "declined"; resolution?: string | null;
  action_id?: number | null; created_at: string;
};
type PolicyEvent = { id: number; run_id: string; agent: string; policy_code: string; decision: string; detail: string; at: string };

function Step({ tone, icon: Icon, who, what }: { tone: string; icon: typeof Ban; who: string; what: string }) {
  return (
    <div className={clsx("min-w-0 flex-1 rounded-lg border px-3 py-2", tone)}>
      <div className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-wide"><Icon className="size-3.5" />{who}</div>
      <div className="mt-0.5 text-[12px] leading-snug text-ink-2">{what}</div>
    </div>
  );
}

/** One escalation, end to end: the agent the database refused, the agent it
 * escalated to, and who decides now. Everything shown is read from the
 * database (policy_event, agent_escalation, care_action). */
export function PolicyChain({ patientKey, actions, refreshKey }: { patientKey: string; actions: CareAction[]; refreshKey: unknown }) {
  const [log, setLog] = useState<{ escalations: Escalation[]; events: PolicyEvent[] }>({ escalations: [], events: [] });
  useEffect(() => {
    let current = true;
    fetch(`/api/patients/${patientKey}/policy`).then((r) => (r.ok ? r.json() : null)).then((d) => current && d && setLog(d)).catch(() => undefined);
    return () => { current = false; };
  }, [patientKey, refreshKey, actions]);
  const latest = log.escalations[0];
  if (!latest) return null;
  const refusal = log.events.find((e) => e.run_id === latest.run_id && e.decision === "refused");
  const action = actions.find((a) => a.id === latest.action_id);
  const doctor = action?.status === "executed" ? "approved by the doctor; the database executed it"
    : action?.status === "rejected" ? "rejected" : action ? "waiting: only the doctor can approve (CP-02)" : "no change proposed";
  return (
    <div className="rounded-xl border border-oracle/30 bg-panel p-3">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-ink-3">Policy in action · escalation #{latest.id} · {latest.subject}</div>
      <div className="flex items-stretch gap-1.5">
        <Step tone="border-oracle/30 bg-oracle-soft text-oracle" icon={Ban} who={`${latest.from_agent} · refused`}
          what={refusal ? `Tried to propose the change. Database policy ${refusal.policy_code} refused it.` : "Escalated the concern."} />
        <ArrowRight className="size-4 shrink-0 self-center text-ink-3" />
        <Step tone="border-ochre/30 bg-ochre-soft/50 text-ochre" icon={ShieldAlert} who="escalate_to_agent"
          what={`Handed to the ${latest.to_agent} agent with the cited reason.`} />
        <ArrowRight className="size-4 shrink-0 self-center text-ink-3" />
        <Step tone="border-teal/30 bg-teal-soft/50 text-teal" icon={UserRoundCheck} who={`${latest.to_agent} · ${latest.status}`}
          what={latest.status === "accepted" ? `Reviewed the chart and proposed action #${latest.action_id}.` : latest.status === "declined" ? "Reviewed and declined: no change supported." : "Reviewing."} />
        <ArrowRight className="size-4 shrink-0 self-center text-ink-3" />
        <Step tone={clsx(action?.status === "executed" ? "border-moss/30 bg-moss-soft/50 text-moss" : "border-line bg-sand/40 text-ink-2")} icon={Stethoscope}
          who="doctor" what={doctor} />
      </div>
    </div>
  );
}
