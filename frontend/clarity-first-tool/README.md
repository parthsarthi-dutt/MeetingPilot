# MeetingPilot — Frontend (Lovable / TanStack Start)

**Status:** Pass 1 shipped — design system + Workflow Timeline + marketing home + `/style-guide` reference page. Real product pages (onboarding, dashboard, meeting detail, settings, admin) land in pass 2 after design review.

## Stack

- **TanStack Start + Vite** (Lovable-required runtime — see PORTING.md for the Next.js App Router migration path).
- React 19, Tailwind v4, shadcn/ui, lucide-react.
- Fonts: Instrument Serif (display), Public Sans (body), IBM Plex Mono (data).

## Structure

```
src/
  lib/api/           # framework-agnostic — port as-is to Next.js
    types.ts         # API contract types (source: API-CONTRACT.md)
    client.ts        # swappable client: mocks by default, real fetch when VITE_USE_MOCK_API=false
    mock-data.ts     # playful personas (Jane Doe / Acme, Sam Rivera / Northwind, ...)
  components/mp/     # MeetingPilot-specific primitives (also portable)
    StatusBadge.tsx
    CaseCard.tsx
    WorkflowTimeline.tsx     # the signature component
  components/ui/     # shadcn primitives (identical API on Next.js)
  routes/            # TanStack Router file-based routes → 1:1 map to app/ dir
    index.tsx        # /  → marketing home (hero uses real Workflow Timeline)
    style-guide.tsx  # /style-guide → design reference (noindex)
```

## Env

Copy `.env.example` → `.env`. Placeholders included for Auth0 (`AUTH0_*`) and the FastAPI backend (`VITE_API_BASE_URL=http://localhost:3005`).

- `VITE_USE_MOCK_API=true` (default): all `api.*` calls return in-memory fixtures with artificial latency.
- Set to `false` once the backend is live — call sites don't change.

## Auth (Auth0)

**Current:** stubbed. "Sign in with Google" routes to `/onboarding` (built in pass 2). `src/lib/api/client.ts` exposes `setAuthTokenGetter(() => Promise<string | null>)` — the backend agent replaces this with `getAccessTokenSilently` from `@auth0/auth0-react` (or the Next.js equivalent) and every `api.*` call automatically attaches the Bearer token.

## Next steps (pass 2, after you review)

1. `/onboarding` (permissions → company profile → KB progress).
2. `/dashboard` + persistent sidebar shell, mobile bottom nav.
3. `/dashboard/meetings/$id` with the full Workflow Timeline in situ.
4. `/settings`, `/admin`.
5. WS event handling (`meeting_status_changed`, `workflow_log_appended`, `kb_progress`).
