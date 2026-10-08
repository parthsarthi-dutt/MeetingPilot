import { createFileRoute, Link } from "@tanstack/react-router";
import { WorkflowTimeline } from "@/components/mp/WorkflowTimeline";
import { CaseCard } from "@/components/mp/CaseCard";
import { StatusBadge } from "@/components/mp/StatusBadge";
import { Button } from "@/components/ui/button";


export const Route = createFileRoute("/style-guide")({
  head: () => ({
    meta: [
      { title: "Style Guide — MeetingPilot" },
      { name: "description", content: "Design tokens, primitives, and the Workflow Timeline component." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: StyleGuide,
});

function Swatch({ name, cssVar, note }: { name: string; cssVar: string; note?: string }) {
  return (
    <div className="rounded-md border border-rule bg-paper-elevated p-3">
      <div
        aria-hidden
        className="h-16 rounded"
        style={{ background: `var(${cssVar})` }}
      />
      <div className="mt-2 font-mono text-[11px] uppercase tracking-wider text-muted-ink">
        {name}
      </div>
      <div className="font-mono text-[11px] text-foreground/80">{cssVar}</div>
      {note && <div className="mt-1 text-xs text-muted-ink">{note}</div>}
    </div>
  );
}

function StyleGuide() {
  const logs: any[] = [];

  return (
    <main className="min-h-screen bg-paper">
      <div className="mx-auto max-w-5xl px-6 py-12">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
              MeetingPilot · Design system
            </div>
            <h1 className="mt-2 font-display text-5xl">The briefing desk</h1>
            <p className="mt-3 max-w-xl text-foreground/80">
              Tokens, primitives, and the signature Workflow Timeline. This page
              is the reference — real pages compose from these pieces.
            </p>
          </div>
          <Link to="/" className="text-sm text-muted-ink hover:text-foreground">← Home</Link>
        </div>

        {/* Palette */}
        <section className="mt-12">
          <h2 className="font-display text-3xl">Palette</h2>
          <p className="mt-2 text-sm text-muted-ink">
            Named by role. Never reference raw hex in components.
          </p>
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Swatch name="Ink" cssVar="--ink" note="Primary text" />
            <Swatch name="Paper" cssVar="--paper" note="Background" />
            <Swatch name="Signal" cssVar="--signal" note="Findings / CTAs" />
            <Swatch name="Slate" cssVar="--slate" note="In-motion" />
            <Swatch name="Alert" cssVar="--alert" note="Failed only" />
            <Swatch name="Success" cssVar="--success" note="Done only" />
            <Swatch name="Rule" cssVar="--rule" note="Hairline borders" />
            <Swatch name="Muted ink" cssVar="--muted-ink" note="Secondary text" />
          </div>
        </section>

        {/* Typography */}
        <section className="mt-16">
          <h2 className="font-display text-3xl">Typography</h2>
          <div className="mt-6 space-y-6">
            <div className="rounded-md border border-rule bg-paper-elevated p-6">
              <div className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
                Display · Instrument Serif · large sizes only
              </div>
              <p className="mt-3 font-display text-6xl leading-none">Arrive prepared.</p>
              <p className="mt-2 font-display text-3xl leading-tight text-muted-ink">
                Never blindsided.
              </p>
            </div>
            <div className="rounded-md border border-rule bg-paper-elevated p-6">
              <div className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
                Body · Public Sans · UI copy, paragraphs, labels
              </div>
              <p className="mt-3 text-base leading-relaxed">
                Acme is expanding into EU markets in Q4 and recently hired a VP
                of RevOps. Jane owns the tooling budget and has publicly
                complained about their current vendor's onboarding time.
              </p>
              <p className="mt-2 text-sm text-muted-ink">
                Smaller sizes stay readable — this is the caption / helper register.
              </p>
            </div>
            <div className="rounded-md border border-rule bg-paper-elevated p-6">
              <div className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
                Mono · IBM Plex Mono · timestamps, node names, data
              </div>
              <p className="mt-3 font-mono text-sm">
                14:02:47 · osint_research · success · 27.0s
              </p>
            </div>
          </div>
        </section>

        {/* Status badges */}
        <section className="mt-16">
          <h2 className="font-display text-3xl">Status badges</h2>
          <p className="mt-2 text-sm text-muted-ink">
            Consistent mapping across meetings and workflow log entries.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <StatusBadge status="not_processed" />
            <StatusBadge status="queued" />
            <StatusBadge status="processing" />
            <StatusBadge status="processed" />
            <StatusBadge status="done" />
            <StatusBadge status="rescheduled" />
            <StatusBadge status="failed" />
          </div>
        </section>

        {/* Buttons */}
        <section className="mt-16">
          <h2 className="font-display text-3xl">Buttons</h2>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button>Approve &amp; Send</Button>
            <Button variant="secondary">Edit agenda</Button>
            <Button variant="outline">Postpone</Button>
            <Button variant="ghost">Cancel</Button>
            <Button variant="destructive">Redo workflow</Button>
          </div>
        </section>

        {/* Case card */}
        <section className="mt-16">
          <h2 className="font-display text-3xl">Case card</h2>
          <p className="mt-2 text-sm text-muted-ink">
            The bordered module every information block lives inside.
          </p>
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <CaseCard
              label="Case file · m_001"
              title="Quarterly review with Acme"
              action={<StatusBadge status="processed" />}
            >
              <p className="text-sm text-foreground/85">
                Every card carries an optional mono label (like a case-file tag),
                a serif title, an optional action slot, and a body.
              </p>
            </CaseCard>
            <CaseCard label="Empty state · example" title="No meetings yet">
              <p className="text-sm text-foreground/85">
                Connect your calendar or simulate one to see how MeetingPilot works.
              </p>
              <div className="mt-4">
                <Button>Simulate a meeting</Button>
              </div>
            </CaseCard>
          </div>
        </section>

        {/* Workflow Timeline — the signature */}
        <section className="mt-16">
          <h2 className="font-display text-3xl">Workflow Timeline</h2>
          <p className="mt-2 text-sm text-muted-ink">
            The single most important component. Vertical trail, status-colored
            nodes, mono timestamps, expandable detail. Reveals in sequence.
          </p>
          <CaseCard className="mt-6" label="Workflow · m_001" title="Research trail">
            <WorkflowTimeline entries={logs} />
          </CaseCard>
        </section>

        {/* Voice */}
        <section className="mt-16 mb-24">
          <h2 className="font-display text-3xl">Voice</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-md border border-rule bg-paper-elevated p-5">
              <div className="font-mono text-[10px] uppercase tracking-wider text-success">Do</div>
              <p className="mt-2 text-sm">"Send agenda"</p>
              <p className="mt-1 text-sm">"No meetings yet — connect your calendar or simulate one."</p>
              <p className="mt-1 text-sm">"We couldn't reach Google. Try reconnecting."</p>
            </div>
            <div className="rounded-md border border-rule bg-paper-elevated p-5">
              <div className="font-mono text-[10px] uppercase tracking-wider text-alert">Don't</div>
              <p className="mt-2 text-sm text-muted-ink">"Trigger agenda dispatch"</p>
              <p className="mt-1 text-sm text-muted-ink">"No data."</p>
              <p className="mt-1 text-sm text-muted-ink">"Oops! Something went wrong."</p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
