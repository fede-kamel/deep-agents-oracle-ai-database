import clsx from "clsx";
import { motion } from "framer-motion";
import { Activity, Database, HeartPulse, Pill, Stethoscope, Wind } from "lucide-react";
import type { Patient } from "../api";

const ICONS = { X: Activity, Y: HeartPulse, Z: Wind } as const;
const TONES = {
  X: "text-teal bg-teal-soft",
  Y: "text-oracle bg-oracle-soft",
  Z: "text-violet bg-violet-soft",
} as const;
// The two numbers a clinician would look at first, per situation.
const KEY_LABS: Record<Patient["key"], string[]> = {
  X: ["eGFR", "HbA1c", "UACR"],
  Y: ["BNP", "Potassium", "eGFR"],
  Z: ["FEV1", "Sodium", "Eosinophils"],
};

export function PatientRail({
  patients,
  selected,
  onSelect,
  disabled,
}: {
  patients: Patient[];
  selected?: string;
  onSelect: (p: Patient) => void;
  disabled: boolean;
}) {
  return (
    <aside className="flex h-full w-[300px] shrink-0 flex-col border-r border-line bg-panel">
      <div className="px-5 pt-5 pb-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-3">Patients</div>
        <p className="mt-1 text-[12.5px] leading-snug text-ink-3">
          Synthetic charts in Oracle AI Database. Pick a situation to brief.
        </p>
      </div>
      <div className="scroll-thin flex-1 space-y-3 overflow-y-auto px-4 pb-4">
        {patients.map((p, i) => {
          const Icon = ICONS[p.key];
          const active = p.key === selected;
          const labs = (p.latest_labs ?? []).filter((l) => KEY_LABS[p.key].includes(l.test));
          return (
            <motion.button
              key={p.key}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              disabled={disabled}
              onClick={() => onSelect(p)}
              className={clsx(
                "group w-full rounded-xl border p-4 text-left transition",
                active
                  ? "border-oracle/60 bg-oracle-soft/40 shadow-[0_1px_0_#fff_inset,0_8px_24px_-12px_rgb(199_70_52/.35)]"
                  : "border-line bg-panel hover:border-ink-3/40 hover:shadow-sm",
                disabled && !active && "opacity-60",
              )}
            >
              <div className="flex items-start gap-3">
                <div className={clsx("grid size-9 shrink-0 place-items-center rounded-lg", TONES[p.key])}>
                  <Icon className="size-[18px]" strokeWidth={2.2} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[15px] font-semibold">{p.display_name}</span>
                    <span className="rounded bg-sand px-1.5 py-0.5 font-mono text-[10px] text-ink-3">{p.id}</span>
                  </div>
                  <div className="text-[12px] text-ink-3">
                    {p.age} · {p.sex} · {p.alias.replace(" (synthetic)", "")}
                  </div>
                </div>
              </div>
              <div className="mt-3 text-[13px] font-medium leading-snug text-ink-2">{p.situation}</div>
              <div className="mt-1 flex items-center gap-1.5 text-[11.5px] text-ink-3">
                <Stethoscope className="size-3.5" /> {p.visit_reason}
              </div>
              {labs.length > 0 && (
                <div className="mt-3 grid grid-cols-3 gap-1.5">
                  {labs.map((l) => (
                    <div key={l.test} className="rounded-md bg-sand/80 px-2 py-1.5">
                      <div className="text-[10px] uppercase tracking-wide text-ink-3">{l.test}</div>
                      <div className="font-mono text-[13px] font-semibold text-ink">
                        {Number.isInteger(l.value) ? l.value : l.value.toFixed(1)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-3 flex items-center justify-between border-t border-line/70 pt-2.5 text-[11px] text-ink-3">
                <span className="flex items-center gap-1">
                  <Pill className="size-3" /> {p.active_medications ?? "–"} meds · {p.notes ?? "–"} notes
                </span>
                <span className="flex items-center gap-1 font-mono" title="Read through this patient's own database user">
                  <Database className="size-3" /> {p.db_user}
                </span>
              </div>
              {p.visible_patients !== undefined && (
                <div className="mt-1.5 text-[10.5px] text-moss">
                  row-level security: this user sees {p.visible_patients} patient
                </div>
              )}
              {p.error && <div className="mt-2 text-[11px] text-oracle">{p.error}</div>}
            </motion.button>
          );
        })}
      </div>
      <div className="border-t border-line px-5 py-3 text-[11px] leading-snug text-ink-3">
        Every record is invented. A database constraint rejects any patient id without the{" "}
        <span className="font-mono">SYN-</span> prefix.
      </div>
    </aside>
  );
}
