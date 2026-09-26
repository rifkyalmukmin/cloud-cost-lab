# Screenshots — capture guide

The 8 PNGs here were captured live from the running demo stack
(`docker compose up -d` + `npm run dev`, demo dataset). To refresh them:

1. Reset to a clean demo state: `cd apps/api && python -m costlab.seed --force`
2. Open each page at http://localhost:3000 and capture the full content area
   at 1440px width (no browser chrome):

| File | Page | Highlight to include |
| --- | --- | --- |
| 01-overview.png | `/` | MTD/prev/MoM cards, STALE chip, Potential Savings with live counts |
| 02-cost-explorer.png | `/cost` | Compute Engine filter + granularity switch |
| 03-resources.png | `/resources` | UNALLOCATED badge on the legacy sandbox row |
| 04-utilization.png | `/utilization` | Cost-vs-Utilization chart with 20%/80% lines |
| 05-recommendations.png | `/recommendations` | evidence badges + priority scores |
| 06-savings.png | `/savings` | Potential → Realized stage cards |
| 07-forecast.png | `/forecast` | expected line with shaded ~80% range |
| 08-budget.png | `/budget` | threshold markers + projected month-end |

Note: recommendation statuses reflect the current database; run the seed
reset (step 1) so statuses read OPEN for the portfolio shots.
