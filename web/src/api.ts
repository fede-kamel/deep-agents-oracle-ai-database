// Typed client for ui/server.py and the reducer that turns the run's event
// stream into the view model the screen renders.

export type Lab = { test: string; value: number; unit: string; date: string };

export type Patient = {
  key: "X" | "Y" | "Z";
  id: string;
  display_name: string;
  alias: string;
  age: number;
  sex: string;
  situation: string;
  visit_reason: string;
  narrative: string;
  question: string;
  db_user: string;
  latest_labs?: Lab[];
  active_medications?: number;
  encounters?: number;
  notes?: number;
  visible_patients?: number;
  error?: string;
};

export type Safety = {
  sandbox_image: string;
  provider: string;
  egress: { rule: string; target: string; allow: string; credential: string }[];
  binary: string;
  everything_else: string;
  chat_model: string;
  worker_model: string;
};

export type AgentEvent = {
  type: "start" | "plan" | "delegate" | "tool" | "tool_result" | "brief" | "done" | "error" | "blocked" | "verify" | "nudge" | "thought" | "memory" | "checkpoints" | "policy" | "escalation";
  t: number;
  agent?: string;
  [key: string]: unknown;
};

export type StreamItem =
  | { channel: "agent"; event: AgentEvent }
  | { channel: "console"; line: string }
  | { channel: "status"; status: string; exit_code: number };

export type Todo = { content: string; status: "pending" | "in_progress" | "completed" };

export type ToolCall = {
  id: number;
  name: string;
  args: string;
  result?: string;
  t: number;
};

export type Lane = {
  name: string;
  request: string;
  status: "running" | "done";
  calls: ToolCall[];
  report?: string;
  started: number;
  finished?: number;
};

export type RunView = {
  id?: string;
  patient?: string;
  status: "idle" | "starting" | "running" | "succeeded" | "failed" | "blocked";
  meta?: { model?: string; worker_model?: string; db_user?: string; question?: string };
  todos: Todo[];
  lanes: Lane[];
  leadCalls: ToolCall[];
  console: string[];
  brief?: string;
  done?: { seconds: number; tool_calls: number; delegations: number; sql: number; searches: number };
  error?: string;
  started?: number;
  repairs: string[][];
  verified?: { passed: boolean; citations: number; problems: string[] };
  /** Every agent event in arrival order: the raw material of the Agent trace. */
  events: AgentEvent[];
  memory?: { entries: number; text: string; written?: boolean };
  checkpoints?: { count: number; thread_id: string };
  /** Latest reasoning text per agent, shown on the overview lanes. */
  thoughts: Record<string, string>;
};

export const emptyRun = (): RunView => ({
  status: "idle", todos: [], lanes: [], leadCalls: [], console: [], repairs: [], events: [], thoughts: {},
});

let seq = 0;

export function reduce(view: RunView, item: StreamItem): RunView {
  if (item.channel === "console") return { ...view, console: [...view.console, item.line] };
  if (item.channel === "status") {
    const status = item.status as RunView["status"];
    return { ...view, status, lanes: view.lanes.map((l) => ({ ...l, status: "done" as const })) };
  }
  const e = item.event;
  const next: RunView = {
    ...view,
    status: view.status === "starting" ? "running" : view.status,
    events: [...view.events, e],
  };
  switch (e.type) {
    case "start":
      return {
        ...next,
        status: "running",
        started: e.t,
        meta: {
          model: e.model as string,
          worker_model: e.worker_model as string,
          db_user: e.db_user as string,
          question: e.question as string,
        },
      };
    case "memory":
      return e.written
        ? { ...next, memory: { ...(next.memory ?? { entries: 0, text: "" }), written: true } }
        : { ...next, memory: { entries: Number(e.entries ?? 0), text: String(e.text ?? "") } };
    case "checkpoints":
      return { ...next, checkpoints: { count: Number(e.count ?? 0), thread_id: String(e.thread_id ?? "") } };
    case "thought":
      return { ...next, thoughts: { ...next.thoughts, [String(e.agent)]: String(e.text ?? "") } };
    case "plan":
      return { ...next, todos: (e.todos as Todo[]) ?? [] };
    case "delegate":
      return {
        ...next,
        lanes: [
          ...next.lanes,
          { name: e.subagent as string, request: (e.request as string) ?? "", status: "running", calls: [], started: e.t },
        ],
      };
    case "tool": {
      const call: ToolCall = { id: ++seq, name: e.name as string, args: (e.args as string) ?? "", t: e.t };
      if (e.agent === "lead") return { ...next, leadCalls: [...next.leadCalls, call] };
      const idx = laneIndex(next.lanes, e.agent as string);
      if (idx < 0) return { ...next, leadCalls: [...next.leadCalls, call] };
      const lanes = [...next.lanes];
      lanes[idx] = { ...lanes[idx], calls: [...lanes[idx].calls, call] };
      return { ...next, lanes };
    }
    case "tool_result": {
      const preview = (e.preview as string) ?? "";
      if (e.agent === "lead" && e.name === "task") {
        // A specialist finished: close the oldest running lane.
        const lanes = [...next.lanes];
        const idx = lanes.findIndex((l) => l.status === "running");
        if (idx >= 0) lanes[idx] = { ...lanes[idx], status: "done", report: preview, finished: e.t };
        return { ...next, lanes };
      }
      const attach = (calls: ToolCall[]) => {
        const copy = [...calls];
        for (let i = copy.length - 1; i >= 0; i--) {
          if (copy[i].name === e.name && copy[i].result === undefined) {
            copy[i] = { ...copy[i], result: preview };
            break;
          }
        }
        return copy;
      };
      if (e.agent === "lead") return { ...next, leadCalls: attach(next.leadCalls) };
      const idx = laneIndex(next.lanes, e.agent as string);
      if (idx < 0) return next;
      const lanes = [...next.lanes];
      lanes[idx] = { ...lanes[idx], calls: attach(lanes[idx].calls) };
      return { ...next, lanes };
    }
    case "verify": {
      const problems = (e.problems as string[]) ?? [];
      if (e.citations === undefined) return { ...next, repairs: [...next.repairs, problems] };
      return { ...next, verified: { passed: Boolean(e.passed), citations: e.citations as number, problems } };
    }
    case "brief":
      return { ...next, brief: e.markdown as string };
    case "done":
      return { ...next, done: e as unknown as RunView["done"] };
    case "error":
    case "blocked":
      return { ...next, status: e.type === "blocked" ? "blocked" : "failed", error: e.message as string };
  }
  return next;
}

function laneIndex(lanes: Lane[], agent: string): number {
  for (let i = lanes.length - 1; i >= 0; i--) if (lanes[i].name === agent) return i;
  // Updates from a specialist the stream could not name go to the newest running lane.
  for (let i = lanes.length - 1; i >= 0; i--) if (lanes[i].status === "running") return i;
  return -1;
}

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export async function startRun(patient: string, question: string): Promise<{ id: string }> {
  const r = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient, question }),
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText);
  return r.json();
}
