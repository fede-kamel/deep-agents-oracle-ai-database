import { Download, FileText, FileType2, Loader2, ShieldCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const CITE = /(\[[A-Z][A-Za-z0-9:_#,\- ]+\])/g;

function tone(id: string) {
  if (id.startsWith("SQL")) return "bg-teal-soft text-teal border-teal/20";
  if (id.startsWith("SYN-")) return "bg-ochre-soft text-ochre border-ochre/20";
  if (id.startsWith("MEDQUAD")) return "bg-moss-soft text-moss border-moss/20";
  if (id.startsWith("PMID")) return "bg-violet-soft text-violet border-violet/20";
  return "bg-sand text-ink-3 border-line";
}

// Citations like [SQL:lab_result] or [SYN-X-NOTE-0005, MEDQUAD-02122] are
// rewritten to inline code before Markdown parsing (so brackets cannot be read
// as link references) and rendered back as coloured chips.
function withCitationCode(markdown: string): string {
  return markdown.replace(CITE, (m) => "`cite:" + m.slice(1, -1) + "`");
}

function Cite({ ids }: { ids: string }) {
  return (
    <>
      {ids.split(/,\s*/).map((id) => (
        <span key={id} className={`mx-0.5 inline-flex rounded border px-1 py-px align-[1px] font-mono text-[10px] leading-none ${tone(id)}`}>
          {id.replace(/#chunk-\d+$/, "")}
        </span>
      ))}
    </>
  );
}

export default function BriefViewer({ brief, runId, running, patientName, extra, wide }: { brief?: string; runId?: string; running: boolean; patientName?: string; extra?: import("react").ReactNode; wide?: boolean }) {
  return (
    <aside className={`flex h-full ${wide ? "w-full rounded-xl border" : "w-[min(560px,40vw)] shrink-0 border-l"} flex-col border-line bg-sand/60`}>
      <div className="flex items-center gap-2 border-b border-line bg-panel px-5 py-3">
        <FileText className="size-4 text-oracle" />
        <div className="text-[13px] font-semibold">Pre-visit brief</div>
        {patientName && <div className="text-[12px] text-ink-3">· {patientName}</div>}
        <div className="ml-auto flex gap-1.5">
          <a
            aria-disabled={!brief}
            href={brief && runId ? `/api/runs/${runId}/brief.docx` : undefined}
            className="flex items-center gap-1 rounded-md border border-line bg-panel px-2.5 py-1 text-[12px] text-ink-2 hover:border-ink-3/50 aria-disabled:pointer-events-none aria-disabled:opacity-40"
          >
            <FileType2 className="size-3.5" /> Word
          </a>
          <a
            aria-disabled={!brief}
            href={brief && runId ? `/api/runs/${runId}/brief.md` : undefined}
            className="flex items-center gap-1 rounded-md border border-line bg-panel px-2.5 py-1 text-[12px] text-ink-2 hover:border-ink-3/50 aria-disabled:pointer-events-none aria-disabled:opacity-40"
          >
            <Download className="size-3.5" /> Markdown
          </a>
          {extra}
        </div>
      </div>
      <div className="scroll-thin flex-1 overflow-y-auto p-5">
        {brief ? (
          <article className={`brief mx-auto ${wide ? "max-w-[860px]" : "max-w-[620px]"} rounded-xl border border-line bg-panel px-8 py-7 shadow-[0_24px_48px_-32px_rgb(22_21_19/.35)]`}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code: ({ children }) => {
                  const text = String(children);
                  return text.startsWith("cite:") ? <Cite ids={text.slice(5)} /> : <code>{children}</code>;
                },
              }}
            >
              {withCitationCode(brief)}
            </ReactMarkdown>
            <div className="mt-6 flex items-center gap-1.5 border-t border-line pt-3 text-[11px] text-ink-3">
              <ShieldCheck className="size-3.5 text-moss" /> Written inside an OpenShell sandbox from one patient's rows, under row-level security.
            </div>
          </article>
        ) : (
          <div className="grid h-full place-items-center text-center">
            <div className="max-w-[300px] text-[13px] text-ink-3">
              {running ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="size-4 animate-spin text-oracle" /> The agent is researching. The brief appears here when it is written.
                </span>
              ) : (
                "Pick a patient and run the brief. The document appears here with every claim linked to a row, a note, or a source."
              )}
            </div>
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 border-t border-line bg-panel px-5 py-2 text-[10.5px] text-ink-3">
        <Legend cls={tone("SQL")} label="SQL row" />
        <Legend cls={tone("SYN-")} label="chart note" />
        <Legend cls={tone("MEDQUAD")} label="NIH reference" />
        <Legend cls={tone("PMID")} label="PubMed" />
      </div>
    </aside>
  );
}

function Legend({ cls, label }: { cls: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className={`size-2.5 rounded-sm border ${cls}`} /> {label}
    </span>
  );
}
