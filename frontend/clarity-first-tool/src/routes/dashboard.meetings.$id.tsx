import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Mail,
  RefreshCw,
  Send,
  Sparkles,
} from "lucide-react";
import { AppShell } from "@/components/mp/AppShell";
import { CaseCard } from "@/components/mp/CaseCard";
import { StatusBadge } from "@/components/mp/StatusBadge";
import { WorkflowTimeline } from "@/components/mp/WorkflowTimeline";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import { toast } from "sonner";
import { useMeetingWebSocket } from "@/hooks/useMeetingWebSocket";

export const Route = createFileRoute("/dashboard/meetings/$id")({
  head: ({ params }) => ({
    meta: [
      { title: `Case file ${params.id} — MeetingPilot` },
      { name: "description", content: "Full briefing, agenda, checklist, and workflow trace for this meeting." },
      { name: "robots", content: "noindex" },
      { property: "og:title", content: `Case file ${params.id} — MeetingPilot` },
      { property: "og:description", content: "Briefing, agenda, and checklist for a researched meeting." },
      { property: "og:type", content: "article" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: MeetingDetail,
});

function MeetingDetail() {
  const { id } = Route.useParams();
  const qc = useQueryClient();
  const { tickChecklist } = useMeetingWebSocket(id);

  const detailQ = useQuery({ queryKey: ["meeting", id], queryFn: () => api.meetings.detail(id) });
  const logsQ = useQuery({ queryKey: ["meeting-logs", id], queryFn: () => api.meetings.workflowLogs(id) });

  const redo = useMutation({
    mutationFn: () => api.meetings.redo(id),
    onSuccess: () => {
      toast.success("Re-running research");
      qc.invalidateQueries({ queryKey: ["meeting", id] });
      qc.invalidateQueries({ queryKey: ["meeting-logs", id] });
    },
  });

  const approve = useMutation({
    mutationFn: () => api.meetings.agenda.approveAndSend(id),
    onSuccess: () => {
      toast.success("Agenda approved and sent");
      qc.invalidateQueries({ queryKey: ["meeting", id] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to send agenda");
    }
  });

  const approveChecklist = useMutation({
    mutationFn: () => api.meetings.checklist.send(id),
    onSuccess: () => {
      toast.success("Checklist approved and sent");
      qc.invalidateQueries({ queryKey: ["meeting", id] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to send checklist");
    }
  });



  if (detailQ.isLoading || !detailQ.data) {
    return (
      <AppShell subtitle="Case file" title="Loading…">
        <div className="mx-auto max-w-5xl px-6 py-10 text-sm text-muted-ink">
          <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> Loading meeting…
        </div>
      </AppShell>
    );
  }

  const m = detailQ.data;

  return (
    <AppShell
      subtitle={`Case file · ${m.id}`}
      title={m.title}
      actions={
        <>
          <Button size="sm" variant="ghost" onClick={() => redo.mutate()} disabled={redo.isPending}>
            {redo.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-1 h-4 w-4" />}
            Re-run
          </Button>
          <StatusBadge status={m.status} size="md" />
        </>
      }
    >
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <div className="mb-4">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1 text-sm text-muted-ink hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to meetings
          </Link>
        </div>

        {/* Meta strip */}
        <div className="grid gap-3 rounded-md border border-rule bg-paper-elevated p-4 sm:grid-cols-3">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">When</div>
            <div className="mt-1 text-sm">
              {new Date(m.start_time).toLocaleString()} → {new Date(m.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </div>
          </div>
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">Attendees</div>
            <div className="mt-1 text-sm">
              {m.attendees.map((a) => `${a.name}${a.company ? ` (${a.company})` : ""}`).join(", ")}
            </div>
          </div>
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">Sources</div>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {(["osint", "direct_search", "rag"] as const).map((s) => (
                <span
                  key={s}
                  className={`rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${
                    m.sources_used?.[s]
                      ? "border-success/40 bg-success/10 text-success"
                      : "border-rule bg-muted text-muted-ink"
                  }`}
                >
                  {s.replace("_", " ")}
                </span>
              ))}
            </div>
          </div>
        </div>

        {["processing", "queued"].includes(m.status) ? (
          <div className="mt-8 rounded-md border border-rule bg-paper p-8 text-center">
            <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-signal" />
            <h3 className="font-display text-xl">Processing Meeting...</h3>
            <p className="mt-2 text-sm text-muted-ink">Gathering intelligence and preparing the agenda.</p>
            
            {logsQ.data && logsQ.data.length > 0 && (
              <div className="mx-auto mt-8 max-w-lg text-left">
                <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink mb-4">Live Progress</div>
                <ul className="space-y-4">
                  {logsQ.data.map((log: any, i: number) => (
                    <li key={i} className="flex items-start gap-3">
                      {log.status === 'started' || log.status === 'retried' ? (
                        <Loader2 className="mt-0.5 h-4 w-4 animate-spin text-signal" />
                      ) : log.status === 'success' || log.status === 'cached' || log.status === 'skipped' ? (
                        <div className="mt-0.5 h-4 w-4 rounded-full bg-success/20 text-success flex items-center justify-center">✓</div>
                      ) : log.status === 'failed' ? (
                        <div className="mt-0.5 h-4 w-4 rounded-full bg-alert/20 text-alert flex items-center justify-center">✕</div>
                      ) : null}
                      <div>
                        <div className={`text-sm ${log.status === 'started' ? 'text-foreground font-medium' : 'text-muted-ink'}`}>
                          {log.message || `Running ${log.node_name}...`}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <Tabs defaultValue="briefing" className="mt-6">
          <TabsList>
            <TabsTrigger value="briefing" className="font-mono text-[11px] uppercase tracking-wider">Briefing</TabsTrigger>
            <TabsTrigger value="agenda" className="font-mono text-[11px] uppercase tracking-wider">Agenda</TabsTrigger>
            <TabsTrigger value="checklist" className="font-mono text-[11px] uppercase tracking-wider">Checklist</TabsTrigger>
            <TabsTrigger value="workflow" className="font-mono text-[11px] uppercase tracking-wider">Workflow</TabsTrigger>
          </TabsList>

          <TabsContent value="briefing" className="mt-6 space-y-6">
            <CaseCard label="Insight report" title="What we found">
              <p className="text-foreground/90">{m.insight_report?.summary}</p>
              <ul className="mt-4 space-y-2">
                {m.insight_report?.key_findings?.map((f: string, i: number) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span aria-hidden className="mt-2 inline-block h-1 w-1 rounded-full bg-signal" />
                    {f}
                  </li>
                ))}
              </ul>
              {m.insight_report?.attendee_briefs?.map((b: any, i: number) => (
                <div key={i} className="mt-6 rounded-md border border-rule bg-paper p-4">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">Attendee brief</div>
                  <div className="mt-1 font-display text-xl">{b.name}</div>
                  <div className="text-sm text-muted-ink">{b.role} · {b.company}</div>
                  <ul className="mt-3 space-y-1 text-sm">
                    {b.notes?.map((n: string, j: number) => (
                      <li key={j} className="flex gap-2">
                        <span aria-hidden className="mt-2 h-1 w-1 rounded-full bg-slate" />
                        {n}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </CaseCard>

            <CaseCard label="Handout" title={m.handout?.headline || "Meeting Handout"} action={<Sparkles className="h-4 w-4 text-signal" />}>
              <div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">Talking points</div>
                <ul className="mt-2 space-y-1 text-sm">
                  {m.handout?.talking_points?.map((p: string, i: number) => (
                    <li key={i} className="flex gap-2">
                      <span aria-hidden className="mt-2 h-1 w-1 rounded-full bg-signal" />
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-6">
                <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">Questions to ask</div>
                <ul className="mt-2 space-y-1 text-sm">
                  {m.handout?.questions_to_ask?.map((p: string, i: number) => (
                    <li key={i} className="flex gap-2">
                      <span aria-hidden className="mt-2 h-1 w-1 rounded-full bg-slate" />
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            </CaseCard>
          </TabsContent>

          <TabsContent value="agenda" className="mt-6">
            <CaseCard
              label={`Agenda · ${m.agenda?.status || "pending"}`}
              title="Proposed agenda"
              action={
                m.agenda?.status !== "sent" ? (
                  <Button size="sm" onClick={() => approve.mutate()} disabled={approve.isPending}>
                    {approve.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Send className="mr-1 h-4 w-4" />}
                    Approve & send
                  </Button>
                ) : (
                  <span className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-wider text-success">
                    <Mail className="h-3.5 w-3.5" /> Sent
                  </span>
                )
              }
            >
              <ol className="space-y-3">
                {m.agenda?.items?.map((item: any) => (
                  <li key={item.id} className="flex items-start gap-3 rounded border border-rule bg-paper p-3">
                    <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-rule font-mono text-[11px]">
                      {item.order}
                    </span>
                    <Textarea defaultValue={item.text} rows={1} className="min-h-0 flex-1 resize-none border-0 bg-transparent p-0 shadow-none focus-visible:ring-0" />
                  </li>
                ))}
              </ol>
            </CaseCard>
          </TabsContent>

          <TabsContent value="checklist" className="mt-6">
            <CaseCard 
              label={`Checklist · ${m.checklist?.status || "pending"}`} 
              title="In-call checklist"
              action={
                m.checklist?.status !== "sent" ? (
                  <Button size="sm" onClick={() => approveChecklist.mutate()} disabled={approveChecklist.isPending}>
                    {approveChecklist.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Send className="mr-1 h-4 w-4" />}
                    Approve & send
                  </Button>
                ) : (
                  <span className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-wider text-success">
                    <Mail className="h-3.5 w-3.5" /> Sent
                  </span>
                )
              }
            >
              <p className="text-sm text-muted-ink">
                Tick items as they're covered. During a call this appears as a quiet 3-second overlay.
              </p>
              <ul className="mt-4 space-y-3">
                {m.agenda?.items?.map((item: any) => {
                  const state = m.checklist?.items?.find((c: any) => c.agenda_item_id === item.id);
                  const isTicked = (state?.ticked_by?.length ?? 0) > 0;
                  return (
                    <li key={item.id} className="flex items-start gap-3 rounded border border-rule bg-paper p-3">
                      <Checkbox
                        checked={isTicked}
                        onCheckedChange={(v) => tickChecklist(item.id, !!v)}
                        className="mt-0.5"
                      />
                      <div className="min-w-0 flex-1">
                        <div className={isTicked ? "text-muted-ink line-through" : ""}>{item.text}</div>
                        {state?.comments?.map((c: any, i: number) => (
                          <div key={i} className="mt-1 rounded bg-muted/40 px-2 py-1 text-[12px] text-foreground/80">
                            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">
                              {c.author}
                            </span>{" "}
                            {c.text}
                          </div>
                        ))}
                      </div>
                      {isTicked && <CheckCircle2 className="h-4 w-4 text-success" />}
                    </li>
                  );
                })}
              </ul>
            </CaseCard>
          </TabsContent>

          <TabsContent value="workflow" className="mt-6">
            <CaseCard label="Trace" title="Workflow log">
              {logsQ.isLoading || !logsQ.data ? (
                <div className="text-sm text-muted-ink">
                  <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> Loading trace…
                </div>
              ) : (
                <WorkflowTimeline entries={logsQ.data} />
              )}
            </CaseCard>
          </TabsContent>
        </Tabs>
        )}
      </div>
    </AppShell>
  );
}
