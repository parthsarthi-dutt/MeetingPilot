import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

// The "case file" module: generously padded bordered card, optional
// monospace label at the top (like a case-file tag).
export function CaseCard({
  label,
  title,
  action,
  children,
  className,
  as: Tag = "section",
}: {
  label?: string;
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  as?: keyof HTMLElementTagNameMap;
}) {
  const Comp = Tag as "section";
  return (
    <Comp
      className={cn(
        "rounded-md border border-rule bg-card text-card-foreground",
        "shadow-[0_1px_0_var(--rule)]",
        className,
      )}
    >
      {(label || title || action) && (
        <header className="flex items-start justify-between gap-4 border-b border-rule px-5 py-4 sm:px-6">
          <div className="min-w-0">
            {label && (
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-ink">
                {label}
              </div>
            )}
            {title && (
              <h3 className="mt-1 font-display text-xl leading-tight text-foreground sm:text-2xl">
                {title}
              </h3>
            )}
          </div>
          {action}
        </header>
      )}
      <div className="px-5 py-5 sm:px-6 sm:py-6">{children}</div>
    </Comp>
  );
}
