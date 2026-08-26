# Cost Dashboard — Cloud Cost Lab

## Overview

The cost dashboard provides a visual interface for monitoring GCP cloud costs. It displays real-time data from the backend API with no hardcoded values.

## Pages

### `/` — Overview Dashboard
Main dashboard showing all cost metrics at a glance.

### `/cost` — Cost Explorer
Detailed cost analysis view (same layout, will be extended in future phases with filters).

## Components

### CostSummaryCard
Displays a single metric (current month, previous month, MoM change, projected cost, potential savings) with loading, error, and success states.

### CostTrendChart
Area chart showing daily cost over the last 30 days. Uses recharts with a gradient fill.

### BreakdownChart (ServiceCostChart, ProjectCostChart, EnvironmentCostChart)
Horizontal bar charts showing cost distribution by dimension. Each includes a legend with percentages.

## States

Every component handles four states:
1. **Loading** — skeleton placeholders
2. **Error** — red border with error message
3. **Empty** — centered "no data available" message
4. **Success** — rendered data with charts/values

## Data Flow

```
API (FastAPI :8000)
    ↓ fetch (no-store)
Client Components (useEffect)
    ↓ setState
Dashboard Components (render)
```

All data is fetched client-side using the `lib/api.ts` module. The API base URL is configured via `NEXT_PUBLIC_API_URL` environment variable (defaults to `http://localhost:8000`).

## Technology

- Next.js 16 (App Router)
- TypeScript (strict)
- Tailwind CSS
- shadcn/ui (Card, Skeleton)
- recharts (AreaChart, BarChart)

## API Integration

| Dashboard Section | API Endpoint |
|-------------------|-------------|
| Current Month / Previous Month / MoM | `GET /api/cost` |
| Daily Cost Trend | `GET /api/cost/trend` |
| Cost by Service | `GET /api/cost/by-service` |
| Cost by Project | `GET /api/cost/by-project` |
| Cost by Environment | `GET /api/cost/by-environment` |

## Running Locally

```bash
# Start API first
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Then start frontend
cd apps/web
npm run dev
```

Dashboard: http://localhost:3000

## Design Decisions

- Client-side fetching for dashboard interactivity (useEffect + useState)
- No hardcoded values — all data from API
- Responsive grid (1 col mobile, 2 col tablet, 5 col desktop for summary cards)
- Professional color palette with distinct colors per breakdown category
- Data freshness indicator at bottom of dashboard
- Minimal navigation header with links to Overview and Cost Explorer
