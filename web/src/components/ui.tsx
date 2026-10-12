import clsx from "clsx";
import { ArrowRight, Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

/** One row at the top of a page: what this is, one line of context, its actions. */
export function PageHeader({ title, subtitle, children }: { title: ReactNode; subtitle?: ReactNode; children?: ReactNode }) {
  return (
    <div className="flex min-h-[44px] flex-wrap items-center gap-x-6 gap-y-2">
      <div className="min-w-0">
        <h1 className="text-lg font-semibold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="text-sm text-ink-3">{subtitle}</p>}
      </div>
      {children && <div className="ml-auto flex shrink-0 items-center gap-2">{children}</div>}
    </div>
  );
}

type Variant = "primary" | "accent" | "quiet" | "ghost";

export function Button({ variant = "quiet", busy = false, className, children, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; busy?: boolean }) {
  return (
    <button {...rest} disabled={rest.disabled || busy}
      className={clsx("inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-ink text-white hover:bg-ink-2",
        variant === "accent" && "bg-oracle text-white hover:bg-[#b23d2d]",
        variant === "quiet" && "border border-line bg-panel text-ink-2 hover:border-ink-3/50 hover:text-ink",
        variant === "ghost" && "text-ink-3 hover:bg-sand hover:text-ink",
        className)}>
      {busy && <Loader2 className="size-3.5 animate-spin" />}
      {children}
    </button>
  );
}

/** The way forward from a page, as a quiet link with an arrow. */
export function NextLink({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button onClick={onClick} className="inline-flex h-8 items-center gap-1 rounded-md px-2 text-sm font-medium text-oracle hover:bg-oracle-soft">
      {children} <ArrowRight className="size-3.5" />
    </button>
  );
}

export function Badge({ tone = "muted", children, className }: { tone?: "ok" | "warn" | "bad" | "muted" | "live"; children: ReactNode; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
      tone === "ok" && "bg-ok-soft text-ok", tone === "warn" && "bg-warn-soft text-warn", tone === "bad" && "bg-oracle-soft text-oracle",
      tone === "muted" && "bg-sand text-ink-3", tone === "live" && "bg-oracle text-white", className)}>
      {tone === "live" && <span className="live-dot size-1.5 rounded-full bg-white" />}
      {children}
    </span>
  );
}

export function Empty({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="grid h-full min-h-[240px] place-items-center rounded-lg border border-dashed border-line p-8 text-center">
      <div className="max-w-[420px] space-y-3 text-sm text-ink-3">
        <div>{children}</div>
        {action}
      </div>
    </div>
  );
}

/** Label above a block of content. */
export function Label({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("text-xs font-semibold uppercase tracking-[0.08em] text-ink-3", className)}>{children}</div>;
}
