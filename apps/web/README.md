# apps/web — Frontend Dashboard

Next.js 15 (App Router) + React 19 + TypeScript (strict) + Tailwind CSS 4 +
shadcn/ui + Recharts frontend for Cloud Cost Lab. Every number comes from the
API in `apps/api`; no GCP access is needed (demo mode).

**Status: implemented** for the pages listed below. Not implemented: `/reports`,
`/ai` (the read-only AI advisor exists in the API as `POST /api/ai/advisor` but
has no UI page), `/settings`, and an audit-log view (the API client has
`listAuditLogs`, no page uses it yet).

## Pages

| Route | Content |
| --- | --- |
| `/` | Overview: cost summary cards (MoM, projected month-end), daily trend, breakdowns, potential savings estimate |
| `/cost` | Cost Explorer: filters, daily/weekly/monthly switch, breakdown tables, pagination |
| `/resources`, `/resources/[resource_id]` | Inventory with monthly cost and utilization; detail page per resource |
| `/utilization` | Per-resource utilization signals and cost-vs-utilization scatter |
| `/recommendations`, `/recommendations/[id]` | List with "run engine" (API key); detail with evidence, savings, risk, priority and approve / reject / implement / verify (API key) |
| `/savings` | Potential vs verified savings |
| `/forecast` | 30-day forecast with a range |
| `/anomalies` | Detected cost anomalies |
| `/budget` | Budgets, thresholds, status (creating a budget needs an API key) |
| `/policies` | Policy results: PASS / WARNING / VIOLATION |

## Layout

```text
apps/web/
├── app/                    App Router pages (one directory per route above) + layout.tsx
├── components/
│   ├── cost/               ChartCard, CostSummaryCard, trend/service/project/environment charts
│   ├── recommendations/    recommendation UI pieces
│   ├── resources/          resource UI pieces, utilization chart
│   ├── utilization/        cost-utilization scatter, signal UI
│   ├── ui/                 shadcn/ui primitives
│   ├── api-key-control.tsx header control for the write API key
│   ├── data-state.tsx      shared loading / error / empty / success states
│   └── site-header.tsx     navigation
├── hooks/use-api.ts        fetch-state hook (abortable, retryable)
├── lib/
│   ├── api.ts              typed API client (mirrors the FastAPI schemas)
│   ├── api-key.ts          write API key (sessionStorage, see below)
│   ├── metrics.ts          MoM (MTD) + run-rate projection (pure, unit-tested)
│   ├── format.ts           USD / percent / date formatters
│   └── __tests__/          vitest unit tests (metrics)
└── vitest.config.ts
```

Data fetching currently goes through `hooks/use-api.ts`. A migration to
React Query, an `error.tsx` boundary and a mobile navigation are in progress in a
separate change; re-check this section after it merges.

## Commands

All defined in `package.json`:

```bash
npm ci              # install exactly what package-lock.json pins
npm run dev         # dev server (Turbopack)
npm run build       # production build (Turbopack; includes type check + ESLint)
npm run start       # serve the production build
npm run typecheck   # tsc --noEmit (strict)
npm run lint        # ESLint
npm test            # vitest run (unit tests for lib/metrics)
```

CI (`.github/workflows/ci.yml`, job `web`) runs `npm ci`, lint, typecheck, test
and build. There is no Dockerfile or compose service for the web app; run it with
npm next to the API (`docker compose up -d` starts only postgres + api).

## Configuration

- `NEXT_PUBLIC_API_URL` — API base URL (default in `.env.example`:
  `http://localhost:8000`). It is **inlined at build time**: restart `npm run dev`
  after changing it. Put it in `.env.local` (git-ignored) or export it.
- The API must allow the dashboard origin via `CORS_ORIGINS` (default
  `http://localhost:3000`).

### Write API key

Write actions (run the engine, approve/reject/implement/verify, create a budget)
need an `X-API-Key` that matches the API's `API_KEYS`. The dashboard header has an
API-key control; the key is kept in `sessionStorage` for the current tab only and
is sent only on write requests. It is deliberately **not** a `NEXT_PUBLIC_*`
variable, which would publish the credential in the JavaScript bundle. Without a
key the dashboard is read-only. See [`docs/security.md`](../../docs/security.md).

## Ground rules

- Every cost figure is fetched from the API — no hardcoded values in the UI.
- Every section implements loading / error / empty / success; errors surface the
  API message + request id with a retry button.
- Derived numbers (MoM, projection) are labelled as estimates; savings are
  *potential* until verified after a change.
- Strict TypeScript; no `any`; ESLint clean.
