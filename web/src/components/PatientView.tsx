import clsx from "clsx";
import { AlertTriangle, Brain, CalendarClock, Database, HeartPulse, Pill, Route, Stethoscope } from "lucide-react";
import { memo, useEffect, useState } from "react";
import { getJSON, type Patient } from "../api";

type Chart = {
  medications: [string, string | null, string | null, string, string | null, string][];
  labs: Record<string, { date: string; value: number; unit: string }[]>;
  timeline: [string, string, string, string | null][];
  referrals: [string, string, string, string | null][];
  appointments: [string, string, string][];
  conditions: [string, string | null, string][];
};

const SETTING_TONE: Record<string, string> = {
  inpatient: "bg-oracle", emergency: "bg-oracle", "urgent care": "bg-ochre", outpatient: "bg-teal",
  telephone: "bg-violet", portal: "bg-violet", pharmacy: "bg-moss", administrative: "bg-ink-3",
};

function Spark({ points }: { points: { date: string; value: number }[] }) {
  if (points.length < 2) return <div className="h-8" />;
  const vs = points.map((p) => p.value);
  const min = Math.min(...vs), max = Math.max(...vs);
  const span = max - min || 1;
  const w = 120, h = 32;
  const xy = points.map((p, i) => [(i / (points.length - 1)) * (w - 6) + 3, h - 4 - ((p.value - min) / span) * (h - 8)]);
  const rising = vs[vs.length - 1] > vs[0];
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={xy.map((p) => p.join(",")).join(" ")} fill="none" stroke={rising ? "#c74634" : "#2c5967"} strokeWidth="2" strokeLinejoin="round" />
      {xy.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={i === xy.length - 1 ? 3 : 1.8} fill={rising ? "#c74634" : "#2c5967"} />)}
    </svg>
  );
}

