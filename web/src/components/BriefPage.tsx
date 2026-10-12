import { Download, FileText, FileType2, Loader2 } from "lucide-react";
import type { RunView } from "../api";
import { CiteLegend } from "./cite";
import Markdown from "./Markdown";
import { Panel } from "./Panel";
import { Button, Empty, NextLink, PageHeader } from "./ui";

/** The brief as a document, every claim carrying the id it rests on. */
export default function BriefPage({ view, patientName, running, pending, onActions, onPatient }: {
  view: RunView; patientName: string; running: boolean; pending: number; onActions: () => void; onPatient: () => void;
}) {
  const v = view.verified;
  const state = v ? (v.passed ? `Verified · ${v.citations} citations, every id found in the database as this patient's user` : `Rejected by the gate · ${v.problems[0] ?? ""}`)
    : running ? "Being written…" : view.brief ? "Draft" : undefined;
  const link = "inline-flex h-8 items-center gap-1.5 rounded-md border border-line bg-panel px-3 text-sm font-medium text-ink-2 hover:border-ink-3/50 hover:text-ink";
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <PageHeader title="Pre-visit brief" subtitle={[patientName, state].filter(Boolean).join(" · ")}>
        {view.brief && view.id && (
          <>
            <a href={`/api/runs/${view.id}/brief.docx`} className={link}><FileType2 className="size-3.5" /> Word</a>
            <a href={`/api/runs/${view.id}/brief.md`} className={link}><Download className="size-3.5" /> Markdown</a>
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
