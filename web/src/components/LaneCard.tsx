import clsx from "clsx";
import { CheckCircle2, ClipboardCheck, Database, Loader2, Search, Wrench } from "lucide-react";
import { agentMeta } from "../agents";
import type { Lane, ToolCall } from "../api";
import { fmtSeconds } from "../hooks";
import { Prose } from "./Prose";
import { Label } from "./ui";

function parseArgs(args: string): Record<string, unknown> {
  try {
    return JSON.parse(args);
  } catch {
    return {};
  }
}

const hitIds = (result?: string) => (result ? [...new Set([...result.matchAll(/Doc ID: ([A-Z][A-Z0-9-]+)/g)].map((m) => m[1]))] : []);

function Call({ call }: { call: ToolCall }) {
  const args = parseArgs(call.args);
  if (call.name === "query_chart") {
    const rows = call.result ? call.result.split("\n").filter((l) => l.startsWith("{")).length : undefined;
    return (
      <div className="rounded-md border border-line bg-sand/50">
        <div className="flex items-center gap-1.5 px-3 pt-2 text-xs font-semibold uppercase tracking-wide text-teal">
          <Database className="size-3" /> SQL · Oracle AI Database
          {rows === undefined && <Loader2 className="ml-auto size-3 animate-spin text-ink-3" />}
        </div>
        <pre className="scroll-thin overflow-x-auto px-3 pt-1 pb-2 font-mono text-xs leading-relaxed whitespace-pre-wrap text-ink-2">{String(args.sql ?? call.args).replace(/\s+/g, " ").trim()}</pre>
        {call.result && <Result summary={call.result.startsWith("Oracle error") ? "error" : `${rows} ${rows === 1 ? "row" : "rows"}`} text={call.result} />}
      </div>
    );
  }
  if (call.name.startsWith("search") || call.name.startsWith("get_document")) {
    const ids = hitIds(call.result);
    return (
      <div className="rounded-md border border-line px-3 py-2">
        <div className="flex items-start gap-1.5 text-sm text-ink-2">
          <Search className="mt-0.5 size-3.5 shrink-0 text-ink-3" />
          <span className="font-mono text-xs text-ink-3">{call.name}</span>
          <span className="min-w-0 break-words">“{String(args.query ?? args.document_id ?? "")}”</span>
          {!call.result && <Loader2 className="ml-auto size-3 shrink-0 animate-spin text-ink-3" />}
        </div>
        {ids.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {ids.map((id) => <span key={id} className="rounded bg-sand px-1.5 py-0.5 font-mono text-[10px] text-ink-3">{id}</span>)}
          </div>
        )}
        {call.result && <Result summary={`${ids.length} ${ids.length === 1 ? "hit" : "hits"}, full text`} text={call.result} />}
      </div>
    );
  }
  if (call.name.startsWith("propose_") || call.name.startsWith("draft_")) {
    const label = String(args.subject ?? (Array.isArray(args.tests) ? (args.tests as string[]).join(", ") : args.visit_type ?? args.medication ?? ""));
    return (
      <div className="rounded-md border border-warn/30 bg-warn-soft/50 px-3 py-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-warn"><ClipboardCheck className="size-3" /> {call.name.replace(/_/g, " ")}</div>
        <div className="mt-0.5 text-sm text-ink-2">{label}</div>
        <div className="mt-0.5 text-xs text-ink-3">{call.result ? call.result.split(".")[0] : "proposing…"} · awaits a decision on the Actions tab</div>
      </div>
    );
  }
  return (
    <div className="rounded-md border border-dashed border-line px-3 py-2">
      <div className="flex items-center gap-1.5 font-mono text-xs text-ink-3">
        <Wrench className="size-3" /> {call.name}
        {!call.result && <Loader2 className="ml-auto size-3 animate-spin" />}
      </div>
      {call.result && <Result summary="result" text={call.result} open={call.result.length < 400} />}
    </div>
  );
}

/** A tool's full result, one click away; short ones are open from the start. */
function Result({ summary, text, open = false }: { summary: string; text: string; open?: boolean }) {
  return (
    <details open={open} className="group mt-1 px-3 pb-2">
      <summary className="cursor-pointer list-none text-xs text-ink-3 hover:text-ink">
        <span className="inline-block w-3 transition group-open:rotate-90">▸</span> {summary}
      </summary>
      <pre className="scroll-thin mt-1 max-h-72 overflow-auto rounded border border-line bg-panel p-2 font-mono text-xs leading-relaxed whitespace-pre-wrap text-ink-2">{text}</pre>
    </details>
  );
}

/** One delegation to a specialist: the request, what came back, every tool call. */
export function LaneCard({ lane, thought, now }: { lane: Lane; thought?: string; now: number }) {
  const meta = agentMeta(lane.name);
  const Icon = meta.icon;
  const running = lane.status === "running";
  return (
    <article className={clsx("rounded-lg border bg-panel p-4", running ? "border-ink-3/40" : "border-line")}>
      <div className="flex items-center gap-3">
        <span className="grid size-8 shrink-0 place-items-center rounded-md" style={{ background: meta.soft, color: meta.color }}><Icon className="size-4" strokeWidth={2.2} /></span>
        <div className="min-w-0">
          <div className="text-sm font-semibold">{meta.label}</div>
          <div className="text-xs text-ink-3">{meta.role}</div>
        </div>
        <div className="ml-auto flex items-center gap-1.5 text-xs text-ink-3">
          {running ? <Loader2 className="size-3.5 animate-spin text-oracle" /> : <CheckCircle2 className="size-3.5 text-ok" />}
          {fmtSeconds((lane.finished ?? now) - lane.started)}
        </div>
      </div>

      <Label className="mt-4">Request from the lead</Label>
      <p className="mt-1 whitespace-pre-wrap text-sm text-ink-2">{lane.request}</p>

      {thought && running && (
        <p className="mt-3 whitespace-pre-wrap border-l-2 border-line pl-3 text-sm italic text-ink-3">{thought}</p>
      )}

      {lane.report && (
        <>
          <Label className="mt-4">Returned to the lead</Label>
          <Prose className="mt-1 text-sm">{lane.report}</Prose>
        </>
      )}

      {lane.calls.length > 0 && (
        <>
          <Label className="mt-4">Tool calls · {lane.calls.length}</Label>
          <div className="mt-1.5 space-y-1.5">{lane.calls.map((c) => <Call key={c.id} call={c} />)}</div>
        </>
      )}
    </article>
  );
}
