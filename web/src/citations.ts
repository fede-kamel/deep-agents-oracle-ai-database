/** A citation as the agent writes it: [SQL:lab_result], [SYN-X-NOTE-0005],
 * [MEDQUAD-02122#chunk-1], [PMID-20977579], alone or comma-separated. */
export const CITE = /(\[[A-Z][A-Za-z0-9:_#,\- ]+\])/g;

export function citeTone(id: string): string {
  if (id.startsWith("SQL")) return "border-teal/25 bg-teal-soft text-teal";
  if (id.startsWith("SYN-")) return "border-ochre/25 bg-ochre-soft text-ochre";
  if (id.startsWith("MEDQUAD")) return "border-moss/25 bg-moss-soft text-moss";
  if (id.startsWith("PMID")) return "border-violet/25 bg-violet-soft text-violet";
  return "border-line bg-sand text-ink-3";
}
