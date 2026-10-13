import { Download, FileText, FileType2, Loader2 } from "lucide-react";
import { useState } from "react";
import type { RunView } from "../api";
import { download, fmtBytes } from "../download";
import { CiteLegend } from "./cite";
import Markdown from "./Markdown";
import { Panel } from "./Panel";
import { Button, Empty, NextLink, PageHeader } from "./ui";

type Format = "docx" | "md";

/** The brief as a document, every claim carrying the id it rests on. */
export default function BriefPage({ view, patientName, running, pending, onActions, onPatient, notify }: {
  view: RunView; patientName: string; running: boolean; pending: number; onActions: () => void; onPatient: () => void;
  notify: (text: string) => void;
}) {
  const v = view.verified;
  const state = v ? (v.passed ? `Verified · ${v.citations} citations, every id found in the database as this patient's user` : `Rejected by the gate · ${v.problems[0] ?? ""}`)
    : running ? "Being written…" : view.brief ? "Draft" : undefined;
  const [saving, setSaving] = useState<Format | null>(null);
  // The file is fetched, then saved: a missing run or a server error becomes a
  // message instead of a page of JSON, and a saved file says so.
  const save = async (format: Format) => {
    if (!view.id || saving) return;
    setSaving(format);
    try {
      const { name, bytes } = await download(`/api/runs/${view.id}/brief.${format}`, `pre-visit-brief-${view.patient ?? ""}.${format}`);
      notify(`Saved ${name} (${fmtBytes(bytes)}) to your downloads.`);
    } catch (err) {
      notify(`The brief could not be downloaded (${String(err).replace(/^Error: /, "")}). It is still on the server; reload the page and try again.`);
    } finally {
      setSaving(null);
    }
  };
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <PageHeader title="Pre-visit brief" subtitle={[patientName, state].filter(Boolean).join(" · ")}>
        {view.brief && view.id && (
          <>
            <Button busy={saving === "docx"} disabled={saving !== null} onClick={() => save("docx")} title="Save the brief as a Word document">
              {saving !== "docx" && <FileType2 className="size-3.5" />} Word
            </Button>
            <Button busy={saving === "md"} disabled={saving !== null} onClick={() => save("md")} title="Save the brief as Markdown">
              {saving !== "md" && <Download className="size-3.5" />} Markdown
            </Button>
          </>
        )}
        {view.brief && <NextLink onClick={onActions}>{pending ? `Review ${pending} proposed ${pending === 1 ? "action" : "actions"}` : "Proposed actions"}</NextLink>}
      </PageHeader>
      <Panel title={<><FileText className="size-3.5 text-oracle" /> Document</>}
        meta={view.status === "rejected" ? "shown for inspection; the gate rejected it, so it was not recorded in memory" : undefined}
        className="min-h-0 flex-1" bodyClassName="scroll-thin overflow-y-auto bg-sand/40 p-5">
        {view.brief ? (
          <article className="brief mx-auto max-w-[860px] rounded-lg border border-line bg-panel px-10 py-8">
            <Markdown>{view.brief}</Markdown>
            <CiteLegend className="mt-8 border-t border-line pt-3" />
          </article>
        ) : running ? (
          <Empty><span className="inline-flex items-center gap-2"><Loader2 className="size-4 animate-spin text-oracle" /> The agents are still working; the brief appears here when the gate accepts it.</span></Empty>
        ) : (
          <Empty action={<Button variant="accent" onClick={onPatient}>Ask for a brief</Button>}>No brief yet.</Empty>
        )}
      </Panel>
    </div>
  );
}
