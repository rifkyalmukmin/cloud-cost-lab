# apps/web — Frontend Dashboard

Next.js + TypeScript (strict) + Tailwind CSS + shadcn/ui + Recharts frontend for Cloud Cost Lab.

**Status: Phase 2 IMPLEMENTED — Cost Dashboard.** Overview (`/`) and Cost Explorer (`/cost`), entirely powered by the Phase 1 API — no hardcoded numbers, no GCP access.

## Layout

```text
apps/web/
├── app/
│   ├── page.tsx            Overview: summary cards + daily trend + 3 breakdowns
│   ├── cost/page.tsx       Cost Explorer: filters, granularity switch, tables, pagination
│   └── layout.tsx          header/nav/footer, metadata, Geist fonts
├── components/
│   ├── cost/               CostSummaryCard, ChartCard, CostTrendChart,
│   │                       ServiceCostChart, ProjectCostChart, EnvironmentCostChart,
│   │                       EnvironmentBadge
│   ├── data-state.tsx      shared loading / error / empty / success states
│   └── site-header.tsx
├── hooks/use-api.ts        fetch-state hook (abortable, retryable)
├── lib/
│   ├── api.ts              typed API client (mirrors the FastAPI schemas)
│   ├── metrics.ts          MoM (MTD) + run-rate projection (pure, unit-tested)
│   ├── format.ts           USD / percent / date formatters
│   └── __tests__/          vitest tests for metrics (8)
└── vitest.config.ts
```

## Commands

```bash
npm run dev         # dev server (Turbopack)
npm run build       # production build (includes type check + ESLint)
npm run typecheck   # tsc --noEmit (strict)
npm run lint        # ESLint
npm test            # vitest (metrics unit tests)
```

Configuration: `NEXT_PUBLIC_API_URL` (inlined at build time — restart dev after changing). Set it in `.env.local` (git-ignored); see `/.env.example`. The backend must allow the dashboard origin via `CORS_ORIGINS` (default `http://localhost:3000`).

## Ground rules

- Every cost figure is fetched from the API — no hardcoded values in the UI.
- Every section implements loading / error / empty / success; errors surface the API message + request id with a retry button.
- Derived numbers (MoM, projection) are labelled as estimates; Potential Savings stays an honest empty state until Phase 4.
- Strict TypeScript; no `any`; ESLint clean.
