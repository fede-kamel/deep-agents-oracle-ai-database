import clsx from "clsx";
import { Suspense } from "react";
import { lazyPage } from "../lazy";

const Markdown = lazyPage(() => import("./Markdown"));

/** Markdown text in full, styled as prose; plain text until the renderer loads. */
export function Prose({ children, className }: { children: string; className?: string }) {
  return (
    <Suspense fallback={<pre className={clsx("prose whitespace-pre-wrap font-sans", className)}>{children}</pre>}>
      <Markdown className={clsx("prose", className)}>{children}</Markdown>
    </Suspense>
  );
}
