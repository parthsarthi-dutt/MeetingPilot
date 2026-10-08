# Porting to Next.js App Router

The frontend is built on TanStack Start because Lovable's runtime requires it. Everything below `src/lib/` and `src/components/` is framework-agnostic and moves without change. Only `src/routes/` needs a mechanical rewrite.

## What moves as-is

- `src/lib/api/*` — types, mock data, client. `import.meta.env.VITE_*` → `process.env.NEXT_PUBLIC_*` (rename only).
- `src/components/mp/*` — Workflow Timeline, StatusBadge, CaseCard. Zero router coupling.
- `src/components/ui/*` — shadcn primitives, unchanged.
- `src/styles.css` — Tailwind v4 tokens. Import from `app/layout.tsx` instead of a route.
- `.env.example` — rename `VITE_*` → `NEXT_PUBLIC_*` where the value must reach the browser; server-only vars stay unprefixed.

## Route mapping

| TanStack file                             | Next.js App Router path         |
| ----------------------------------------- | ------------------------------- |
| `src/routes/__root.tsx`                   | `app/layout.tsx`                |
| `src/routes/index.tsx`                    | `app/page.tsx`                  |
| `src/routes/style-guide.tsx`              | `app/style-guide/page.tsx`      |
| `src/routes/onboarding.tsx`               | `app/onboarding/page.tsx`       |
| `src/routes/dashboard.tsx` (layout)       | `app/dashboard/layout.tsx`      |
| `src/routes/dashboard.index.tsx`          | `app/dashboard/page.tsx`        |
| `src/routes/dashboard.meetings.$id.tsx`   | `app/dashboard/meetings/[id]/page.tsx` |
| `src/routes/settings.tsx`                 | `app/settings/page.tsx`         |
| `src/routes/admin.tsx`                    | `app/admin/page.tsx`            |

## Navigation swaps

- `import { Link } from "@tanstack/react-router"` → `import Link from "next/link"` (prop `to=` → `href=`).
- `useNavigate()` (TanStack) → `useRouter()` from `next/navigation`, `router.push(...)`.
- `head: () => ({ meta, links })` in each route → export `metadata: Metadata` from the equivalent `page.tsx` / `layout.tsx`.

## Auth0

- Replace the stub in `src/lib/api/client.ts`:
  ```ts
  import { getAccessToken } from "@auth0/nextjs-auth0";
  setAuthTokenGetter(async () => (await getAccessToken()).accessToken ?? null);
  ```
- Wrap `app/layout.tsx` in `<UserProvider />` from `@auth0/nextjs-auth0/client`.
- Callback: `app/api/auth/[auth0]/route.ts` (see Auth0 Next.js quickstart).

## SSR / fonts

`next/font/google` replaces the `<link rel="stylesheet" href="fonts.googleapis...">` block in `__root.tsx`. Import Instrument Serif, Public Sans, IBM Plex Mono there and expose them as CSS variables matching `--font-display`, `--font-sans`, `--font-mono` — components then need no changes.
