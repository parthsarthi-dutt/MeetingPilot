import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { AppShell } from "@/components/mp/AppShell";
import { CaseCard } from "@/components/mp/CaseCard";
import { StatusBadge } from "@/components/mp/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api/client";
import type { MeetingStatus } from "@/lib/api/types";

export const Route = createFileRoute("/admin")({
  head: () => ({
    meta: [
      { title: "Admin — MeetingPilot" },
      { name: "description", content: "Team-wide usage, agent throughput, and workflow health." },
      { name: "robots", content: "noindex" },
      { property: "og:title", content: "Admin — MeetingPilot" },
      { property: "og:description", content: "MeetingPilot admin dashboard." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Admin,
});

function Admin() {
  const overviewQ = useQuery({ queryKey: ["admin-overview"], queryFn: api.admin.overview });
  const usersQ = useQuery({ queryKey: ["admin-users"], queryFn: api.admin.users });

  if (overviewQ.isError || usersQ.isError) {
    return (
      <AppShell subtitle="Operations" title="Admin">
        <div className="flex h-full items-center justify-center p-8">
          <div className="text-center">
            <Shield className="mx-auto mb-4 h-12 w-12 text-alert" />
            <h2 className="font-display text-2xl">Access Denied</h2>
            <p className="mt-2 text-sm text-muted-ink">
              You do not have permission to view this page. This area is restricted to administrators.
            </p>
          </div>
        </div>
      </AppShell>
    );
  }

  if (!overviewQ.data || !usersQ.data) {
    return (
      <AppShell subtitle="Operations" title="Admin">
        <div className="p-8 text-sm text-muted-ink">
          <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> Loading analytics…
        </div>
      </AppShell>
    );
  }
  const o = overviewQ.data;

  const stats = [
    { label: "Total users", value: o.total_users },
    { label: "Credits used", value: o.total_credits_used.toLocaleString() },
    { label: "Reports", value: o.total_reports },
    { label: "Agendas sent", value: o.total_agendas_sent },
    { label: "Checklists sent", value: o.total_checklists_sent },
    { label: "Avg workflow", value: `${(o.avg_workflow_time_ms / 1000).toFixed(1)}s` },
    { label: "Failed runs", value: o.failed_workflow_count, tone: "text-alert" },
  ];

  return (
    <AppShell subtitle="Operations" title="Admin">
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6 sm:py-8">
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-7">
          {stats.map((s) => (
            <div key={s.label} className="rounded-md border border-rule bg-paper-elevated p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">{s.label}</div>
              <div className={`mt-1 font-display text-2xl ${s.tone ?? ""}`}>{s.value}</div>
            </div>
          ))}
        </div>

        <CaseCard label="Throughput" title="Meetings by status">
          <div className="grid gap-3 sm:grid-cols-4 lg:grid-cols-7">
            {(Object.keys(o.meetings_by_status) as MeetingStatus[]).map((k) => (
              <div key={k} className="rounded-md border border-rule bg-paper p-3">
                <StatusBadge status={k} />
                <div className="mt-2 font-display text-2xl">{o.meetings_by_status[k]}</div>
              </div>
            ))}
          </div>
        </CaseCard>

        <CaseCard label="Users" title="Recent activity">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Signup</TableHead>
                  <TableHead>Credits</TableHead>
                  <TableHead>Meetings</TableHead>
                  <TableHead>Reports</TableHead>
                  <TableHead>Agendas</TableHead>
                  <TableHead>Checklists</TableHead>
                  <TableHead>KB</TableHead>
                  <TableHead>Last active</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {usersQ.data.map((u) => (
                  <TableRow key={u.email}>
                    <TableCell className="font-mono text-xs">{u.email}</TableCell>
                    <TableCell className="text-xs text-muted-ink">
                      {new Date(u.signup_date).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {u.credits_used}/{u.credits_total}
                    </TableCell>
                    <TableCell>{u.meetings_processed}</TableCell>
                    <TableCell>{u.reports_generated}</TableCell>
                    <TableCell>{u.agendas_sent}</TableCell>
                    <TableCell>{u.checklists_sent}</TableCell>
                    <TableCell>
                      <StatusBadge status={u.kb_status === "complete" ? "done" : u.kb_status === "in_progress" ? "processing" : "not_processed"} />
                    </TableCell>
                    <TableCell className="text-xs text-muted-ink">
                      {new Date(u.last_active).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CaseCard>
      </div>
    </AppShell>
  );
}
