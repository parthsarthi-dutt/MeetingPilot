import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, ChevronRight, Loader2, PlayCircle, Search, Plus, Trash2 } from "lucide-react";
import { AppShell } from "@/components/mp/AppShell";
import { CaseCard } from "@/components/mp/CaseCard";
import { StatusBadge } from "@/components/mp/StatusBadge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import type { Meeting, MeetingStatus } from "@/lib/api/types";
import { toast } from "sonner";

export const Route = createFileRoute("/dashboard/")({
  head: () => ({
    meta: [
      { title: "Meetings — MeetingPilot" },
      { name: "description", content: "Every meeting on your calendar, researched and ready." },
      { name: "robots", content: "noindex" },
      { property: "og:title", content: "Meetings — MeetingPilot" },
      { property: "og:description", content: "Your researched meeting queue." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Dashboard,
});

const FILTERS: { key: "all" | MeetingStatus; label: string }[] = [
  { key: "all", label: "All" },
  { key: "processed", label: "Ready" },
  { key: "processing", label: "Processing" },
  { key: "not_processed", label: "Not processed" },
  { key: "done", label: "Done" },
  { key: "rescheduled", label: "Rescheduled" },
  { key: "failed", label: "Failed" },
];

function formatWhen(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Dashboard() {
  const qc = useQueryClient();
  const meetingsQ = useQuery({ queryKey: ["meetings"], queryFn: () => api.meetings.list() });
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["key"]>("all");
  const [q, setQ] = useState("");
  const [showSimulateModal, setShowSimulateModal] = useState(false);

  const simulate = useMutation({
    mutationFn: (data: Parameters<typeof api.meetings.simulate>[0]) => api.meetings.simulate(data),
    onSuccess: () => {
      toast.success("Simulated meeting queued");
      setShowSimulateModal(false);
      qc.invalidateQueries({ queryKey: ["meetings"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to simulate meeting");
    },
  });

  const meetings = meetingsQ.data?.meetings ?? [];
  const filtered = useMemo(() => {
    let rows = meetings;
    if (filter !== "all") rows = rows.filter((m) => m.status === filter);
    if (q.trim())
      rows = rows.filter(
        (m) =>
          m.title.toLowerCase().includes(q.toLowerCase()) ||
          m.attendees.some((a) => a.name.toLowerCase().includes(q.toLowerCase())),
      );
    return rows;
  }, [meetings, filter, q]);

  const stats = useMemo(() => {
    const by = (s: MeetingStatus) => meetings.filter((m) => m.status === s).length;
    return {
      ready: by("processed"),
      processing: by("processing") + by("queued"),
      done: by("done"),
      failed: by("failed"),
    };
  }, [meetings]);

  return (
    <AppShell
      subtitle="Case queue"
      title="Meetings"
      actions={
        <Button size="sm" onClick={() => setShowSimulateModal(true)}>
          <PlayCircle className="mr-1 h-4 w-4" />
          Simulate meeting
        </Button>
      }
    >
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        {/* Stat strip */}
        <div className="grid gap-3 sm:grid-cols-4">
          {[
            { label: "Ready", value: stats.ready, tone: "text-signal" },
            { label: "Processing", value: stats.processing, tone: "text-slate" },
            { label: "Done", value: stats.done, tone: "text-success" },
            { label: "Failed", value: stats.failed, tone: "text-alert" },
          ].map((s) => (
            <div key={s.label} className="rounded-md border border-rule bg-paper-elevated p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">{s.label}</div>
              <div className={`mt-1 font-display text-3xl ${s.tone}`}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Filter + search */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
            <TabsList>
              {FILTERS.map((f) => (
                <TabsTrigger key={f.key} value={f.key} className="font-mono text-[11px] uppercase tracking-wider">
                  {f.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          <div className="relative w-full max-w-xs">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-ink" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search meetings or attendees"
              className="pl-8"
            />
          </div>
        </div>

        {/* List */}
        <div className="mt-6">
          {meetingsQ.isLoading ? (
            <div className="rounded-md border border-rule bg-paper-elevated p-10 text-center text-sm text-muted-ink">
              <Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" /> Loading queue…
            </div>
          ) : filtered.length === 0 ? (
            <CaseCard label="Empty" title="No meetings match">
              <p className="text-sm text-muted-ink">Try clearing filters or simulating a meeting.</p>
            </CaseCard>
          ) : (
            <ul className="divide-y divide-rule overflow-hidden rounded-md border border-rule bg-paper-elevated">
              {filtered.map((m) => (
                <MeetingRow key={m.id} m={m} />
              ))}
            </ul>
          )}
        </div>
      </div>

      <SimulateMeetingModal 
        isOpen={showSimulateModal} 
        onClose={() => setShowSimulateModal(false)} 
        onSimulate={data => simulate.mutate(data)} 
        isPending={simulate.isPending} 
      />
    </AppShell>
  );
}

function MeetingRow({ m }: { m: Meeting }) {
  const externals = m.attendees.filter((a) => a.is_external);
  return (
    <li>
      <Link
        to="/dashboard/meetings/$id"
        params={{ id: m.id }}
        className="flex items-center gap-4 px-4 py-4 transition-colors hover:bg-secondary/50 sm:px-6"
      >
        <div className="hidden shrink-0 sm:block">
          <Calendar className="h-5 w-5 text-muted-ink" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="truncate font-medium text-foreground">{m.title}</span>
            <StatusBadge status={m.status} />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] uppercase tracking-wider text-muted-ink">
            <span>{formatWhen(m.start_time)}</span>
            {externals.length > 0 && (
              <>
                <span aria-hidden>·</span>
                <span className="normal-case tracking-normal">
                  {externals.map((a) => `${a.name}${a.company ? ` (${a.company})` : ""}`).join(", ")}
                </span>
              </>
            )}
          </div>
        </div>
        <ChevronRight className="h-4 w-4 shrink-0 text-muted-ink" />
      </Link>
    </li>
  );
}

function SimulateMeetingModal({
  isOpen,
  onClose,
  onSimulate,
  isPending
}: {
  isOpen: boolean;
  onClose: () => void;
  onSimulate: (data: any) => void;
  isPending: boolean;
}) {
  const [title, setTitle] = useState("Simulated Briefing");
  const [description, setDescription] = useState("");
  
  const getDefaultStart = () => {
    const d = new Date();
    d.setMinutes(d.getMinutes() + 30);
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  };
  const getDefaultEnd = () => {
    const d = new Date();
    d.setMinutes(d.getMinutes() + 90);
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  };

  const [start, setStart] = useState(getDefaultStart());
  const [end, setEnd] = useState(getDefaultEnd());
  const [attendees, setAttendees] = useState([{ name: "Alex Kim", email: "alex@example.example", company: "Example Co" }]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSimulate({
      title,
      description,
      start_time: new Date(start).toISOString(),
      end_time: new Date(end).toISOString(),
      attendees,
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Simulate Meeting</DialogTitle>
          <DialogDescription>
            Test the workflow without creating a Google Calendar event.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Title</Label>
              <Input required value={title} onChange={e => setTitle(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Start Time</Label>
              <Input type="datetime-local" required value={start} onChange={e => setStart(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>End Time</Label>
              <Input type="datetime-local" required value={end} onChange={e => setEnd(e.target.value)} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Description</Label>
              <Textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} placeholder="Meeting context..." />
            </div>
          </div>

          <div className="pt-4 border-t border-rule">
            <div className="flex items-center justify-between mb-2">
              <Label>Attendees</Label>
              <Button type="button" variant="outline" size="sm" onClick={() => setAttendees([...attendees, { name: "", email: "", company: "" }])}>
                <Plus className="h-4 w-4 mr-1" /> Add
              </Button>
            </div>
            <div className="space-y-3">
              {attendees.map((a, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Input placeholder="Name" value={a.name} onChange={e => {
                    const newA = [...attendees];
                    newA[i].name = e.target.value;
                    setAttendees(newA);
                  }} />
                  <Input type="email" placeholder="Email" value={a.email} onChange={e => {
                    const newA = [...attendees];
                    newA[i].email = e.target.value;
                    setAttendees(newA);
                  }} />
                  <Input placeholder="Company" value={a.company} onChange={e => {
                    const newA = [...attendees];
                    newA[i].company = e.target.value;
                    setAttendees(newA);
                  }} />
                  <Button type="button" variant="ghost" size="icon" onClick={() => {
                    setAttendees(attendees.filter((_, idx) => idx !== i));
                  }}>
                    <Trash2 className="h-4 w-4 text-alert" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          <DialogFooter className="mt-6">
            <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
            <Button type="button" onClick={handleSubmit} disabled={isPending}>
              {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Simulate
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
