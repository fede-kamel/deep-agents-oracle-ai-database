import clsx from "clsx";
import { Network, ShieldCheck, ShieldX, SquareTerminal } from "lucide-react";
import { memo, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

type Filter = "all" | "agents" | "network" | "lifecycle";

const ANSI_TOKEN = /\x1b\[([0-9;]*)m/g;
const SGR: Record<string, string> = {
  "1": "font-semibold",
  "31": "text-[#ff6b6b]",
  "32": "text-[#7ee787]",
  "33": "text-[#e3b341]",
  "36": "text-[#79c0ff]",
};

// Split a line into spans: ANSI colours from the script, then highlights for
// the gateway's network decisions.
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

const AGENT_TAG: Record<string, string> = {
  lead: "bg-[#2d3a5c] text-[#c8d3f5]",
  "chart-analyst": "bg-[#123c45] text-[#7fd1e0]",
  "guideline-researcher": "bg-[#25381c] text-[#a6e08a]",
  "evidence-researcher": "bg-[#33244d] text-[#d2a8ff]",
  "care-coordinator": "bg-[#4a3511] text-[#f2c46d]",
  runner: "bg-[#1f3d29] text-[#7ee787]",
};

function AgentLine({ line }: { line: string }) {
  const m = line.match(/^\[agent:([a-z-]+)\] (.*)$/);
  if (!m) return <>{line}</>;
  const [, who, rest] = m;
  const isResult = rest.startsWith("  →") || rest.startsWith("←");
  return (
    <>
      <span className={clsx("mr-2 rounded px-1.5 py-px text-[10.5px] font-semibold", AGENT_TAG[who] ?? "bg-[#30363d] text-white")}>{who}</span>
      <span className={clsx(isResult ? "text-[#8b949e]" : rest.startsWith("SQL") ? "text-[#7fd1e0]" : rest.startsWith("thinking") ? "italic text-[#a5b4cf]" : "text-[#e6edf3]")}>{rest}</span>
    </>
  );
}

function classify(line: string): Filter | "noise" {
  if (line.startsWith("[agent:")) return "agents";
  if (/GetSandbox|Settings poll|relay (stream|opened|closed)|supervisor session|ssh relay|metadata\.id index|error-help\/db\/ora-41900/.test(line)) return "noise";
  if (/NET:|HTTP:|Policy DNS|DENIED|ALLOWED/.test(line)) return "network";
  return "lifecycle";
}

export const SandboxConsole = memo(function SandboxConsole({ lines, live, extra, defaultFilter = "all" }: { lines: string[]; live: boolean; extra?: ReactNode; defaultFilter?: Filter }) {
  const [filter, setFilter] = useState<Filter>(defaultFilter);
  const [showNoise, setShowNoise] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  const shown = useMemo(
    () =>
      lines.filter((l) => {
        const c = classify(l);
        if (c === "noise") return showNoise;
        return filter === "all" || c === filter;
      }),
    [lines, filter, showNoise],
  );
  const allowed = useMemo(() => lines.filter((l) => /ALLOWED/.test(l)).length, [lines]);
  const agentLines = useMemo(() => lines.filter((l) => l.startsWith("[agent:")).length, [lines]);
  const denied = useMemo(() => lines.filter((l) => /DENIED/.test(l)).length, [lines]);

  useEffect(() => {
    const el = box.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [shown.length]);

  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-[#2a2a2a] bg-term shadow-[0_20px_40px_-24px_rgb(0_0_0/.55)]">
      <header className="flex items-center gap-3 border-b border-[#262626] bg-term-2 px-3.5 py-2">
        <div className="flex gap-1.5">
          <span className="size-2.5 rounded-full bg-[#ff5f57]" />
          <span className="size-2.5 rounded-full bg-[#febc2e]" />
          <span className="size-2.5 rounded-full bg-[#28c840]" />
        </div>
        <div className="flex shrink-0 items-center gap-1.5 whitespace-nowrap font-mono text-[11.5px] text-[#c9d1d9]">
          <SquareTerminal className="size-3.5 text-[#7ee787]" /> OpenShell sandbox console
          {live && <span className="live-dot ml-1 size-1.5 rounded-full bg-oracle" />}
        </div>
        <div className="ml-auto flex items-center gap-1 whitespace-nowrap font-mono text-[11px]">
          <span className="flex items-center gap-1 rounded-md bg-[#2d3a5c] px-2 py-0.5 text-[#c8d3f5]">{agentLines} agent steps</span>
          <span className="flex items-center gap-1 rounded-md bg-[#1f3d29] px-2 py-0.5 text-[#7ee787]">
            <ShieldCheck className="size-3" /> {allowed} allowed
          </span>
          <span className={clsx("flex items-center gap-1 rounded-md px-2 py-0.5", denied ? "bg-[#4a1f1f] text-[#ff7b72]" : "bg-[#262626] text-[#8b949e]")}>
            <ShieldX className="size-3" /> {denied} denied
          </span>
          <div className="ml-2 flex overflow-hidden rounded-md border border-[#30363d]">
            {(["all", "agents", "network", "lifecycle"] as Filter[]).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={clsx("px-2 py-0.5 capitalize", filter === f ? "bg-[#30363d] text-white" : "text-[#8b949e] hover:text-white")}
              >
                {f === "network" ? <span className="flex items-center gap-1"><Network className="size-3" />network</span> : f}
              </button>
            ))}
          </div>
          <label className="ml-2 flex cursor-pointer items-center gap-1 text-[#8b949e]">
            <input type="checkbox" className="accent-[#7ee787]" checked={showNoise} onChange={(e) => setShowNoise(e.target.checked)} />
            gRPC
          </label>
          {extra && <div className="ml-2">{extra}</div>}
        </div>
      </header>
      <div
        ref={box}
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
        }}
        className="scroll-term min-h-0 flex-1 overflow-y-auto px-4 py-3 font-mono text-[11.5px] leading-[1.6] text-[#c9d1d9]"
      >
        {shown.length === 0 && (
          <div className="text-[#6e7681]">
            {live ? "waiting for the sandbox…" : "Run a brief to watch the sandbox: every agent step from inside it, next to each network decision the gateway makes."}
          </div>
        )}
        {shown.map((l, i) => (
          <div key={i} className={clsx("whitespace-pre-wrap break-all", l.startsWith("[agent:") && "border-l-2 border-[#3b4252] pl-2")}>
            {l.startsWith("[agent:") ? <AgentLine line={l} /> : renderLine(l.replace(/^\[openshell\] /, ""))}
          </div>
        ))}
      </div>
    </section>
  );
});
