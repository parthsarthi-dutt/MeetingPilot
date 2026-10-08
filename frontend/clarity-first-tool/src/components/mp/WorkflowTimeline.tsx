import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { WorkflowLogEntry, WorkflowNodeStatus } from "@/lib/api/types";

// The signature component. Vertical case-file trail — thin connecting line,
// status-colored nodes, IBM Plex Mono timestamps, expandable detail per step.
// Nodes reveal in sequence when the timeline mounts / new entries arrive.

const NODE_COLOR: Record<WorkflowNodeStatus, string> = {
  started: "bg-slate ring-slate/20 mp-node-pulse",
  success: "bg-success ring-success/20",
  skipped: "bg-muted-ink ring-muted-ink/20",
  failed: "bg-alert ring-alert/20",
  retried: "bg-slate ring-slate/20",
};

const NODE_TEXT: Record<WorkflowNodeStatus, string> = {
  started: "text-slate",
  success: "text-success",
  skipped: "text-muted-ink",
  failed: "text-alert",
  retried: "text-slate",
};

function formatTime(iso?: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

function formatDuration(a: string, b?: string) {
  if (!b) return "…";
  const ms = new Date(b).getTime() - new Date(a).getTime();
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function WorkflowTimeline({
  entries,
  compact = false,
  className,
}: {
  entries: WorkflowLogEntry[];
  compact?: boolean;
  className?: string;
}) {
  // Sequenced reveal: staggered per index.
  const [revealed, setRevealed] = useState(0);
  useEffect(() => {
    setRevealed(0);
    const timers: ReturnType<typeof setTimeout>[] = [];
    entries.forEach((_, i) => {
      timers.push(setTimeout(() => setRevealed((r) => Math.max(r, i + 1)), 140 * i));
    });
    return () => timers.forEach(clearTimeout);
  }, [entries]);

  return (
    <ol
      className={cn("relative", className)}
      aria-label="Workflow timeline"
    >
      {/* Vertical trail line */}
      <span
        aria-hidden
        className="absolute left-[11px] top-2 bottom-2 w-px bg-rule"
      />
      {entries.map((e, i) => (
        <TimelineNode
          key={`${e.node_name}-${e.started_at}`}
          entry={e}
          isLast={i === entries.length - 1}
          visible={i < revealed}
          compact={compact}
        />
      ))}
    </ol>
  );
}

function TimelineNode({
  entry,
  isLast,
  visible,
  compact,
}: {
  entry: WorkflowLogEntry;
  isLast: boolean;
  visible: boolean;
  compact: boolean;
}) {
  const [open, setOpen] = useState(false);
  const hasMetadata = entry.metadata && Object.keys(entry.metadata).length > 0;

  return (
    <li
      className={cn(
        "relative pl-9",
        !isLast && (compact ? "pb-4" : "pb-6"),
        visible ? "mp-reveal opacity-100" : "opacity-0",
      )}
    >
      {/* Node */}
      <span
        aria-hidden
        className={cn(
          "absolute left-1.5 top-1.5 h-3 w-3 rounded-full ring-4 ring-offset-0",
          NODE_COLOR[entry.status],
        )}
      />
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
          {formatTime(entry.started_at)}
        </span>
        <span className={cn("font-mono text-xs font-medium", NODE_TEXT[entry.status])}>
          {entry.node_name}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">
          · {entry.status} · {formatDuration(entry.started_at, entry.completed_at)}
        </span>
      </div>
      <p className={cn("mt-1 text-sm text-foreground/85", compact && "text-[13px]")}>
        {entry.message}
      </p>
      {hasMetadata && !compact && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="mt-2 inline-flex items-center gap-1 rounded font-mono text-[11px] uppercase tracking-wider text-muted-ink hover:text-foreground focus-visible:text-foreground"
        >
          {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          {open ? "Hide detail" : "Show detail"}
        </button>
      )}
      {open && hasMetadata && (
        <pre className="mt-2 overflow-x-auto rounded border border-rule bg-muted/40 px-3 py-2 font-mono text-[11px] leading-relaxed text-foreground/80">
{JSON.stringify(entry.metadata, null, 2)}
        </pre>
      )}
    </li>
  );
}
