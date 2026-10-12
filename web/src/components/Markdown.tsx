import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CITE } from "../citations";
import { Cite } from "./cite";

/** Markdown with citations rendered as chips. Citations are rewritten to inline
 * code before parsing, so their brackets cannot be read as link references.
 * Heavy (react-markdown): load through Prose, which splits it into its own chunk. */
export default function Markdown({ children, className }: { children: string; className?: string }) {
  const text = children.replace(CITE, (m) => "`cite:" + m.slice(1, -1) + "`");
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code: ({ children }) => {
            const t = String(children);
            return t.startsWith("cite:") ? <Cite ids={t.slice(5)} /> : <code>{children}</code>;
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
