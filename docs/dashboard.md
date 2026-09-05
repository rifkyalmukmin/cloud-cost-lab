# Cost Dashboard — Cloud Cost Lab (Phase 2)

> Status: Implemented · Date: 2026-09-05
> The web dashboard (`apps/web`) — Next.js + TypeScript (strict) + Tailwind CSS + shadcn/ui + Recharts.

---

## 1. What it shows

### `/` — Overview

| Section | Source | Notes |
| --- | --- | --- |
| Current Month Cost | `/api/cost/trend?granularity=month` + `granularity=day` | month-to-date of the **latest month in the data**, labelled `MTD · N days` |
| Previous Month Cost | monthly trend | full previous month, gross + net after credits |
| MoM Change | derived (`lib/metrics.ts`) | **MTD vs prior MTD** — the same number of days on both sides; comparing a partial month to a full month would produce a misleading drop |
| Projected Month-End | derived | linear run-rate: `MTD / days elapsed × days in month`, always badged **estimate** |
| Potential Savings | — | deliberately empty (`Phase 4` badge): the recommendation engine does not exist yet, so no honest savings number can be shown |
| Daily cost trend | `/api/cost/trend?granularity=day` | full available range; the Compute +35% spike week and the elevated September run-rate are visible |
| Cost by Service | `/api/cost/by-service` | donut with share in legend |
| Cost by Project | `/api/cost/by-project` | bar chart |
| Cost by Environment | `/api/cost/by-environment` | bar chart with fixed semantic colors |

### `/cost` — Cost Explorer

- Filters: start/end date, service, project, environment — the option lists are **fetched from the API** (full-range breakdowns), not hardcoded.
- Cost trend with daily / weekly / monthly switch.
- By-Service / By-Project / By-Environment tables, respecting the active filters.
- Cost records table: newest first, **server-side pagination** (`page`, `page_size` 10/25/50), environment badges, gross + net columns.

## 2. Data flow and states

- Every number comes from the Phase 1 API via the typed client `lib/api.ts` (types mirror `apps/api/src/costlab/schemas/cost.py`). There are **no hardcoded cost values** anywhere in the UI.
- `hooks/use-api.ts` gives every section the same four states: **loading** (skeleton), **error** (destructive alert with the API error message + request id + retry button), **empty** (dashed placeholder with hint), **success**. Refetches dim the existing data instead of flashing skeletons.
- The dashboard degrades gracefully: with the backend down, each section shows the error state with a hint to start the stack — the page itself still renders.

## 3. Honest-metrics rules (CLAUDE.md §4)

- "Current month" = the latest month **in the data**, not the wall clock (mock data is date-anchored; real billing data always lags).
- Projections and MoM values are labelled *estimate* / *MTD vs prior MTD*; nothing is presented as exact or realized.
- Potential Savings is intentionally an empty state until Phase 4 delivers real recommendation data.

## 4. Running it

```bash
# backend (Phase 1)
cp .env.example .env && docker compose up -d

# frontend
cd apps/web
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local   # already git-ignored
npm install
npm run dev          # http://localhost:3000
```

The API allows browser origins via `CORS_ORIGINS` (backend env, default `http://localhost:3000`, GET-only). `NEXT_PUBLIC_API_URL` is inlined by Next.js at build time — restart `next dev` after changing it.

## 5. Validation performed

- `npm run build` (Next.js production build, type check + ESLint included) — clean.
- `npm run typecheck` (tsc --noEmit, strict) — clean.
- `npm run lint` (ESLint) — clean. `npm test` (vitest) — 8 tests on the derived metrics (MoM MTD math, run-rate projection, month lengths, edge cases).
- Backend: 41 pytest tests including two CORS tests (allowed origin echoes header, unknown origin gets none).
- Browser verification: both pages render with live API data; filter → Cloud SQL shows 194 records ($60.82 gross / $58.33 net — matches the API exactly); pagination `Page 2 of 8`; reset restores 1,164 records; console error collector reported **zero errors**; mobile (390px) stacks to a single column with no overflow.

## 6. Trade-offs accepted

| Decision | Trade-off |
| --- | --- |
| Client-side fetching (not server components) | `next build` stays hermetic — it never calls the API, so CI builds work without a database. Cost: first paint shows skeletons, no SSR data. |
| Derived metrics in the frontend | Keeps the Phase 1 API contract untouched (no duplicate/overlapping endpoints); forecasting done properly arrives in Phase 6. |
| shadcn/ui + Recharts | Accessible primitives + composable charts; chart palette fixed to distinct hues (the default neutral theme made donut slices indistinguishable). |
| Radix Select labels wired via `htmlFor`/`id` | Screen-reader accessible names and stable test locators (`getByRole("combobox", { name: "Service" })`). |
