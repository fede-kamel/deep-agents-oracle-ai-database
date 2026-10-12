import { BookOpenText, ClipboardCheck, Database, FlaskConical, ShieldAlert, TableProperties } from "lucide-react";

// One entry per specialist: its tab, its lane card, its colours.
export const LANES: Record<string, { label: string; store: string; icon: typeof Database; tone: string; ring: string }> = {
  "chart-analyst": { label: "Chart analyst", store: "SQL + patient notes", icon: TableProperties, tone: "text-teal bg-teal-soft", ring: "border-teal/40" },
  "guideline-researcher": { label: "Guideline researcher", store: "MedQuAD reference", icon: BookOpenText, tone: "text-moss bg-moss-soft", ring: "border-moss/40" },
  "evidence-researcher": { label: "Evidence researcher", store: "PubMed abstracts", icon: FlaskConical, tone: "text-violet bg-violet-soft", ring: "border-violet/40" },
  "care-coordinator": { label: "Care coordinator", store: "proposes actions, escalates", icon: ClipboardCheck, tone: "text-ochre bg-ochre-soft", ring: "border-ochre/40" },
  "medication-safety": { label: "Medication safety", store: "only agent allowed med changes", icon: ShieldAlert, tone: "text-oracle bg-oracle-soft", ring: "border-oracle/40" },
};
