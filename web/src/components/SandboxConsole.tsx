import clsx from "clsx";
import { SquareTerminal } from "lucide-react";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { agentMeta } from "../agents";
import { Panel } from "./Panel";

type Filter = "agents" | "network" | "all";

// The console carries ANSI colour codes from the run script; matching ESC is the point.
// oxlint-disable-next-line no-control-regex
const ANSI_TOKEN = /\x1b\[([0-9;]*)m/g;
const SGR: Record<string, string> = { "1": "font-semibold", "31": "text-[#ff6b6b]", "32": "text-[#7ee787]", "33": "text-[#e3b341]", "36": "text-[#79c0ff]" };

function renderLine(raw: string) {
  const parts: { text: string; cls: string }[] = [];
  let cls = "";
  let last = 0;
  for (const m of raw.matchAll(ANSI_TOKEN)) {
    if (m.index! > last) parts.push({ text: raw.slice(last, m.index), cls });
    cls = m[1] === "0" || m[1] === "" ? "" : m[1].split(";").map((c) => SGR[c] ?? "").join(" ");
    last = m.index! + m[0].length;
  }
  if (last < raw.length) parts.push({ text: raw.slice(last), cls });
  return parts.map((p, i) => <span key={i} className={p.cls}>{highlight(p.text)}</span>);
}

function highlight(text: string) {
  const tokens = text.split(/(ALLOWED|DENIED|NET:OPEN|HTTP:POST|HTTP:GET|CONFIG:[A-Z]+|\[policy:[^\]]+\]|\[reason:[^\]]+\])/);
  return tokens.map((t, i) => {
    if (t === "ALLOWED") return <span key={i} className="rounded bg-[#1f3d29] px-1 font-semibold text-[#7ee787]">ALLOWED</span>;
    if (t === "DENIED") return <span key={i} className="rounded bg-[#4a1f1f] px-1 font-semibold text-[#ff7b72]">DENIED</span>;
    if (/^(NET|HTTP):/.test(t)) return <span key={i} className="text-[#d2a8ff]">{t}</span>;
    if (/^CONFIG:/.test(t)) return <span key={i} className="text-[#79c0ff]">{t}</span>;
    if (t.startsWith("[policy:")) return <span key={i} className="text-[#e3b341]">{t}</span>;
    if (t.startsWith("[reason:")) return <span key={i} className="text-[#ff7b72]">{t}</span>;
    return t;
  });
}

// Gateway lines arrive as `[1791833071.222] [sandbox] [OCSF ] [ocsf] NET:OPEN [INFO] ALLOWED …`.
// Keep what a reader needs: the time of day, the decision, the process and
// the destination; drop the bookkeeping (mapping ids, engine tags, log level).
const GATEWAY = /^\[(\d{10})(?:\.\d+)?\] \[sandbox\] \[[A-Z ]+\] (?:\[ocsf\] )?/;
function tidy(line: string): string {
  const m = line.match(GATEWAY);
  if (!m) return line;
  const clock = new Date(Number(m[1]) * 1000).toLocaleTimeString([], { hour12: false });
  const rest = line
    .slice(m[0].length)
    .replace(/^\[openshell_[a-z_:]+\] /, "")
    .replace(/ \[(INFO|MED|LOW|HIGH|WARN)\]/, "")
    .replace(/ mapping_id=[0-9a-f-]+/, "")
    .replace(/ engine:[a-z0-9]+\]/, "]")
    .replace(/http:\/\/([^/\s]+):443\//, "https://$1/")
    .replace(/\/usr\/local\/bin\/(python[0-9.]+)\(\d+\)/, "$1");
  return `${clock}  ${rest}`;
}

/** An agent's step. Long ones (a delegation, a thought) show three rows and
 * open in full on a click; the text itself is never cut. */
