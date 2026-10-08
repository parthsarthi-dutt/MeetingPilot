import { cn } from "@/lib/utils";
import type { MeetingStatus, WorkflowNodeStatus } from "@/lib/api/types";

// Consistent status → color mapping per the brief.
// - not_processed = neutral grey
// - queued/processing = slate
// - processed/ready = signal (amber)
// - done = success (sage)
// - rescheduled = slate outline
// - failed = alert (brick)
type AnyStatus = MeetingStatus | WorkflowNodeStatus | "ready";

const LABELS: Record<AnyStatus, string> = {
  not_processed: "Not processed",
  queued: "Queued",
  processing: "Processing",
  processed: "Ready",
  ready: "Ready",
  done: "Done",
  rescheduled: "Rescheduled",
  failed: "Failed",
  started: "In progress",
  success: "Done",
  skipped: "Skipped",
  retried: "Retried",
};

const STYLES: Record<AnyStatus, string> = {
  not_processed: "bg-muted text-muted-ink border-rule",
  not_started: "bg-muted text-muted-ink border-rule",
  queued: "bg-slate/10 text-slate border-slate/25",
  processing: "bg-slate/10 text-slate border-slate/25",
  started: "bg-slate/10 text-slate border-slate/25",
  retried: "bg-slate/10 text-slate border-slate/25",
  processed: "bg-signal/15 text-[color:var(--ink)] border-signal/40",
  ready: "bg-signal/15 text-[color:var(--ink)] border-signal/40",
  done: "bg-success/12 text-success border-success/35",
  success: "bg-success/12 text-success border-success/35",
  rescheduled: "bg-transparent text-slate border-slate/45 border-dashed",
  failed: "bg-alert/10 text-alert border-alert/40",
  skipped: "bg-muted text-muted-ink border-rule",
} as Record<string, string>;

export function StatusBadge({
  status,
  className,
  size = "sm",
}: {
  status: AnyStatus | string;
  className?: string;
  size?: "sm" | "md";
}) {
  const key = (status as AnyStatus) in STYLES ? (status as AnyStatus) : "not_processed";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-mono uppercase tracking-wide",
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
        STYLES[key],
        className,
      )}
    >
      <span
        aria-hidden
        className={cn(
          "inline-block h-1.5 w-1.5 rounded-full",
          key === "processed" || key === "ready" ? "bg-signal" :
          key === "done" || key === "success" ? "bg-success" :
          key === "failed" ? "bg-alert" :
          key === "processing" || key === "queued" || key === "started" ? "bg-slate" :
          "bg-muted-ink/60",
        )}
      />
      {LABELS[key] ?? String(status)}
    </span>
  );
}
