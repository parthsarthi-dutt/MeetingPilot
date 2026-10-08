import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { AppShell } from "@/components/mp/AppShell";
import { CaseCard } from "@/components/mp/CaseCard";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import type { Settings } from "@/lib/api/types";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — MeetingPilot" },
      { name: "description", content: "Tune your agent. Toggle research, drafting, and in-call overlays." },
      { name: "robots", content: "noindex" },
      { property: "og:title", content: "Settings — MeetingPilot" },
      { property: "og:description", content: "Configure your MeetingPilot agent." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: SettingsPage,
});

const SUB_TOGGLES: { key: string; label: string; help: string }[] = [
  { key: "osint_research", label: "OSINT research", help: "Scan public sources on attendees." },
  { key: "agenda_drafting", label: "Agenda drafting", help: "Draft a proposed agenda for each meeting." },
  { key: "checklist_overlay", label: "In-call checklist", help: "Show the quiet 3-second overlay during calls." },
  { key: "quick_messages", label: "Quick messages", help: "Suggest short follow-ups after each call." },
];

function SettingsPage() {
  const qc = useQueryClient();
  const settingsQ = useQuery({ queryKey: ["settings"], queryFn: api.settings.get });
  const [s, setS] = useState<Settings | null>(null);
  useEffect(() => {
    if (settingsQ.data) setS(settingsQ.data);
  }, [settingsQ.data]);

  const save = useMutation({
    mutationFn: (partial: Partial<Settings>) => api.settings.patch(partial),
    onSuccess: () => {
      toast.success("Settings saved");
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
  });


  if (!s) {
    return (
      <AppShell title="Settings" subtitle="Configuration">
        <div className="p-8 text-sm text-muted-ink">
          <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> Loading…
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell subtitle="Configuration" title="Settings">
      <div className="mx-auto max-w-3xl space-y-6 px-4 py-6 sm:px-6 sm:py-8">
        <CaseCard label="Agent" title="Master switch">
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label className="text-base">Agent enabled</Label>
              <p className="mt-1 text-sm text-muted-ink">
                Turn the whole pipeline on or off. When off, no meetings are researched.
              </p>
            </div>
            <Switch
              checked={s.agent_enabled}
              onCheckedChange={(v) => setS({ ...s, agent_enabled: v })}
            />
          </div>
        </CaseCard>

        <CaseCard label="Modules" title="What the agent does">
          <div className="divide-y divide-rule">
            {SUB_TOGGLES.map((t) => (
              <div key={t.key} className="flex items-start justify-between gap-4 py-4 first:pt-0 last:pb-0">
                <div>
                  <Label className="text-base">{t.label}</Label>
                  <p className="mt-1 text-sm text-muted-ink">{t.help}</p>
                </div>
                <Switch
                  checked={!!s.agent_sub_toggles[t.key]}
                  disabled={!s.agent_enabled}
                  onCheckedChange={(v) =>
                    setS({
                      ...s,
                      agent_sub_toggles: { ...s.agent_sub_toggles, [t.key]: v },
                    })
                  }
                />
              </div>
            ))}
          </div>
        </CaseCard>

        <CaseCard label="Delivery" title="Auto-send behaviour">
          <div className="divide-y divide-rule">
            {[
              { key: "auto_send_agenda", label: "Auto-send agenda", help: "Send drafted agendas before the meeting without approval." },
              { key: "auto_send_checklist", label: "Auto-send checklist", help: "Send finalized checklist to all participants after the meeting ends." },
              { key: "always_rerun_osint", label: "Always re-run OSINT", help: "Re-fetch attendee research even on repeat meetings." },
            ].map((t) => (
              <div key={t.key} className="flex items-start justify-between gap-4 py-4 first:pt-0 last:pb-0">
                <div>
                  <Label className="text-base">{t.label}</Label>
                  <p className="mt-1 text-sm text-muted-ink">{t.help}</p>
                </div>
                <Switch
                  checked={!!(s as unknown as Record<string, boolean>)[t.key]}
                  onCheckedChange={(v) => setS({ ...s, [t.key]: v } as Settings)}
                />
              </div>
            ))}
          </div>
        </CaseCard>

        {s.company_profile && (
          <CaseCard label="Identity" title="Company Profile">
            <div className="space-y-4 pt-2">
              <div>
                <Label className="text-base">Company Name</Label>
                <Input
                  className="mt-1"
                  value={s.company_profile.company_name}
                  onChange={(e) => setS({ ...s, company_profile: { ...s.company_profile!, company_name: e.target.value } })}
                />
              </div>
              <div>
                <Label className="text-base">Your Role / Title</Label>
                <Input
                  className="mt-1"
                  value={s.company_profile.user_role_title}
                  onChange={(e) => setS({ ...s, company_profile: { ...s.company_profile!, user_role_title: e.target.value } })}
                />
              </div>
              <div>
                <Label className="text-base">Product Description</Label>
                <Textarea
                  className="mt-1"
                  rows={3}
                  value={s.company_profile.product_description}
                  onChange={(e) => setS({ ...s, company_profile: { ...s.company_profile!, product_description: e.target.value } })}
                />
              </div>
              <div>
                <Label className="text-base">Value Proposition</Label>
                <Textarea
                  className="mt-1"
                  rows={3}
                  value={s.company_profile.value_proposition}
                  onChange={(e) => setS({ ...s, company_profile: { ...s.company_profile!, value_proposition: e.target.value } })}
                />
              </div>
            </div>
          </CaseCard>
        )}

        <div className="flex justify-end">
          <Button onClick={() => save.mutate(s)} disabled={save.isPending}>
            {save.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
            Save changes
          </Button>
        </div>
      </div>
    </AppShell>
  );
}
