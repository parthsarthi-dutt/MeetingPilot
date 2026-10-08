import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { useReveal } from "@/hooks/use-reveal";

/**
 * Reveal — wrap any block to fade + slide up as it enters the viewport.
 * Uses IntersectionObserver, respects prefers-reduced-motion.
 */
export function Reveal({
  children,
  className,
  delayMs = 0,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  delayMs?: number;
  as?: keyof HTMLElementTagNameMap;
}) {
  const { ref, visible } = useReveal<HTMLDivElement>();
  const Comp = Tag as "div";
  return (
    <Comp
      ref={ref as never}
      style={{ transitionDelay: `${delayMs}ms` }}
      className={cn(
        "transition-all duration-700 ease-out will-change-transform",
        visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0",
        className,
      )}
    >
      {children}
    </Comp>
  );
}
