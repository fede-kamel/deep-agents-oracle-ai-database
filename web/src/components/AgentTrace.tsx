import clsx from "clsx";
import { ArrowRightLeft, Bot, Brain, ChevronDown, ChevronRight, ClipboardList, Database, FileCheck2, Search, ShieldAlert, ShieldCheck, Sparkles, Wrench } from "lucide-react";
import { useMemo, useState } from "react";
import { agentMeta } from "../agents";
import type { AgentEvent } from "../api";

type Kind = "thought" | "plan" | "delegate" | "tool" | "gate";
type Row = { i: number; t: number; agent: string; kind: Kind; title: string; body?: string; result?: string; icon: typeof Bot; tone?: "ok" | "bad" };

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
    /* not JSON */
  }
  if (name === "query_chart") return { title: `SQL  ${String(parsed.sql ?? "").replace(/\s+/g, " ")}`, icon: Database };
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
        out.push({ i, t: e.t, agent, kind: "thought", title: String(e.text ?? ""), icon: Brain });
        break;
      case "plan": {
        const todos = (e.todos as { content: string; status: string }[]) ?? [];
        const done = todos.filter((x) => x.status === "completed").length;
        out.push({ i, t: e.t, agent, kind: "plan", title: `plan updated · ${done} of ${todos.length} done`,
          body: todos.map((x) => `${x.status === "completed" ? "✓" : x.status === "in_progress" ? "▸" : "○"} ${x.content}`).join("\n"), icon: ClipboardList });
        break;
      }
      case "delegate":
        out.push({ i, t: e.t, agent, kind: "delegate", title: `task → ${agentMeta(String(e.subagent)).label}`, body: String(e.request ?? ""), icon: ArrowRightLeft });
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
        const at = open[`${agent}:${e.name}`]?.shift();
        if (at !== undefined) out[at].result = String(e.preview ?? "");
        break;
      }
      case "verify": {
        const problems = (e.problems as string[]) ?? [];
        out.push({ i, t: e.t, agent: "runner", kind: "gate",
          title: e.passed ? `brief accepted · ${e.citations} citations, every id found in the database` : `brief sent back · ${problems.length} problem${problems.length === 1 ? "" : "s"}`,
          body: problems.join("\n") || "all checks passed", icon: e.passed ? ShieldCheck : ShieldAlert, tone: e.passed ? "ok" : "bad" });
        break;
      }
      case "memory":
        out.push({ i, t: e.t, agent: "runner", kind: "gate", icon: Brain,
          title: e.written ? "brief recorded in long-term memory (OracleStore)" : `memory loaded: ${Number(e.entries ?? 0)} entries from OracleStore`,
          body: String(e.text ?? "") || "nothing remembered yet" });
        break;
      case "checkpoints":
        out.push({ i, t: e.t, agent: "runner", kind: "gate", icon: Database, title: `${Number(e.count)} checkpoints persisted by OracleSaver`, body: `thread_id ${String(e.thread_id)}` });
        break;
      case "policy":
        out.push({ i, t: e.t, agent: "runner", kind: "gate", icon: ShieldAlert, tone: "bad",
          title: `policy ${String(e.code)} refused the ${String(e.agent)}: escalate to medication-safety`, body: String(e.detail ?? "") });
        break;
      case "escalation":
        out.push({ i, t: e.t, agent: String(e.agent), kind: "delegate", icon: ArrowRightLeft, title: `escalation #${String(e.id)} → ${agentMeta(String(e.to)).label}`, body: "opened in DA_OWNER.agent_escalation" });
        break;
      case "start":
        out.push({ i, t: e.t, agent: "lead", kind: "thought", title: `run started as ${String(e.db_user)} · ${String(e.model)} lead, ${String(e.worker_model)} specialists`, body: String(e.question ?? ""), icon: Sparkles });
        break;
    }
  });
  return out;
}

