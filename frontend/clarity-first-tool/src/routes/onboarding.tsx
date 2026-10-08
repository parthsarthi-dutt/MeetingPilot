import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Circle, Loader2, ShieldCheck } from "lucide-react";
import { api, API_BASE_URL } from "@/lib/api/client";
import { CaseCard } from "@/components/mp/CaseCard";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import type { CompanyProfile } from "@/lib/api/types";
import { toast } from "sonner";

export const Route = createFileRoute("/onboarding")({
  head: () => ({
    meta: [
      { title: "Get set up — MeetingPilot" },
      { name: "description", content: "Grant calendar access, tell us about your company, and build your knowledge base." },
      { name: "robots", content: "noindex" },
      { property: "og:title", content: "Get set up — MeetingPilot" },
      { property: "og:description", content: "Three quick steps and MeetingPilot starts researching your meetings." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Onboarding,
});

const STEPS = [
  { key: "permissions", label: "Calendar access" },
  { key: "profile", label: "Your company" },
  { key: "kb", label: "Knowledge base" },
] as const;

function Onboarding() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const status = useQuery({ queryKey: ["onboarding-status"], queryFn: api.onboarding.status });
  const profileQ = useQuery({ queryKey: ["company-profile"], queryFn: api.companyProfile.get });

  // Derive initial step from server state.
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (!status.data) return;
    if (!status.data.permissions_complete) setStep(0);
    else if (!status.data.company_profile_complete) setStep(1);
    else setStep(2);
  }, [status.data]);

  const [profile, setProfile] = useState<CompanyProfile>({
    company_name: "",
    product_description: "",
    value_proposition: "",
    user_role_title: "",
  });
  useEffect(() => {
    if (profileQ.data) setProfile(profileQ.data);
  }, [profileQ.data]);

  const saveProfile = useMutation({
    mutationFn: (body: CompanyProfile) => api.companyProfile.save(body),
    onSuccess: () => {
      toast.success("Company profile saved");
      qc.invalidateQueries({ queryKey: ["company-profile"] });
      setStep(2);
    },
  });

  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    <div className="min-h-screen bg-paper">

      <header className="border-b border-rule">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2">
            <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-full bg-signal" />
            <span className="font-display text-xl">MeetingPilot</span>
          </Link>
          <Link to="/dashboard" className="text-sm text-muted-ink hover:text-foreground">
            Skip for now
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-3xl px-6 py-12">
        <div className="font-mono text-[11px] uppercase tracking-wider text-muted-ink">
          Step {step + 1} of {STEPS.length}
        </div>
        <h1 className="mt-2 font-display text-4xl leading-tight">Let's get you briefed.</h1>
        <p className="mt-2 max-w-xl text-foreground/80">
          Three quick steps. Takes under two minutes.
        </p>

        <div className="mt-6">
          <Progress value={progress} className="h-1" />
          <ol className="mt-4 grid grid-cols-3 gap-2 text-sm">
            {STEPS.map((s, i) => (
              <li key={s.key} className="flex items-center gap-2">
                {i < step ? (
                  <CheckCircle2 className="h-4 w-4 text-success" />
                ) : i === step ? (
                  <Circle className="h-4 w-4 text-signal" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-ink/40" />
                )}
                <span className={i === step ? "text-foreground" : "text-muted-ink"}>{s.label}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="mt-10">
          {step === 0 && (
            <CaseCard label="01 · Permissions" title="Connect your Google Calendar">
              <p className="text-foreground/80">
                MeetingPilot needs read-only access to your calendar to see upcoming meetings, plus
                a minimal Gmail scope to send you briefings. We never post as you and we never read
                unrelated email.
              </p>
              <ul className="mt-4 space-y-2 text-sm">
                {[
                  "calendar.readonly — see upcoming meetings",
                  "gmail.send — email briefings to you",
                  "profile — your name and photo",
                ].map((s) => (
                  <li key={s} className="flex items-start gap-2">
                    <ShieldCheck className="mt-0.5 h-4 w-4 text-success" />
                    <span className="font-mono text-[12px]">{s}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-6 flex justify-end">
                <Button
                  onClick={() => {
                    window.location.href = `${API_BASE_URL}/api/auth/login`;
                  }}
                >
                  Connect Google Calendar
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Button>
              </div>
            </CaseCard>
          )}

          {step === 1 && (
            <CaseCard label="02 · Your company" title="Tell us who you are">
              <p className="text-foreground/80">
                We use this to tune every briefing — what to research, how to frame findings, what
                to leave out.
              </p>
              <form
                className="mt-6 grid gap-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  saveProfile.mutate(profile);
                }}
              >
                <div className="grid gap-2">
                  <Label htmlFor="company_name">Company name</Label>
                  <Input
                    id="company_name"
                    required
                    value={profile.company_name}
                    onChange={(e) => setProfile({ ...profile, company_name: e.target.value })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="user_role_title">Your role</Label>
                  <Input
                    id="user_role_title"
                    required
                    value={profile.user_role_title}
                    onChange={(e) => setProfile({ ...profile, user_role_title: e.target.value })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="product_description">What do you sell?</Label>
                  <Textarea
                    id="product_description"
                    required
                    rows={3}
                    value={profile.product_description}
                    onChange={(e) => setProfile({ ...profile, product_description: e.target.value })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="value_proposition">One-line value prop</Label>
                  <Input
                    id="value_proposition"
                    required
                    value={profile.value_proposition}
                    onChange={(e) => setProfile({ ...profile, value_proposition: e.target.value })}
                  />
                </div>
                <div className="mt-2 flex justify-between">
                  <Button type="button" variant="ghost" onClick={() => setStep(0)}>
                    <ArrowLeft className="mr-1 h-4 w-4" /> Back
                  </Button>
                  <Button type="submit" disabled={saveProfile.isPending}>
                    {saveProfile.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
                    Save & continue
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </form>
            </CaseCard>
          )}

          {step === 2 && (
            <CaseCard label="03 · Knowledge base" title="Building your knowledge base">
              <p className="text-foreground/80">
                MeetingPilot is indexing your recent emails and docs to learn how you talk about
                your product. This runs in the background — you can leave this page.
              </p>
              <div className="mt-6 rounded-md border border-rule bg-paper-elevated p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-mono text-[12px] uppercase tracking-wider text-muted-ink">
                    Indexing progress
                  </span>
                  <span className="font-mono text-[12px]">
                    {status.data?.kb_progress_pct ?? 0}%
                  </span>
                </div>
                <Progress value={status.data?.kb_progress_pct ?? 12} className="mt-2 h-1.5" />
                <div className="mt-3 text-[12px] text-muted-ink">
                  Status: <span className="font-mono">{status.data?.kb_status ?? "in_progress"}</span>
                </div>
              </div>
              <div className="mt-6 flex justify-between">
                <Button type="button" variant="ghost" onClick={() => setStep(1)}>
                  <ArrowLeft className="mr-1 h-4 w-4" /> Back
                </Button>
                <Button onClick={() => navigate({ to: "/dashboard" })}>
                  Enter dashboard <ArrowRight className="ml-1 h-4 w-4" />
                </Button>
              </div>
            </CaseCard>
          )}
        </div>
      </div>
    </div>
  );
}
