import { Button } from "./ui";

/** Reset asks once, says exactly what goes and what stays. */
export function ConfirmReset({ busy, runInProgress, onCancel, onConfirm }: { busy: boolean; runInProgress: boolean; onCancel: () => void; onConfirm: () => void }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/30" onClick={() => !busy && onCancel()}>
      <div className="w-[520px] rounded-lg border border-line bg-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold">Clear everything and start again?</h2>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink-2">
          <li>every proposed and decided care action, and its audit trail</li>
          <li>the lab orders, portal messages and appointment requests they created</li>
          <li>each patient's memory (OracleStore) and the agents' checkpoints (OracleSaver)</li>
          <li>physician orders from approved medication changes (the medications return to active)</li>
          <li>every run this application remembers, stopping any run in progress</li>
        </ul>
        {runInProgress && <p className="mt-3 rounded-md bg-warn-soft px-3 py-2 text-sm text-ink-2">A run is in progress: it will be stopped and its sandbox deleted first.</p>}
        <p className="mt-3 text-sm text-ink-3">The synthetic charts, the reference stores and every configuration stay as they are.</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button disabled={busy} onClick={onCancel}>Cancel</Button>
          <Button variant="accent" busy={busy} onClick={onConfirm}>{busy ? "Resetting…" : "Reset the demo"}</Button>
        </div>
      </div>
    </div>
  );
}

export function Toast({ text }: { text: string }) {
  return <div className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-lg bg-ink px-4 py-2.5 text-sm text-white shadow-xl">{text}</div>;
}
