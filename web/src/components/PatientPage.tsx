import clsx from "clsx";
import { AlertTriangle, Brain, CalendarClock, Play } from "lucide-react";
import { memo, useEffect, useState, type ReactNode } from "react";
import { getJSON, type Patient } from "../api";
import { Button, Label, NextLink, PageHeader } from "./ui";

type Chart = {
  medications: [string, string | null, string | null, string, string | null, string][];
  labs: Record<string, { date: string; value: number; unit: string }[]>;
  timeline: [string, string, string, string | null][];
  referrals: [string, string, string, string | null][];
  appointments: [string, string, string][];
  conditions: [string, string | null, string][];
};

const SETTING_TONE: Record<string, string> = {
  inpatient: "bg-oracle", emergency: "bg-oracle", "urgent care": "bg-warn", outpatient: "bg-teal",
  telephone: "bg-violet", portal: "bg-violet", pharmacy: "bg-moss", administrative: "bg-ink-3",
};

function Spark({ points }: { points: { date: string; value: number }[] }) {
  if (points.length < 2) return <div className="h-8" />;
  const vs = points.map((p) => p.value);
  const min = Math.min(...vs), max = Math.max(...vs);
  const span = max - min || 1;
  const w = 120, h = 32;
  const xy = points.map((p, i) => [(i / (points.length - 1)) * (w - 6) + 3, h - 4 - ((p.value - min) / span) * (h - 8)]);
  const stroke = vs[vs.length - 1] > vs[0] ? "#c74634" : "#2c5967";
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={xy.map((p) => p.join(",")).join(" ")} fill="none" stroke={stroke} strokeWidth="2" strokeLinejoin="round" />
      {xy.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={i === xy.length - 1 ? 3 : 1.8} fill={stroke} />)}
    </svg>
  );
}

function Card({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={clsx("rounded-lg border border-line bg-panel p-4", className)}>
      <Label className="mb-3">{title}</Label>
      {children}
    </section>
  );
}