/** Every event of the run in order, by agent, each one opening to its full text. */
export function AgentTrace({ events }: { events: AgentEvent[] }) {
  const [agents, setAgents] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const [openRows, setOpenRows] = useState<Set<number>>(new Set());
  const all = useMemo(() => rows(events), [events]);
  const t0 = events[0]?.t ?? 0;
  const present = useMemo(() => [...new Set(all.map((r) => r.agent))], [all]);
  const shown = all.filter((r) => (agents.size === 0 || agents.has(r.agent)) && (!query || `${r.title}\n${r.body ?? ""}\n${r.result ?? ""}`.toLowerCase().includes(query.toLowerCase())));
  const toggle = <T,>(set: Set<T>, v: T) => { const n = new Set(set); if (n.has(v)) n.delete(v); else n.add(v); return n; };

  if (events.length === 0) return <div className="grid h-full place-items-center text-sm text-ink-3">The timeline fills as the agents work.</div>;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-1.5 border-b border-line pb-3">
        {present.map((a) => {
          const m = agentMeta(a);
          const on = agents.size === 0 || agents.has(a);
          return (
            <button key={a} onClick={() => setAgents(toggle(agents, a))} aria-pressed={on}
              className={clsx("flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition", on ? "border-transparent" : "border-line bg-panel opacity-50")}
              style={on ? { background: m.soft, color: m.color } : undefined}>
              <span className="size-2 rounded-full" style={{ background: m.color }} /> {m.label}
              <span className="font-mono opacity-70">{all.filter((r) => r.agent === a).length}</span>
            </button>
          );
        })}
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search the timeline"
          className="ml-auto h-8 w-56 rounded-md border border-line bg-panel px-2.5 text-sm outline-none focus:border-ink-3/50" />
        <button onClick={() => setOpenRows(openRows.size ? new Set() : new Set(shown.map((r) => r.i)))}
          className="h-8 rounded-md border border-line bg-panel px-2.5 text-xs text-ink-3 hover:text-ink">
          {openRows.size ? "Collapse all" : "Expand all"}
        </button>
      </div>
      <ol className="scroll-thin min-h-0 flex-1 overflow-y-auto pt-2">
        {shown.map((r) => {
          const m = agentMeta(r.agent);
          const open = openRows.has(r.i);
          const Icon = r.icon;
          const nested = r.agent !== "lead" && r.agent !== "runner";
          return (
            <li key={r.i} className={clsx("group flex gap-3 py-1", nested && "pl-7")}>
              <span className="mt-1 grid size-7 shrink-0 place-items-center rounded-md" style={{ background: m.soft, color: r.tone === "bad" ? "#c74634" : m.color }}>
                <Icon className="size-3.5" strokeWidth={2.2} />
              </span>
              <button onClick={() => setOpenRows(toggle(openRows, r.i))} className="min-w-0 flex-1 rounded-md px-2 py-1 text-left hover:bg-sand/70">
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-xs text-ink-3">+{(r.t - t0).toFixed(1)}s</span>
                  <span className="text-xs font-semibold" style={{ color: m.color }}>{m.label}</span>
                  {r.result !== undefined && <span className="rounded bg-ok-soft px-1 text-[10px] font-semibold text-ok">result</span>}
                  {open ? <ChevronDown className="ml-auto size-3.5 text-ink-3" /> : <ChevronRight className="ml-auto size-3.5 text-ink-3 opacity-0 group-hover:opacity-100" />}
                </div>
                <div className={clsx("text-sm leading-snug", r.kind === "thought" ? "italic text-ink-2" : r.kind === "tool" ? "font-mono text-xs text-ink-2" : "text-ink", !open && "line-clamp-2")}>{r.title}</div>
                {open && (
                  <div className="mt-1.5 space-y-1.5" onClick={(e) => e.stopPropagation()}>
                    {r.body && <pre className="scroll-thin max-h-[60vh] overflow-auto rounded-md border border-line bg-paper p-2.5 font-mono text-xs leading-relaxed whitespace-pre-wrap text-ink-2">{r.body}</pre>}
                    {r.result && <pre className="scroll-thin max-h-[60vh] overflow-auto rounded-md border border-ok/25 bg-ok-soft/40 p-2.5 font-mono text-xs leading-relaxed whitespace-pre-wrap text-ink-2">{r.result}</pre>}
                  </div>
                )}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
