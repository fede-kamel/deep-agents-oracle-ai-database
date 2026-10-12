import { Brain } from "lucide-react";
import type { Patient, RunView } from "../api";
import { Panel } from "./Panel";
import { Prose } from "./Prose";
import { Empty, NextLink, PageHeader } from "./ui";

/** What the system recorded for this patient: each accepted brief, each decision. */
export function MemoryPage({ patient, memory, entries, checkpoints, onPatient }: {
  patient: Patient; memory?: string; entries: number; checkpoints?: RunView["checkpoints"]; onPatient: () => void;
}) {
  const subtitle = [
    patient.display_name,
    `${entries} ${entries === 1 ? "entry" : "entries"} in OracleStore`,
    checkpoints ? `${checkpoints.count} checkpoints for the last run in OracleSaver` : null,
  ].filter(Boolean).join(" · ");
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <PageHeader title="What the agent remembers" subtitle={subtitle}>
        <NextLink onClick={onPatient}>Run again with this memory</NextLink>
      </PageHeader>
      <Panel title={<><Brain className="size-3.5 text-teal" /> /memories/patient-history.md</>}
        meta={`written by the system, not the model · in ${patient.db_user}'s own schema · read-only to the agent`}
        className="min-h-0 flex-1" bodyClassName="scroll-thin overflow-y-auto p-6">
        {memory ? (
          <Prose className="mx-auto max-w-[860px]">{memory}</Prose>
        ) : (
          <Empty>Nothing yet. Run a brief and decide on its actions; both are recorded here, and the next brief starts from them.</Empty>
        )}
      </Panel>
    </div>
  );
}
