import clsx from "clsx";
import { ArrowRight, Ban, ShieldAlert, Stethoscope, UserRoundCheck } from "lucide-react";
import { useEffect, useState } from "react";
import type { CareAction } from "./ActionsPage";
import { Label } from "./ui";

type Escalation = {
  id: number; run_id: string; from_agent: string; to_agent: string; policy_code: string;
  subject: string; reason: string; status: "open" | "accepted" | "declined"; resolution?: string | null;
  action_id?: number | null; created_at: string;
};
type PolicyEvent = { id: number; run_id: string; agent: string; policy_code: string; decision: string; detail: string; at: string };

function Step({ tone, icon: Icon, who, what }: { tone: "bad" | "warn" | "ink" | "ok"; icon: typeof Ban; who: string; what: string }) {
  return (
    <div className={clsx("min-w-0 flex-1 rounded-md border px-3 py-2",
      tone === "bad" ? "border-oracle/30 bg-oracle-soft" : tone === "warn" ? "border-warn/30 bg-warn-soft" : tone === "ok" ? "border-ok/30 bg-ok-soft" : "border-line bg-sand/60")}>
      <div className={clsx("flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide",
        tone === "bad" ? "text-oracle" : tone === "warn" ? "text-warn" : tone === "ok" ? "text-ok" : "text-ink-2")}>
        <Icon className="size-3.5" />{who}
      </div>
      <div className="mt-0.5 text-sm text-ink-2">{what}</div>
    </div>
  );
}

/** One escalation, end to end: the agent the database refused, the agent it
 * escalated to, and who decides now. Read from policy_event,
 * agent_escalation and care_action. */
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
  const doctor = action?.status === "executed" ? "Approved by the doctor; the database executed it."
    : action?.status === "rejected" ? "Rejected." : action ? "Waiting: only the doctor can approve (CP-02)." : "No change proposed.";
  return (
    <section className="rounded-lg border border-line bg-panel p-4">
      <Label className="mb-3">Policy in action · escalation #{latest.id} · {latest.subject}</Label>
      <div className="flex items-stretch gap-1.5">
        <Step tone="bad" icon={Ban} who={`${latest.from_agent} · refused`}
          what={refusal ? `Tried to propose the change. Database policy ${refusal.policy_code} refused it.` : "Escalated the concern."} />
        <ArrowRight className="size-4 shrink-0 self-center text-ink-3" />
        <Step tone="warn" icon={ShieldAlert} who="escalate_to_agent" what={`Handed to the ${latest.to_agent} agent with the cited reason.`} />
        <ArrowRight className="size-4 shrink-0 self-center text-ink-3" />
        <Step tone="ink" icon={UserRoundCheck} who={`${latest.to_agent} · ${latest.status}`}
          what={latest.status === "accepted" ? `Reviewed the chart and proposed action #${latest.action_id}.` : latest.status === "declined" ? "Reviewed and declined: no change supported." : "Reviewing."} />
        <ArrowRight className="size-4 shrink-0 self-center text-ink-3" />
        <Step tone={action?.status === "executed" ? "ok" : "ink"} icon={Stethoscope} who="doctor" what={doctor} />
      </div>
    </section>
  );
}
