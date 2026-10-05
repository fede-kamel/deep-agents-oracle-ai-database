import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpenText, Bot, CheckCircle2, ClipboardCheck, Circle, CircleDashed, Database, FileText, FlaskConical,
  Brain, Loader2, Search, ShieldAlert, ShieldCheck, Sparkles, TableProperties, UserRound,
} from "lucide-react";
import type { Lane, RunView, ToolCall } from "../api";

const LANES: Record<string, { label: string; store: string; icon: typeof Database; tone: string; ring: string }> = {
  "chart-analyst": { label: "Chart analyst", store: "SQL + patient notes", icon: TableProperties, tone: "text-teal bg-teal-soft", ring: "border-teal/40" },
  "guideline-researcher": { label: "Guideline researcher", store: "MedQuAD reference", icon: BookOpenText, tone: "text-moss bg-moss-soft", ring: "border-moss/40" },
  "evidence-researcher": { label: "Evidence researcher", store: "PubMed abstracts", icon: FlaskConical, tone: "text-violet bg-violet-soft", ring: "border-violet/40" },
  "care-coordinator": { label: "Care coordinator", store: "proposes actions, escalates", icon: ClipboardCheck, tone: "text-ochre bg-ochre-soft", ring: "border-ochre/40" },
  "medication-safety": { label: "Medication safety", store: "only agent allowed med changes", icon: ShieldAlert, tone: "text-oracle bg-oracle-soft", ring: "border-oracle/40" },
};

function parseArgs(args: string): Record<string, unknown> {
  try {
    return JSON.parse(args);
  } catch {
    return {};
  }
}

function hitIds(result?: string): string[] {
  if (!result) return [];
  return [...new Set([...result.matchAll(/Doc ID: ([A-Z][A-Z0-9-]+)/g)].map((m) => m[1]))].slice(0, 6);
}

function Call({ call }: { call: ToolCall }) {
  const args = parseArgs(call.args);
  if (call.name === "query_chart") {
    const rows = call.result ? call.result.split("\n").filter((l) => l.startsWith("{")).length : undefined;
    return (
      <div className="rounded-lg border border-line bg-sand/50">
        <div className="flex items-center gap-1.5 px-2.5 pt-2 text-[10.5px] font-semibold uppercase tracking-wide text-teal">
          <Database className="size-3" /> SQL · Oracle AI Database
          {rows !== undefined && <span className="ml-auto font-mono normal-case text-ink-3">{call.result?.startsWith("Oracle error") ? "error" : `${rows} rows`}</span>}
        </div>
        <pre className="scroll-thin overflow-x-auto px-2.5 pt-1 pb-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-ink-2">
          {String(args.sql ?? call.args).replace(/\s+/g, " ").trim()}
        </pre>
      </div>
    );
  }
  if (call.name.startsWith("search") || call.name.startsWith("get_document")) {
    const ids = hitIds(call.result);
    return (
      <div className="rounded-lg border border-line bg-panel px-2.5 py-2">
        <div className="flex items-center gap-1.5 text-[12px] text-ink-2">
          <Search className="size-3.5 text-ink-3" />
          <span className="font-mono text-[10.5px] text-ink-3">{call.name}</span>
          <span className="truncate">“{String(args.query ?? args.document_id ?? "")}”</span>
        </div>
        {ids.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {ids.map((id) => (
              <span key={id} className="rounded bg-sand px-1.5 py-0.5 font-mono text-[10px] text-ink-3">{id}</span>
            ))}
          </div>
        )}
        {!call.result && <Loader2 className="mt-1 size-3 animate-spin text-ink-3" />}
      </div>
    );
  }
  if (call.name.startsWith("propose_") || call.name.startsWith("draft_")) {
    const label = String(args.subject ?? (Array.isArray(args.tests) ? (args.tests as string[]).join(", ") : args.visit_type ?? ""));
    return (
      <div className="rounded-lg border border-ochre/30 bg-ochre-soft/50 px-2.5 py-2">
        <div className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-wide text-ochre">
          <ClipboardCheck className="size-3" /> {call.name.replace(/_/g, " ")}
        </div>
        <div className="mt-0.5 text-[12px] text-ink-2">{label}</div>
        <div className="mt-0.5 text-[11px] text-ink-3">{call.result ? call.result.split(".")[0] : "proposing…"} · awaits your approval</div>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 rounded-lg border border-dashed border-line px-2.5 py-1.5 font-mono text-[11px] text-ink-3">
      <Sparkles className="size-3" /> {call.name}
    </div>
  );
}

