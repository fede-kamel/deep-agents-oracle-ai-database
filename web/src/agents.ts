import { BookOpenText, Bot, ClipboardCheck, FlaskConical, ShieldAlert, ShieldCheck, TableProperties, type LucideIcon } from "lucide-react";

/** One entry per agent: how every screen names and colours it. `tint` is the
 * text colour on the dark console; `color` and `soft` work on light panels. */
export type AgentMeta = { label: string; role: string; icon: LucideIcon; color: string; soft: string; tint: string };

export const AGENTS: Record<string, AgentMeta> = {
  lead: { label: "Lead", role: "plans, delegates, writes the brief", icon: Bot, color: "#2d3a5c", soft: "#e8eaf0", tint: "#c8d3f5" },
  "chart-analyst": { label: "Chart analyst", role: "SQL and the patient's notes", icon: TableProperties, color: "#2c5967", soft: "#e6eff1", tint: "#7fd1e0" },
  "guideline-researcher": { label: "Guideline researcher", role: "NIH reference (MedQuAD)", icon: BookOpenText, color: "#5f7d4f", soft: "#edf3e8", tint: "#a6e08a" },
  "evidence-researcher": { label: "Evidence researcher", role: "PubMed abstracts", icon: FlaskConical, color: "#6b4fa0", soft: "#f0ecf7", tint: "#d2a8ff" },
  "care-coordinator": { label: "Care coordinator", role: "proposes actions, escalates", icon: ClipboardCheck, color: "#a8701a", soft: "#fbf3e2", tint: "#f2c46d" },
  "medication-safety": { label: "Medication safety", role: "the only agent that may propose a medication change", icon: ShieldAlert, color: "#c74634", soft: "#fbeae7", tint: "#ff9b8a" },
  runner: { label: "Runner", role: "gate, memory, checkpoints", icon: ShieldCheck, color: "#3f7d4f", soft: "#e9f2eb", tint: "#7ee787" },
};

const UNKNOWN: AgentMeta = { label: "agent", role: "", icon: Bot, color: "#6f6964", soft: "#f2f0ee", tint: "#d0cbc6" };

export const agentMeta = (name?: string): AgentMeta => (name && AGENTS[name]) || { ...UNKNOWN, label: name ?? "agent" };
