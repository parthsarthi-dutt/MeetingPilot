import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/api/client";
import {
  ArrowRight,
  BrainCircuit,
  Calendar,
  CheckCircle2,
  ClipboardList,
  FileSearch,
  MessageSquare,
  Send,
  Sparkles,
} from "lucide-react";
import { WorkflowTimeline } from "@/components/mp/WorkflowTimeline";
import { CaseCard } from "@/components/mp/CaseCard";
import { StatusBadge } from "@/components/mp/StatusBadge";
import { Reveal } from "@/components/mp/Reveal";


export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "MeetingPilot — Arrive prepared, never blindsided" },
      {
        name: "description",
        content:
          "An AI chief of staff that researches every meeting on your calendar. Evidence-backed briefings, drafted agendas, and quiet in-call checklists — delivered before you walk in.",
      },
      { property: "og:title", content: "MeetingPilot — Arrive prepared, never blindsided" },
      {
        property: "og:description",
        content: "An AI chief of staff that briefs you before every meeting.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "MeetingPilot — Arrive prepared, never blindsided" },
      { name: "twitter:description", content: "An AI chief of staff that briefs you before every meeting." },
    ],
  }),
  component: Home,
});

function Home() {
  const [hasToken, setHasToken] = useState(false);
  useEffect(() => {
    setHasToken(Boolean(localStorage.getItem("mp_access_token")));
  }, []);

  const logs: any[] = [
    {
      id: "l_1",
      meeting_id: "m_001",
      step: "system",
      status: "success",
      message: "Webhook received. Calendar event created.",
      timestamp: "2024-03-10T09:00:00Z",
    },
    {
      id: "l_2",
      meeting_id: "m_001",
      step: "osint",
      status: "success",
      message: "Researched Acme Corp. Found recent series B funding.",
      timestamp: "2024-03-10T09:00:15Z",
    }
  ];

  return (
    <main className="min-h-screen bg-paper text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-rule bg-paper/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2">
            <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-full bg-signal" />
            <span className="font-display text-xl">MeetingPilot</span>
          </Link>
          <nav className="flex items-center gap-6 text-sm">
            <a href="#how" className="hidden text-muted-ink hover:text-foreground sm:inline">
              How it works
            </a>
            <a href="#pricing" className="hidden text-muted-ink hover:text-foreground sm:inline">
              Pricing
            </a>
            <a href="#faq" className="hidden text-muted-ink hover:text-foreground sm:inline">
              FAQ
            </a>
            <Link
              to="/style-guide"
              className="hidden text-muted-ink hover:text-foreground md:inline"
            >
              Style guide
            </Link>
            {hasToken ? (
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-paper transition-colors hover:opacity-90"
              >
                Go to Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <a
                href={`${API_BASE_URL}/api/auth/login`}
                className="inline-flex items-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-paper transition-colors hover:opacity-90"
              >
                Sign in with Google
                <ArrowRight className="h-4 w-4" />
              </a>
            )}
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-rule">
        {/* Ambient case-file gridlines */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              "linear-gradient(to right, var(--rule) 1px, transparent 1px), linear-gradient(to bottom, var(--rule) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
            maskImage:
              "radial-gradient(ellipse at 60% 40%, black 0%, transparent 70%)",
          }}
        />
        <div className="relative mx-auto grid max-w-6xl gap-12 px-6 py-16 lg:grid-cols-2 lg:py-24">
          <Reveal className="flex flex-col justify-center">
            <span className="inline-flex w-fit items-center gap-2 rounded-full border border-rule bg-paper-elevated px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-muted-ink">
              <Sparkles className="h-3 w-3 text-signal" />
              Chief of staff for every meeting
            </span>
            <h1 className="mt-6 font-display text-5xl leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
              Arrive prepared.<br />
              <span className="text-muted-ink">Never blindsided.</span>
            </h1>
            <p className="mt-6 max-w-md text-lg text-foreground/80">
              MeetingPilot researches every meeting on your calendar — the people, the company, the
              recent signals — and hands you a briefing before you walk in. Not a chatbot. A sharp
              analyst.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              {hasToken ? (
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-2 rounded-md bg-ink px-5 py-3 text-sm font-medium text-paper transition-transform hover:opacity-90 hover:-translate-y-[1px]"
                >
                  Go to Dashboard
                  <ArrowRight className="h-4 w-4" />
                </Link>
              ) : (
                <a
                  href={`${API_BASE_URL}/api/auth/login`}
                  className="inline-flex items-center gap-2 rounded-md bg-ink px-5 py-3 text-sm font-medium text-paper transition-transform hover:opacity-90 hover:-translate-y-[1px]"
                >
                  Sign in with Google
                  <ArrowRight className="h-4 w-4" />
                </a>
              )}
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 rounded-md border border-rule bg-paper-elevated px-5 py-3 text-sm font-medium text-foreground hover:bg-secondary"
              >
                See the live demo
              </Link>
            </div>
            <p className="mt-6 font-mono text-[11px] uppercase tracking-wider text-muted-ink">
              No credit card · Read-only calendar access
            </p>

            <dl className="mt-10 grid max-w-md grid-cols-3 gap-4 border-t border-rule pt-6">
              {[
                { k: "12s", v: "avg. research time" },
                { k: "38%", v: "shorter meetings" },
                { k: "0", v: "post-call scrambles" },
              ].map((s) => (
                <div key={s.v}>
                  <dt className="font-display text-3xl">{s.k}</dt>
                  <dd className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">{s.v}</dd>
                </div>
              ))}
            </dl>
          </Reveal>

          <Reveal delayMs={120} className="self-center">
            <CaseCard
              label="Case file · m_001"
              title="Quarterly review with Acme"
              action={<StatusBadge status="processed" size="md" />}
            >
              <div className="mb-4 flex items-center gap-3 text-xs text-muted-ink">
                <span className="font-mono">14:00 → 14:45</span>
                <span aria-hidden>·</span>
                <span>Jane Doe · Acme Corp</span>
              </div>
              <WorkflowTimeline entries={logs} />
            </CaseCard>
          </Reveal>
        </div>
      </section>

      {/* Trusted by strip */}
      <section className="border-b border-rule bg-paper-elevated">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6 px-6 py-8">
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
            Trusted by operators at
          </p>
          <div className="flex flex-wrap items-center gap-x-10 gap-y-3 opacity-70">
            {["ACME", "NORTHWIND", "GLOBEX", "INITECH", "UMBRELLA", "STARK IND."].map((n) => (
              <span key={n} className="font-display text-xl tracking-tight">
                {n}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* The problem */}
      <section className="border-b border-rule">
        <div className="mx-auto grid max-w-6xl gap-12 px-6 py-20 lg:grid-cols-2">
          <Reveal>
            <span className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
              The problem
            </span>
            <h2 className="mt-3 max-w-xl font-display text-4xl leading-tight sm:text-5xl">
              You walked in cold. Again.
            </h2>
            <p className="mt-6 max-w-md text-foreground/80">
              You have thirty calls this week. Half are with people you've never met. Their company
              raised last month, hired a new VP, or just shipped a competitor to your product — and
              nobody told you.
            </p>
            <p className="mt-4 max-w-md text-foreground/80">
              You'll figure it out in the first ten minutes of every call. That's ten minutes you
              didn't spend closing.
            </p>
          </Reveal>
          <Reveal delayMs={100}>
            <ul className="grid gap-3">
              {[
                "Skimming LinkedIn on the walk to the meeting room",
                "Asking a colleague 'what do we know about them?'",
                "Getting caught out by news the attendee already saw",
                "Forgetting what you promised last quarter",
                "Writing follow-ups from memory, missing half",
              ].map((line) => (
                <li key={line} className="flex items-start gap-3 rounded-md border border-rule bg-paper-elevated p-4">
                  <span aria-hidden className="mt-1.5 inline-block h-1.5 w-1.5 rounded-full bg-alert" />
                  <span className="text-sm">{line}</span>
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </section>

      {/* Feature blocks */}
      <section id="how" className="border-b border-rule bg-paper-elevated">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <span className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
              How it works
            </span>
            <h2 className="mt-3 max-w-2xl font-display text-4xl leading-tight sm:text-5xl">
              A sharp analyst handing you a briefing —<br />
              <span className="text-muted-ink">not a chatbot to argue with.</span>
            </h2>
          </Reveal>

          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {FEATURES.map((f, i) => (
              <Reveal key={f.title} delayMs={i * 90}>
                <div className="group h-full rounded-md border border-rule bg-paper p-6 transition-transform hover:-translate-y-1">
                  <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-ink">
                    <f.icon className="h-3.5 w-3.5 text-signal" />
                    {f.tag}
                  </div>
                  <h3 className="mt-3 font-display text-2xl">{f.title}</h3>
                  <p className="mt-3 text-sm text-foreground/80">{f.body}</p>
                  <ul className="mt-4 space-y-1.5 text-[13px]">
                    {f.bullets.map((b) => (
                      <li key={b} className="flex gap-2">
                        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow visual */}
      <section className="border-b border-rule">
        <div className="mx-auto grid max-w-6xl gap-12 px-6 py-24 lg:grid-cols-2">
          <Reveal>
            <span className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
              Under the hood
            </span>
            <h2 className="mt-3 font-display text-4xl leading-tight sm:text-5xl">
              Every briefing is a workflow you can trace.
            </h2>
            <p className="mt-6 max-w-md text-foreground/80">
              MeetingPilot doesn't hand you a paragraph and hope you trust it. Every finding shows
              which sources it came from, which nodes ran, and how long each step took.
            </p>
            <ul className="mt-8 space-y-4">
              {WORKFLOW_STEPS.map((s) => (
                <li key={s.title} className="flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-rule bg-paper-elevated">
                    <s.icon className="h-4 w-4 text-signal" />
                  </div>
                  <div>
                    <div className="font-medium">{s.title}</div>
                    <div className="text-sm text-muted-ink">{s.body}</div>
                  </div>
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal delayMs={100}>
            <CaseCard label="Live trace · m_001" title="Workflow log">
              <WorkflowTimeline entries={logs} compact />
            </CaseCard>
          </Reveal>
        </div>
      </section>

      {/* Big quote */}
      <section className="border-b border-rule bg-paper-elevated">
        <div className="mx-auto max-w-4xl px-6 py-24 text-center">
          <Reveal>
            <p className="font-display text-3xl leading-snug sm:text-4xl">
              "It's like walking into every meeting with a briefing binder someone already read
              for me. I stopped losing the first ten minutes to 'so, remind me what you do?'"
            </p>
            <div className="mt-8 font-mono text-[11px] uppercase tracking-wider text-muted-ink">
              — Priya P., Head of Sales, Globex (early user)
            </div>
          </Reveal>
        </div>
      </section>

      {/* Testimonials grid */}
      <section className="border-b border-rule">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <span className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
              What operators say
            </span>
            <h2 className="mt-3 font-display text-4xl">
              Boring name for a tool. Sharp results.
            </h2>
          </Reveal>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {TESTIMONIALS.map((t, i) => (
              <Reveal key={t.who} delayMs={i * 90}>
                <figure className="h-full rounded-md border border-rule bg-paper-elevated p-6">
                  <blockquote className="text-[15px] leading-relaxed text-foreground/90">
                    "{t.quote}"
                  </blockquote>
                  <figcaption className="mt-6 flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-signal/20 font-display text-lg">
                      {t.who.charAt(0)}
                    </div>
                    <div>
                      <div className="text-sm font-medium">{t.who}</div>
                      <div className="font-mono text-[10px] uppercase tracking-wider text-muted-ink">
                        {t.role}
                      </div>
                    </div>
                  </figcaption>
                </figure>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="border-b border-rule bg-paper-elevated">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <span className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
              Not just another AI note-taker
            </span>
            <h2 className="mt-3 max-w-2xl font-display text-4xl leading-tight">
              Note-takers record what happened. MeetingPilot prepares what's about to.
            </h2>
          </Reveal>
          <Reveal delayMs={100}>
            <div className="mt-10 overflow-hidden rounded-md border border-rule bg-paper">
              <div className="grid grid-cols-3 divide-x divide-rule border-b border-rule text-sm">
                <div className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-ink">
                  Feature
                </div>
                <div className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted-ink">
                  AI Note-taker
                </div>
                <div className="bg-signal/10 px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-[color:var(--ink)]">
                  MeetingPilot
                </div>
              </div>
              {COMPARE.map((row) => (
                <div key={row.feature} className="grid grid-cols-3 divide-x divide-rule border-b border-rule text-sm last:border-b-0">
                  <div className="px-4 py-3">{row.feature}</div>
                  <div className="px-4 py-3 text-muted-ink">{row.other}</div>
                  <div className="bg-signal/5 px-4 py-3 font-medium">{row.us}</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-b border-rule">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <h2 className="font-display text-4xl sm:text-5xl">Simple credits, no surprises</h2>
            <p className="mt-3 max-w-xl text-foreground/80">
              One credit per meeting researched. Rescheduled meetings don't re-charge. Unused
              credits roll over one month.
            </p>
          </Reveal>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {PLANS.map((p, i) => (
              <Reveal key={p.name} delayMs={i * 80}>
                <div
                  className={`h-full rounded-md border p-6 transition-transform hover:-translate-y-1 ${
                    p.featured ? "border-signal bg-paper-elevated shadow-[0_10px_40px_-20px_var(--signal)]" : "border-rule bg-paper-elevated"
                  }`}
                >
                  {p.featured && (
                    <span className="inline-block rounded-full bg-signal/15 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-[color:var(--ink)]">
                      Most popular
                    </span>
                  )}
                  <h3 className="mt-3 font-display text-2xl">{p.name}</h3>
                  <div className="mt-2 font-display text-4xl">{p.price}</div>
                  <div className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
                    {p.credits} credits / month
                  </div>
                  <ul className="mt-6 space-y-2 text-sm text-foreground/85">
                    {p.features.map((line) => (
                      <li key={line} className="flex gap-2">
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                        {line}
                      </li>
                    ))}
                  </ul>
                  <Link
                    to="/onboarding"
                    className={`mt-8 inline-flex w-full items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition-colors ${
                      p.featured
                        ? "bg-ink text-paper hover:opacity-90"
                        : "border border-rule bg-paper text-foreground hover:bg-secondary"
                    }`}
                  >
                    {p.cta} <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="border-b border-rule bg-paper-elevated">
        <div className="mx-auto max-w-4xl px-6 py-24">
          <Reveal>
            <h2 className="font-display text-4xl">Frequently asked</h2>
          </Reveal>
          <div className="mt-10 divide-y divide-rule border-y border-rule">
            {FAQ.map((q, i) => (
              <Reveal key={q.q} delayMs={i * 60}>
                <details className="group py-5">
                  <summary className="flex cursor-pointer items-start justify-between gap-6 text-left">
                    <span className="font-display text-xl">{q.q}</span>
                    <span
                      aria-hidden
                      className="mt-1 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-rule bg-paper transition-transform group-open:rotate-45"
                    >
                      +
                    </span>
                  </summary>
                  <p className="mt-3 pr-10 text-foreground/85">{q.a}</p>
                </details>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative overflow-hidden border-b border-rule bg-ink text-paper">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-20"
          style={{
            backgroundImage:
              "radial-gradient(600px circle at 20% 20%, var(--signal) 0%, transparent 60%), radial-gradient(500px circle at 80% 80%, var(--slate) 0%, transparent 60%)",
          }}
        />
        <div className="relative mx-auto max-w-4xl px-6 py-24 text-center">
          <Reveal>
            <h2 className="font-display text-5xl leading-tight sm:text-6xl">
              Stop walking in cold.
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-lg text-paper/80">
              Two minutes to set up. Zero prompts to write. Your next meeting will already be
              researched.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              {hasToken ? (
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-2 rounded-md bg-signal px-6 py-3 text-sm font-medium text-[color:var(--ink)] hover:opacity-90"
                >
                  Go to Dashboard <ArrowRight className="h-4 w-4" />
                </Link>
              ) : (
                <a
                  href={`${API_BASE_URL}/api/auth/login`}
                  className="inline-flex items-center gap-2 rounded-md bg-signal px-6 py-3 text-sm font-medium text-[color:var(--ink)] hover:opacity-90"
                >
                  Sign in with Google <ArrowRight className="h-4 w-4" />
                </a>
              )}
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 rounded-md border border-paper/30 px-6 py-3 text-sm font-medium text-paper hover:bg-paper/10"
              >
                Explore the demo
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="bg-paper">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8 text-sm text-muted-ink">
          <div className="flex items-center gap-2">
            <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-signal" />
            <span className="font-display text-base text-foreground">MeetingPilot</span>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <Link to="/style-guide" className="hover:text-foreground">Style guide</Link>
            <Link to="/dashboard" className="hover:text-foreground">Demo</Link>
            <Link to="/admin" className="hover:text-foreground">Admin</Link>
          </div>
          <div className="font-mono text-[11px] uppercase tracking-wider">
            © 2026 MeetingPilot
          </div>
        </div>
      </footer>
    </main>
  );
}

const FEATURES = [
  {
    tag: "01 · Research",
    icon: FileSearch,
    title: "The homework, done",
    body: "Every attendee, every company, every recent signal — pulled together before the meeting starts. You just read.",
    bullets: ["OSINT + direct source search", "Retrieval from your own KB", "Confidence scores on findings"],
  },
  {
    tag: "02 · Agenda",
    icon: ClipboardList,
    title: "Drafted, yours to approve",
    body: "A proposed agenda based on where you left off and what's changed. Edit inline, approve, and it sends.",
    bullets: ["Aware of last meeting's outcomes", "Editable in-place", "One-click send to attendees"],
  },
  {
    tag: "03 · In-call",
    icon: MessageSquare,
    title: "A checklist that follows you",
    body: "During the call, a quiet overlay tracks the agenda items covered. Fades in for 3 seconds, hover to keep it.",
    bullets: ["Chrome extension overlay", "Auto-detects covered points", "Notes captured to the case file"],
  },
];

const WORKFLOW_STEPS = [
  { icon: Calendar, title: "Watches your calendar", body: "Read-only access. New meetings enter the queue automatically." },
  { icon: BrainCircuit, title: "Researches the room", body: "OSINT, direct search, your KB — every source cited." },
  { icon: ClipboardList, title: "Drafts an agenda", body: "Based on where you left off. HITL by default, auto-send optional." },
  { icon: Send, title: "Sends the briefing", body: "Straight to your inbox before the call. No dashboard required." },
];

const TESTIMONIALS = [
  {
    who: "Marcus Chen",
    role: "Founder, Initech",
    quote: "I killed three tabs of pre-meeting spelunking. My CS lead now walks in already knowing the account's last support ticket.",
  },
  {
    who: "Sam Rivera",
    role: "Head of RevOps, Northwind",
    quote: "Our reps stopped opening every deal cold. Cycle time is measurably down. That's the whole review.",
  },
  {
    who: "Jane Doe",
    role: "VP Product, Acme",
    quote: "The traceability matters. It's not a black box paragraph — I can see exactly which sources fed each finding.",
  },
];

const COMPARE = [
  { feature: "Runs BEFORE the meeting", other: "No — after", us: "Yes — briefing waiting for you" },
  { feature: "Researches the attendees", other: "No", us: "Yes — OSINT + your KB" },
  { feature: "Drafts your agenda", other: "No", us: "Yes — editable, approve-and-send" },
  { feature: "In-call checklist overlay", other: "No", us: "Yes — quiet Chrome extension" },
  { feature: "Shows its sources", other: "Rarely", us: "Every finding cited" },
];

const PLANS = [
  {
    name: "Solo",
    price: "$29",
    credits: "60",
    featured: false,
    cta: "Start free",
    features: ["1 seat", "60 researched meetings", "Chrome extension included", "Email support"],
  },
  {
    name: "Team",
    price: "$79",
    credits: "200",
    featured: true,
    cta: "Start team trial",
    features: ["Up to 5 seats", "200 researched meetings", "Shared knowledge base", "Priority support", "SSO (Google)"],
  },
  {
    name: "Scale",
    price: "Custom",
    credits: "∞",
    featured: false,
    cta: "Talk to us",
    features: ["Unlimited seats", "Custom KB & integrations", "Dedicated success manager", "SOC 2 report"],
  },
];

const FAQ = [
  {
    q: "How does MeetingPilot access my calendar?",
    a: "Read-only Google Calendar scope, plus a gmail.send scope so we can email you briefings. We never post as you and we never read unrelated email.",
  },
  {
    q: "Is my data used to train anyone's model?",
    a: "No. Your calendar, KB, and briefings are yours. We don't fine-tune on customer data, ever.",
  },
  {
    q: "What happens when a meeting is rescheduled?",
    a: "The existing case file is reused — you don't get charged a fresh credit and you don't lose the briefing you already read.",
  },
  {
    q: "Can I turn off individual modules?",
    a: "Yes. Every part of the agent — OSINT, agenda drafting, checklist overlay, quick messages — has its own toggle in Settings.",
  },
  {
    q: "Does it work for internal meetings too?",
    a: "It works best for external meetings, but internal calls also get a lightweight briefing pulled from your knowledge base and past meeting notes.",
  },
  {
    q: "What if the research is wrong?",
    a: "Every finding cites its source and every run has a traceable workflow log. Bad findings get flagged, and you can re-run research with one click.",
  },
];