function LaneCard({ lane, thought }: { lane: Lane; thought?: string }) {
  const meta = LANES[lane.name] ?? { label: lane.name, store: "", icon: Bot, tone: "text-ink-2 bg-sand", ring: "border-line" };
  const Icon = meta.icon;
  const secs = ((lane.finished ?? Date.now() / 1000) - lane.started).toFixed(0);
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={clsx("flex min-w-0 flex-col rounded-xl border bg-panel p-3.5", lane.status === "running" ? meta.ring : "border-line")}
    >
      <div className="flex items-center gap-2.5">
        <div className={clsx("grid size-8 place-items-center rounded-lg", meta.tone)}>
          <Icon className="size-4" strokeWidth={2.2} />
        </div>
        <div className="min-w-0">
          <div className="text-[13px] font-semibold">{meta.label}</div>
          <div className="text-[11px] text-ink-3">{meta.store}</div>
        </div>
        <div className="ml-auto flex items-center gap-1 text-[11px] text-ink-3">
          {lane.status === "running" ? <Loader2 className="size-3.5 animate-spin text-oracle" /> : <CheckCircle2 className="size-3.5 text-moss" />}
          {secs}s
        </div>
      </div>
      <p className="mt-2 line-clamp-3 text-[12px] leading-snug text-ink-3">{lane.request}</p>
      {thought && lane.status === "running" && (
        <p className="mt-2 line-clamp-4 rounded-lg border-l-2 border-ink-3/30 bg-sand/50 px-2.5 py-1.5 text-[11.5px] italic leading-snug text-ink-2">{thought}</p>
      )}
      <div className="mt-2.5 space-y-1.5">
        <AnimatePresence initial={false}>
          {lane.calls.map((c) => (
            <motion.div key={c.id} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}>
              <Call call={c} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      {lane.report && (
        <div className="mt-2.5 rounded-lg bg-sand/70 px-2.5 py-2 text-[11.5px] leading-snug text-ink-2">
          <span className="font-semibold text-ink">Returned · </span>
          {lane.report.replace(/[*#]/g, "").slice(0, 260)}…
        </div>
      )}
    </motion.div>
  );
}

export function RunTimeline({ view, question, patientName }: { view: RunView; question: string; patientName: string }) {
  if (view.status === "idle") return null;
  const writing = view.leadCalls.some((c) => c.name === "write_file");
  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <div className="max-w-[78%] rounded-2xl rounded-br-md bg-ink px-4 py-3 text-[13.5px] leading-relaxed text-white shadow-sm">
          <div className="mb-1 flex items-center gap-1.5 text-[11px] text-white/60">
            <UserRound className="size-3" /> Clinician · {patientName}
          </div>
          {question}
        </div>
      </div>

      <div className="flex gap-3">
        <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-oracle text-white shadow-sm">
          <Bot className="size-4" />
        </div>
        <div className="min-w-0 flex-1 space-y-4">
          <div className="text-[13px] text-ink-2">
            <span className="font-semibold text-ink">Deep Agent</span> · langchain-oci{" "}
            <span className="font-mono text-[11.5px]">create_deepagents_agent</span> · {view.meta?.model ?? "…"} lead,{" "}
            {view.meta?.worker_model ?? "…"} specialists
          </div>

          {view.memory && (
            <div className="flex items-start gap-3 rounded-xl border border-teal/25 bg-teal-soft/40 px-4 py-3">
              <Brain className="mt-0.5 size-4 shrink-0 text-teal" />
              <div className="text-[12.5px] leading-snug text-ink-2">
                <span className="font-semibold text-ink">Memory loaded from Oracle · </span>
                {view.memory.entries === 0
                  ? "first brief for this patient: nothing remembered yet."
                  : `${view.memory.entries} entries from earlier briefs and clinician decisions, read from /memories/patient-history.md (OracleStore).`}
                {view.memory.written && <span className="ml-1 font-semibold text-moss">This brief has been added to memory.</span>}
              </div>
            </div>
          )}
          {view.thoughts.lead && (
            <div className="rounded-xl border-l-[3px] border-navy/40 bg-panel px-4 py-3 text-[12.5px] italic leading-relaxed text-ink-2" style={{ borderColor: "#161F3466" }}>
              <span className="mr-1.5 not-italic text-[10.5px] font-semibold uppercase tracking-wide text-ink-3">lead is thinking</span>
              {view.thoughts.lead.slice(0, 600)}
            </div>
          )}
          <div className="rounded-xl border border-line bg-panel p-4">
            <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">
              Plan <span className="font-mono normal-case tracking-normal">write_todos</span>
            </div>
            {view.todos.length === 0 ? (
              <div className="flex items-center gap-2 text-[12.5px] text-ink-3">
                <Loader2 className="size-3.5 animate-spin" /> planning…
              </div>
            ) : (
              <ul className="space-y-1.5">
                {view.todos.map((t, i) => (
                  <li key={i} className="flex items-start gap-2 text-[13px]">
                    {t.status === "completed" ? (
                      <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-moss" />
                    ) : t.status === "in_progress" ? (
                      <CircleDashed className="mt-0.5 size-4 shrink-0 animate-spin text-oracle [animation-duration:3s]" />
                    ) : (
                      <Circle className="mt-0.5 size-4 shrink-0 text-line" />
                    )}
                    <span className={clsx(t.status === "completed" ? "text-ink-3 line-through decoration-ink-3/40" : "text-ink-2")}>{t.content}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {view.lanes.length > 0 && (
            <div>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">
                Delegated to specialists <span className="font-mono normal-case tracking-normal">task</span>
              </div>
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                {view.lanes.map((l, i) => (
                  <LaneCard key={`${l.name}-${i}`} lane={l} thought={view.thoughts[l.name]} />
                ))}
              </div>
            </div>
          )}

          {view.repairs.map((r, i) => (
            <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-xl border border-ochre/30 bg-ochre-soft px-4 py-3 text-[12.5px] text-ink-2">
              <div className="mb-1 flex items-center gap-1.5 font-semibold text-ochre">
                <ShieldAlert className="size-4" /> Brief verifier sent the draft back
              </div>
              <ul className="list-disc space-y-0.5 pl-5">{r.map((p) => <li key={p}>{p}</li>)}</ul>
            </motion.div>
          ))}

          {(writing || view.brief) && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 rounded-xl border border-oracle/30 bg-oracle-soft/50 px-4 py-3 text-[13px] text-ink-2">
              <FileText className="size-4 text-oracle" />
              {view.brief ? "The brief is rendered from the structured PreVisitBrief." : "Writing the brief…"}
              {view.verified && (
                <span className={clsx("ml-auto flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11.5px] font-semibold", view.verified.passed ? "bg-moss-soft text-moss" : "bg-oracle-soft text-oracle")}>
                  <ShieldCheck className="size-3.5" />
                  {view.verified.passed ? `verified · ${view.verified.citations} citations` : "not verified"}
                </span>
              )}
            </motion.div>
          )}

          {view.done && (
            <div className="flex flex-wrap gap-2 text-[11.5px]">
              {[
                ["seconds", `${view.done.seconds}s`],
                ["tool calls", view.done.tool_calls],
                ["SQL queries", view.done.sql],
                ["searches", view.done.searches],
                ["delegations", view.done.delegations],
                ["actions proposed", (view.done as unknown as { actions?: number }).actions ?? 0],
                ["Oracle checkpoints", view.checkpoints?.count ?? "–"],
              ].map(([k, v]) => (
                <span key={k} className="rounded-full border border-line bg-panel px-2.5 py-1 text-ink-3">
                  <span className="font-mono font-semibold text-ink">{v}</span> {k}
                </span>
              ))}
            </div>
          )}
          {view.error && (
            <div className="rounded-xl border border-oracle/40 bg-oracle-soft px-4 py-3 text-[12.5px] text-oracle">
              <span className="font-semibold">{view.status === "blocked" ? "Blocked by the input guard: " : "Run failed: "}</span>
              {view.error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