function AgentLine({ line }: { line: string }) {
  const [open, setOpen] = useState(false);
  const m = line.match(/^\[agent:([a-z-]+)\] (.*)$/);
  if (!m) return <>{line}</>;
  const [, who, rest] = m;
  const meta = agentMeta(who);
  const isResult = rest.startsWith("  →") || rest.startsWith("←");
  const long = rest.length > 320;
  return (
    <div className={clsx("flex items-start gap-2", long && "cursor-pointer")} onClick={long ? () => setOpen((o) => !o) : undefined} title={long && !open ? "Click to show the whole step" : undefined}>
      <span className="mt-[3px] shrink-0 rounded px-1.5 py-px text-[10.5px] font-semibold leading-[1.4]" style={{ color: meta.tint, background: meta.color }}>{who}</span>
      <span className={clsx("min-w-0 whitespace-pre-wrap break-words", long && !open && "line-clamp-3",
        isResult ? "text-[#8b949e]" : rest.startsWith("SQL") ? "text-[#7fd1e0]" : rest.startsWith("thinking") ? "italic text-[#a5b4cf]" : "text-[#e6edf3]")}>{rest}</span>
    </div>
  );
}

function classify(line: string): Filter | "lifecycle" {
  if (line.startsWith("[agent:")) return "agents";
  if (/NET:|HTTP:|Policy DNS|DENIED|ALLOWED/.test(line)) return "network";
  return "lifecycle";
}

/** Every agent step, written from inside the sandbox, next to the network
 * decision the gateway made for it. One switch: agents, network, everything. */
export const SandboxConsole = memo(function SandboxConsole({ lines, live }: { lines: string[]; live: boolean }) {
  const [filter, setFilter] = useState<Filter>("agents");
  const box = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  const shown = useMemo(() => (filter === "all" ? lines : lines.filter((l) => classify(l) === filter)), [lines, filter]);
  const counts = useMemo(() => ({
    agents: lines.filter((l) => l.startsWith("[agent:")).length,
    allowed: lines.filter((l) => /ALLOWED/.test(l)).length,
    denied: lines.filter((l) => /DENIED/.test(l)).length,
  }), [lines]);

  useEffect(() => {
    const el = box.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [shown.length]);

  return (
    <Panel dark className="h-full"
      title={<><SquareTerminal className="size-3.5 text-[#7ee787]" /> Sandbox console {live && <span className="live-dot ml-1 size-1.5 rounded-full bg-oracle" />}</>}
      meta={<span>{counts.agents} agent steps · <span className="text-[#7ee787]">{counts.allowed} allowed</span> · <span className={counts.denied ? "text-[#ff7b72]" : undefined}>{counts.denied} denied</span></span>}
      actions={
        <div className="flex overflow-hidden rounded-md border border-[#30363d] font-mono text-xs">
          {(["agents", "network", "all"] as Filter[]).map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={clsx("px-2.5 py-1 capitalize", filter === f ? "bg-[#30363d] text-white" : "text-[#8b949e] hover:text-white")}>{f}</button>
          ))}
        </div>
      }
      bodyClassName="flex flex-col">
      <div ref={box}
        onScroll={(e) => { const el = e.currentTarget; stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40; }}
        className="scroll-term min-h-0 flex-1 overflow-y-auto px-4 py-3 font-mono text-sm leading-[1.7] text-[#c9d1d9]">
        {shown.length === 0 && (
          <div className="text-[#6e7681]">{live ? "Waiting for the sandbox…" : "Nothing in this view yet."}</div>
        )}
        {shown.map((l, i) => (
          <div key={i} className={clsx("break-all", l.startsWith("[agent:") ? "border-l-2 border-[#3b4252] pl-2" : "whitespace-pre-wrap")}>
            {l.startsWith("[agent:") ? <AgentLine line={l} /> : renderLine(tidy(l.replace(/^\[openshell\] /, "")))}
          </div>
        ))}
      </div>
    </Panel>
  );
});
