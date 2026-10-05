import clsx from "clsx";
import {
  ArrowRightLeft, Bot, Brain, ChevronDown, ChevronRight, ClipboardList, Database, FileCheck2,
  Search, ShieldAlert, ShieldCheck, Sparkles, Wrench,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { AgentEvent } from "../api";

const AGENTS: Record<string, { label: string; color: string; bg: string; depth: number }> = {
  lead: { label: "Lead", color: "#161F34", bg: "#e8eaf0", depth: 0 },
  "chart-analyst": { label: "Chart analyst", color: "#2C5967", bg: "#e6eff1", depth: 1 },
  "guideline-researcher": { label: "Guideline researcher", color: "#5f7d4f", bg: "#edf3e8", depth: 1 },
  "evidence-researcher": { label: "Evidence researcher", color: "#6b4fa0", bg: "#f0ecf7", depth: 1 },
  "care-coordinator": { label: "Care coordinator", color: "#b07d1f", bg: "#fbf3e2", depth: 1 },
  "medication-safety": { label: "Medication safety", color: "#C74634", bg: "#fbeceb", depth: 1 },
  runner: { label: "Runner gate", color: "#2e8b57", bg: "#e9f5ee", depth: 0 },
};
const meta = (a?: string) => AGENTS[a ?? ""] ?? { label: a ?? "agent", color: "#6f6964", bg: "#f1efed", depth: 1 };

type Kind = "thought" | "plan" | "delegate" | "tool" | "gate";
const KINDS: { key: Kind; label: string }[] = [
  { key: "thought", label: "reasoning" },
  { key: "plan", label: "plan" },
  { key: "delegate", label: "delegation" },
  { key: "tool", label: "tool calls" },
  { key: "gate", label: "gate" },
];

type Row = {
  i: number;
  t: number;
  agent: string;
  kind: Kind;
  title: string;
  body?: string;
  result?: string;
  icon: typeof Bot;
  tone?: "ok" | "bad";
};

function pretty(raw: unknown): string {
  if (typeof raw !== "string") return JSON.stringify(raw, null, 2);
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

function toolTitle(name: string, args: string): { title: string; icon: typeof Bot } {
  let parsed: Record<string, unknown> = {};
  try {
    parsed = JSON.parse(args);
  } catch {
    /* previews may be truncated */
  }
  if (name === "query_chart") return { title: `SQL  ${String(parsed.sql ?? "").replace(/\s+/g, " ").slice(0, 160)}`, icon: Database };
  if (name.startsWith("search")) return { title: `${name}  “${String(parsed.query ?? "")}”`, icon: Search };
  if (name.startsWith("get_document")) return { title: `${name}  ${String(parsed.document_id ?? "")}`, icon: FileCheck2 };
  return { title: name, icon: Wrench };
}

/** Pair each tool call with its result and turn the raw stream into readable rows. */
function rows(events: AgentEvent[]): Row[] {
  const out: Row[] = [];
  const open: Record<string, number[]> = {};
  events.forEach((e, i) => {
    const agent = String(e.agent ?? "lead");
    switch (e.type) {
      case "thought":
        out.push({ i, t: e.t, agent, kind: "thought", title: String(e.text ?? "").slice(0, 220), body: String(e.text ?? ""), icon: Brain });
        break;
      case "plan": {
        const todos = (e.todos as { content: string; status: string }[]) ?? [];
        const done = todos.filter((x) => x.status === "completed").length;
        out.push({ i, t: e.t, agent, kind: "plan", title: `plan updated · ${done}/${todos.length} done`,
          body: todos.map((x) => `${x.status === "completed" ? "✓" : x.status === "in_progress" ? "▸" : "○"} ${x.content}`).join("\n"), icon: ClipboardList });
        break;
      }
      case "delegate":
        out.push({ i, t: e.t, agent, kind: "delegate", title: `task → ${meta(String(e.subagent)).label}`, body: String(e.request ?? ""), icon: ArrowRightLeft });
        break;
      case "tool": {
        const { title, icon } = toolTitle(String(e.name), String(e.args ?? ""));
        out.push({ i, t: e.t, agent, kind: "tool", title, body: pretty(e.args), icon });
        (open[`${agent}:${e.name}`] ??= []).push(out.length - 1);
        break;
      }
      case "tool_result": {
        if (e.name === "task") {
          out.push({ i, t: e.t, agent, kind: "delegate", title: "specialist reported back", body: String(e.preview ?? ""), icon: ArrowRightLeft });
          break;
        }
        const q = open[`${agent}:${e.name}`];
        const at = q?.shift();
        if (at !== undefined) out[at].result = String(e.preview ?? "");
        break;
      }
      case "verify": {
        const problems = (e.problems as string[]) ?? [];
        out.push({ i, t: e.t, agent: "runner", kind: "gate",
          title: e.passed ? `brief accepted · ${e.citations} citations, every id found in the database` : `brief sent back · ${problems.length} problem(s)`,
          body: problems.join("\n") || "all checks passed", icon: e.passed ? ShieldCheck : ShieldAlert, tone: e.passed ? "ok" : "bad" });
        break;
      }
      case "memory":
        out.push({ i, t: e.t, agent: "runner", kind: "gate", icon: Brain,
          title: e.written ? "brief recorded in long-term memory (OracleStore)" : `memory loaded: ${Number(e.entries ?? 0)} entries from OracleStore`,
          body: String(e.text ?? "") || "nothing remembered yet" });
        break;
      case "checkpoints":
        out.push({ i, t: e.t, agent: "runner", kind: "gate", icon: Database,
          title: `${Number(e.count)} checkpoints persisted by OracleSaver`, body: `thread_id ${String(e.thread_id)}` });
        break;
      case "policy":
        out.push({ i, t: e.t, agent: "runner", kind: "gate", icon: ShieldAlert, tone: "bad",
          title: `policy ${String(e.code)} refused the ${String(e.agent)}: escalate to medication-safety`, body: String(e.detail ?? "") });
        break;
      case "escalation":
        out.push({ i, t: e.t, agent: String(e.agent), kind: "delegate", icon: ArrowRightLeft,
          title: `escalation #${String(e.id)} → ${meta(String(e.to)).label}`, body: "opened in DA_OWNER.agent_escalation" });
        break;
      case "start":
        out.push({ i, t: e.t, agent: "lead", kind: "thought", title: `run started as ${String(e.db_user)} · ${String(e.model)} lead, ${String(e.worker_model)} specialists`, body: String(e.question ?? ""), icon: Sparkles });
        break;
    }
  });
  return out;
}

export function AgentTrace({ events }: { events: AgentEvent[] }) {
  const [agents, setAgents] = useState<Set<string>>(new Set());
  const [kinds, setKinds] = useState<Set<Kind>>(new Set(KINDS.map((k) => k.key)));
  const [query, setQuery] = useState("");
  const [openRows, setOpenRows] = useState<Set<number>>(new Set());
  const all = useMemo(() => rows(events), [events]);
  const t0 = events[0]?.t ?? 0;
  const present = useMemo(() => [...new Set(all.map((r) => r.agent))], [all]);
  const shown = all.filter(
    (r) =>
      (agents.size === 0 || agents.has(r.agent)) &&
      kinds.has(r.kind) &&
      (!query || `${r.title}\n${r.body ?? ""}\n${r.result ?? ""}`.toLowerCase().includes(query.toLowerCase())),
  );
  const toggle = <T,>(set: Set<T>, v: T) => {
    const n = new Set(set);
    if (n.has(v)) n.delete(v);
    else n.add(v);
    return n;
  };
  const counts = (a: string) => all.filter((r) => r.agent === a).length;

  if (events.length === 0)
    return <div className="grid h-full place-items-center text-[13px] text-ink-3">The trace fills as the agents work: reasoning, plans, delegations, every tool call and result, and the gate's verdicts.</div>;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-1.5 border-b border-line pb-2.5">
        {present.map((a) => {
          const m = meta(a);
          const on = agents.size === 0 || agents.has(a);
          return (
            <button key={a} onClick={() => setAgents(toggle(agents, a))}
              className={clsx("flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11.5px] font-medium transition", on ? "border-transparent" : "border-line bg-panel opacity-50")}
              style={on ? { background: m.bg, color: m.color } : undefined}>
              <span className="size-2 rounded-full" style={{ background: m.color }} /> {m.label}
              <span className="font-mono text-[10px] opacity-70">{counts(a)}</span>
            </button>
          );
        })}
        <span className="mx-1 h-4 w-px bg-line" />
        {KINDS.map((k) => (
          <button key={k.key} onClick={() => setKinds(toggle(kinds, k.key))}
            className={clsx("rounded-md px-2 py-1 text-[11px]", kinds.has(k.key) ? "bg-ink text-white" : "bg-sand text-ink-3")}>
            {k.label}
          </button>
        ))}
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="search the trace…"
          className="ml-auto w-48 rounded-md border border-line bg-panel px-2.5 py-1 text-[12px] outline-none focus:border-ink-3/50" />
        <button onClick={() => setOpenRows(openRows.size ? new Set() : new Set(shown.map((r) => r.i)))}
          className="rounded-md border border-line bg-panel px-2 py-1 text-[11px] text-ink-3 hover:text-ink">
          {openRows.size ? "collapse all" : "expand all"}
        </button>
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto pt-2">
        <ol className="relative">
          {shown.map((r) => {
            const m = meta(r.agent);
            const open = openRows.has(r.i);
            const Icon = r.icon;
            return (
              <li key={r.i} className="group relative flex gap-3 py-1" style={{ paddingLeft: m.depth * 28 }}>
                <span className="absolute top-0 bottom-0 w-0.5 rounded" style={{ left: m.depth * 28 + 13, background: m.bg }} />
                <div className="relative z-10 mt-1 grid size-7 shrink-0 place-items-center rounded-lg" style={{ background: m.bg, color: r.tone === "bad" ? "#C0392B" : m.color }}>
                  <Icon className="size-3.5" strokeWidth={2.3} />
                </div>
                <button onClick={() => setOpenRows(toggle(openRows, r.i))} className="min-w-0 flex-1 rounded-lg px-2 py-1 text-left hover:bg-sand/70">
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-[10.5px] text-ink-3">+{(r.t - t0).toFixed(1)}s</span>
                    <span className="text-[11px] font-semibold" style={{ color: m.color }}>{m.label}</span>
                    {r.result !== undefined && <span className="rounded bg-moss-soft px-1 text-[9.5px] font-semibold text-moss">result</span>}
                    {open ? <ChevronDown className="ml-auto size-3.5 text-ink-3" /> : <ChevronRight className="ml-auto size-3.5 text-ink-3 opacity-0 group-hover:opacity-100" />}
                  </div>
                  <div className={clsx("text-[12.5px] leading-snug", r.kind === "thought" ? "italic text-ink-2" : r.kind === "tool" ? "font-mono text-[11.5px] text-ink-2" : "text-ink", !open && "line-clamp-2")}>
                    {r.title}
                  </div>
                  {open && (
                    <div className="mt-1.5 space-y-1.5" onClick={(e) => e.stopPropagation()}>
                      {r.body && (
                        <pre className="scroll-thin max-h-[420px] overflow-auto rounded-md border border-line bg-paper p-2.5 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-ink-2">{r.body}</pre>
                      )}
                      {r.result && (
                        <pre className="scroll-thin max-h-[420px] overflow-auto rounded-md border border-moss/25 bg-moss-soft/40 p-2.5 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-ink-2">{r.result}</pre>
                      )}
                    </div>
                  )}
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