export const PatientView = memo(function PatientView({ patient, refresh }: { patient: Patient; refresh: number }) {
  const [chart, setChart] = useState<Chart>();
  const [memory, setMemory] = useState<string>();
  useEffect(() => {
    let current = true; // a slow answer for the previous patient must not land here
    setChart(undefined);
    setMemory(undefined);
    getJSON<Chart>(`/api/patients/${patient.key}/chart`).then((c) => current && setChart(c)).catch(() => undefined);
    getJSON<{ text: string }>(`/api/patients/${patient.key}/memory`).then((m) => current && setMemory(m.text)).catch(() => current && setMemory(""));
    return () => { current = false; };
  }, [patient.key, refresh]);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-line bg-panel p-6">
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-oracle">
          {patient.display_name} · {patient.id}
          <span className="rounded bg-ink px-1.5 py-0.5 text-[9.5px] tracking-wider text-white">SYNTHETIC</span>
        </div>
        <h1 className="mt-1.5 text-[23px] font-semibold tracking-tight">{patient.situation}</h1>
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12.5px] text-ink-3">
          <span>{patient.alias.replace(" (synthetic)", "")} · {patient.age} · {patient.sex}</span>
          <span className="flex items-center gap-1"><Stethoscope className="size-3.5" /> {patient.visit_reason}</span>
          <span className="flex items-center gap-1 font-mono"><Database className="size-3.5" /> read as {patient.db_user}</span>
        </div>
        <p className="mt-4 max-w-[900px] text-[14.5px] leading-[1.7] text-ink-2">{patient.narrative}</p>
        {chart && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {chart.conditions.map(([d, , st]) => (
              <span key={d} className={clsx("rounded-full border px-2.5 py-1 text-[11.5px]", st === "active" ? "border-teal/25 bg-teal-soft text-teal" : "border-line bg-sand text-ink-3")}>{d}</span>
            ))}
          </div>
        )}
      </div>

      <section className="rounded-2xl border border-teal/25 bg-teal-soft/30 p-5">
        <h3 className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-teal">
          <Brain className="size-3.5" /> What the agent remembers <span className="font-mono normal-case tracking-normal text-ink-3">OracleStore · /memories/patient-history.md</span>
        </h3>
        {memory === undefined ? (
          <div className="text-[12.5px] text-ink-3">Reading memory…</div>
        ) : memory ? (
          <pre className="scroll-thin max-h-56 overflow-auto whitespace-pre-wrap font-sans text-[12.5px] leading-relaxed text-ink-2">{memory.replace(/^# .*\n\n.*\n/, "")}</pre>
        ) : (
          <div className="text-[12.5px] text-ink-3">Nothing yet. After the first accepted brief, the system records its findings here, and every clinician decision on a proposed action.</div>
        )}
      </section>

      {!chart ? (
        <div className="rounded-2xl border border-line bg-panel p-6 text-[13px] text-ink-3">Reading the chart from Oracle AI Database…</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.15fr_1fr]">
          <section className="rounded-2xl border border-line bg-panel p-5">
            <h3 className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3"><HeartPulse className="size-3.5" /> Lab trends</h3>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(chart.labs).map(([test, pts]) => {
                const last = pts[pts.length - 1];
                return (
                  <div key={test} className="rounded-xl bg-sand/60 p-3">
                    <div className="flex items-baseline justify-between">
                      <span className="text-[11.5px] font-semibold text-ink-2">{test}</span>
                      <span className="text-[10.5px] text-ink-3">{last.date}</span>
                    </div>
                    <div className="mt-1 flex items-end justify-between gap-2">
                      <span className="font-mono text-[19px] font-semibold">{last.value}<span className="ml-1 text-[10.5px] font-normal text-ink-3">{last.unit}</span></span>
                      <Spark points={pts} />
                    </div>
                    {pts.length > 1 && <div className="mt-1 font-mono text-[10.5px] text-ink-3">{pts.map((p) => p.value).join(" → ")}</div>}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-2xl border border-line bg-panel p-5">
            <h3 className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3"><Route className="size-3.5" /> What happened, in order</h3>
            <ol className="relative space-y-2.5 border-l-2 border-line pl-4">
              {chart.timeline.map(([d, kind, setting, ref], i) => (
                <li key={i} className="relative">
                  <span className={clsx("absolute -left-[22px] top-1 size-2.5 rounded-full ring-2 ring-panel", SETTING_TONE[setting] ?? "bg-ink-3")} />
                  <div className="flex flex-wrap items-baseline gap-x-2 text-[12.5px]">
                    <span className="font-mono text-[11px] text-ink-3">{d}</span>
                    <span className="font-medium text-ink">{kind}</span>
                    <span className="text-[11px] text-ink-3">{setting}</span>
                    {ref && <span className="rounded bg-ochre-soft px-1 font-mono text-[9.5px] text-ochre">{ref}</span>}
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section className="rounded-2xl border border-line bg-panel p-5">
            <h3 className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3"><Pill className="size-3.5" /> Medications ({chart.medications.filter((m) => m[5] === "active").length} active)</h3>
            <table className="w-full text-[12.5px]">
              <tbody>
                {chart.medications.map(([name, dose, freq, source, , status], i) => (
                  <tr key={i} className="border-b border-line/60 last:border-0">
                    <td className="py-1.5 pr-2 font-medium text-ink">{name}</td>
                    <td className="py-1.5 pr-2 text-ink-3">{[dose, freq].filter(Boolean).join(", ")}</td>
                    <td className="py-1.5 text-right">
                      {source !== "prescribed" && <span className="rounded bg-ochre-soft px-1.5 py-0.5 text-[10.5px] text-ochre">{source}</span>}
                      {status !== "active" && <span className="ml-1 rounded bg-sand px-1.5 py-0.5 text-[10.5px] text-ink-3">{status}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="rounded-2xl border border-line bg-panel p-5">
            <h3 className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3"><CalendarClock className="size-3.5" /> Referrals and appointments</h3>
            <div className="space-y-2">
              {chart.referrals.map(([kind, opened, status, detail], i) => (
                <div key={i} className="flex items-start gap-2 rounded-lg bg-sand/60 px-3 py-2">
                  <AlertTriangle className={clsx("mt-0.5 size-3.5 shrink-0", status === "open" || status === "requested" || status === "not scheduled" ? "text-ochre" : "text-oracle")} />
                  <div className="text-[12.5px]">
                    <div className="font-medium text-ink">{kind} <span className="font-normal text-ink-3">· {status} since {opened}</span></div>
                    {detail && <div className="text-ink-3">{detail}</div>}
                  </div>
                </div>
              ))}
              {chart.appointments.map(([d, kind, status], i) => (
                <div key={i} className="flex items-center gap-2 rounded-lg border border-teal/25 bg-teal-soft/50 px-3 py-2 text-[12.5px]">
                  <CalendarClock className="size-3.5 text-teal" />
                  <span className="font-medium text-ink">{kind}</span>
                  <span className="text-ink-3">· {d} · {status}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
});