/** The patient: ask the agents, read the situation, see the chart they will read. */
export const PatientPage = memo(function PatientPage({ patient, question, setQuestion, onRun, running, notice, active, onWatch, refresh, memoryEntries, onMemory }: {
  patient: Patient; question: string; setQuestion: (q: string) => void; onRun: () => void; running: boolean; notice?: string;
  active: { id: string; patient: string } | null; onWatch: () => void; refresh: number; memoryEntries: number; onMemory: () => void;
}) {
  const [chart, setChart] = useState<Chart>();
  useEffect(() => {
    let current = true;
    getJSON<Chart>(`/api/patients/${patient.key}/chart`).then((c) => current && setChart(c)).catch(() => undefined);
    return () => { current = false; };
  }, [patient.key, refresh]);

  return (
    <div className="space-y-4">
      <PageHeader title={patient.situation} subtitle={`${patient.alias.replace(" (synthetic)", "")} · ${patient.age} · ${patient.sex} · ${patient.visit_reason}`}>
        <span className="font-mono text-xs text-ink-3" title="The agents read this chart through the patient's own database user">{patient.id} · {patient.db_user}</span>
      </PageHeader>

      <section className="rounded-lg border border-line bg-panel p-4">
        <Label>Ask the agents</Label>
        <div className="mt-2 flex items-stretch gap-3">
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} disabled={running}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onRun(); } }}
            className="flex-1 resize-none rounded-md border border-line bg-paper px-3 py-2 text-base outline-none focus:border-ink-3/60 disabled:text-ink-3" />
          <Button variant="accent" onClick={onRun} disabled={running || !question.trim()} busy={running} className="h-auto shrink-0 px-5">
            {!running && <Play className="size-4" />}{running ? "Agents running" : "Run in sandbox"}
          </Button>
        </div>
        <div className="mt-1.5 flex items-center gap-3 text-xs text-ink-3">
          <span>Enter runs it · Shift+Enter for a new line · identifiers that look real, and other patients' ids, are blocked</span>
          {question !== patient.question && <button onClick={() => setQuestion(patient.question)} disabled={running} className="ml-auto hover:text-ink">Reset the question</button>}
        </div>
        {(notice || active) && (
          <div className="mt-3 flex items-center gap-3 rounded-md bg-warn-soft px-3 py-2 text-sm text-ink-2">
            <span>{notice ?? `A run for Patient ${active?.patient} is in progress in the sandbox.`}</span>
            {active && <Button variant="primary" onClick={onWatch} className="ml-auto h-7">Watch live</Button>}
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <Card title="Situation">
          <p className="text-base text-ink-2">{patient.narrative}</p>
          {chart && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {chart.conditions.map(([d, , st]) => (
                <span key={d} className={clsx("rounded-full border px-2.5 py-0.5 text-xs", st === "active" ? "border-teal/25 bg-teal-soft text-teal" : "border-line bg-sand text-ink-3")}>{d}</span>
              ))}
            </div>
          )}
        </Card>
        <Card title="Memory">
          <div className="flex items-start gap-2 text-sm text-ink-2">
            <Brain className="mt-0.5 size-4 shrink-0 text-teal" />
            {memoryEntries ? (
              <div>
                <div>{memoryEntries} {memoryEntries === 1 ? "entry" : "entries"} from earlier briefs and decisions, in OracleStore. The next brief starts from it.</div>
                <NextLink onClick={onMemory}>Read what it remembers</NextLink>
              </div>
            ) : (
              <div>Nothing yet. The first accepted brief, and every decision you take on its actions, are recorded here by the system.</div>
            )}
          </div>
        </Card>
      </div>

      {!chart ? (
        <div className="rounded-lg border border-line bg-panel p-6 text-sm text-ink-3">Reading the chart from Oracle AI Database…</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <Card title="Lab trends">
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(chart.labs).map(([test, pts]) => {
                const last = pts[pts.length - 1];
                return (
                  <div key={test} className="rounded-md bg-sand/70 p-3">
                    <div className="flex items-baseline justify-between">
                      <span className="text-sm font-semibold text-ink-2">{test}</span>
                      <span className="text-xs text-ink-3">{last.date}</span>
                    </div>
                    <div className="mt-1 flex items-end justify-between gap-2">
                      <span className="font-mono text-lg font-semibold">{last.value}<span className="ml-1 text-xs font-normal text-ink-3">{last.unit}</span></span>
                      <Spark points={pts} />
                    </div>
                    {pts.length > 1 && <div className="mt-1 font-mono text-xs text-ink-3">{pts.map((p) => p.value).join(" → ")}</div>}
                  </div>
                );
              })}
            </div>
          </Card>

          <Card title="What happened, in order">
            <ol className="relative space-y-2.5 border-l-2 border-line pl-4">
              {chart.timeline.map(([d, kind, setting, ref], i) => (
                <li key={i} className="relative">
                  <span className={clsx("absolute -left-[22px] top-1.5 size-2.5 rounded-full ring-2 ring-panel", SETTING_TONE[setting] ?? "bg-ink-3")} />
                  <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
                    <span className="font-mono text-xs text-ink-3">{d}</span>
                    <span className="font-medium text-ink">{kind}</span>
                    <span className="text-xs text-ink-3">{setting}</span>
                    {ref && <span className="rounded bg-ochre-soft px-1 font-mono text-[10px] text-ochre">{ref}</span>}
                  </div>
                </li>
              ))}
            </ol>
          </Card>

          <Card title={`Medications · ${chart.medications.filter((m) => m[5] === "active").length} active`}>
            <table className="w-full text-sm">
              <tbody>
                {chart.medications.map(([name, dose, freq, source, , status], i) => (
                  <tr key={i} className="border-b border-line/60 last:border-0">
                    <td className="py-1.5 pr-2 font-medium text-ink">{name}</td>
                    <td className="py-1.5 pr-2 text-ink-3">{[dose, freq].filter(Boolean).join(", ")}</td>
                    <td className="py-1.5 text-right">
                      {source !== "prescribed" && <span className="rounded bg-ochre-soft px-1.5 py-0.5 text-xs text-ochre">{source}</span>}
                      {status !== "active" && <span className="ml-1 rounded bg-sand px-1.5 py-0.5 text-xs text-ink-3">{status}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <Card title="Referrals and appointments">
            <div className="space-y-2">
              {chart.referrals.map(([kind, opened, status, detail], i) => (
                <div key={i} className="flex items-start gap-2 rounded-md bg-sand/70 px-3 py-2 text-sm">
                  <AlertTriangle className={clsx("mt-0.5 size-3.5 shrink-0", status === "open" || status === "requested" || status === "not scheduled" ? "text-warn" : "text-oracle")} />
                  <div>
                    <div className="font-medium text-ink">{kind} <span className="font-normal text-ink-3">· {status} since {opened}</span></div>
                    {detail && <div className="text-ink-3">{detail}</div>}
                  </div>
                </div>
              ))}
              {chart.appointments.map(([d, kind, status], i) => (
                <div key={i} className="flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm">
                  <CalendarClock className="size-3.5 text-teal" />
                  <span className="font-medium text-ink">{kind}</span>
                  <span className="text-ink-3">· {d} · {status}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
});
