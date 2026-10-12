import clsx from "clsx";
import { CITE, citeTone } from "../citations";

export function Cite({ ids }: { ids: string }) {
  return (
    <>
      {ids.split(/,\s*/).filter(Boolean).map((id, i) => (
        <span key={`${id}-${i}`} className={clsx("mx-0.5 inline-flex rounded border px-1 py-px align-[1px] font-mono text-[10px] leading-none", citeTone(id))}>
          {id.replace(/#chunk-\d+$/, "")}
        </span>
      ))}
    </>
  );
}

const idsIn = (text: string) => [...new Set([...text.matchAll(CITE)].flatMap((m) => m[1].slice(1, -1).split(/,\s*/)))];

/** A string of citations, as stored with a care action, rendered as chips;
 * `except` drops the ones already shown inline. */
export function Citations({ text, except = "", className }: { text: string; except?: string; className?: string }) {
  const shown = new Set(idsIn(except));
  const ids = idsIn(text).filter((id) => !shown.has(id));
  if (ids.length === 0) return null;
  return <span className={clsx("inline-flex flex-wrap gap-y-1", className)}>{ids.map((id) => <Cite key={id} ids={id} />)}</span>;
}

/** Plain text with its [citations] turned into chips. */
export function Cited({ text, className }: { text: string; className?: string }) {
  const parts = text.split(CITE);
  return <span className={className}>{parts.map((p, i) => (i % 2 ? <Cite key={i} ids={p.slice(1, -1)} /> : p))}</span>;
}

export function CiteLegend({ className }: { className?: string }) {
  return (
    <div className={clsx("flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink-3", className)}>
      {[["SQL", "table row"], ["SYN-", "chart note"], ["MEDQUAD", "NIH reference"], ["PMID", "PubMed abstract"]].map(([k, label]) => (
        <span key={k} className="flex items-center gap-1"><span className={clsx("size-2.5 rounded-sm border", citeTone(k))} /> {label}</span>
      ))}
    </div>
  );
}
