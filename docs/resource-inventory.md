# Resource Inventory — Cloud Cost Lab (Phase 3)

> Status: Implemented · Date: 2026-09-12
> Links cost to resources: `/api/resources` + `/api/resources/{id}` (FastAPI) and `/resources` + `/resources/{id}` (Next.js).

---

## 1. Objective

Phase 2 answered *where does cost go* (by service/project/environment). Phase 3 answers
*which specific resource does it belong to, and what is it doing* — the join between
billing lines, resource metadata, and utilization that every later optimization phase
(idle detection, rightsizing, storage hygiene) is built on.

## 2. Data model

`ResourceRecord` (CLAUDE.md §10) is stored in the `resources` table
(`apps/api/src/costlab/db/models.py`):

| Field | Column | Notes |
| --- | --- | --- |
| resource_id | `resources.resource_id` (PK) | mock ids like `vm-shop-api-prod-1` |
| name | `resource_name` | display name, separate from the id |
| type | `resource_type` | `vm_instance`, `sql_instance`, `storage_bucket`, … |
| project | FK → `projects` | |
| service | FK → `services` | |
| region / zone | `region`, `zone` | zone nullable (regional resources) |
| status | `status` | RUNNING / RUNNABLE / ACTIVE in the dataset |
| environment | `environment` | development / staging / production |
| owner / team / application | nullable columns | **never guessed** — see §6 |
| created_at / last_seen | nullable timestamps | |
| labels | JSONB | as they exist in the cloud provider |

Cost linkage: `cost_records.resource_id` (nullable — some billing lines are not
attributable to a single resource). Utilization linkage: `resource_usage.resource_id`
(one daily sample per resource, `cpu/memory/disk/network/requests` — all metrics
nullable because not every resource exposes every metric).

## 3. API

### `GET /api/resources`

Filtered, paginated inventory. Every item carries metadata + **monthly cost**
+ **latest utilization**.

- Filters: `project_id`, `service`, `region`, `environment`, `status`, `owner`,
  `team` (exact match), plus `unallocated=true` (only resources missing owner **or**
  team — the UNALLOCATED audit view).
- Pagination: `page` (1-based, ≥ 1), `page_size` (1–100, default 25). Response contains
  `pagination.{page, page_size, total_items, total_pages}`; a page beyond the end
  returns an empty `items` list, not an error.
- Response envelope: `window` (trailing 30-day cost window), `summary`
  (gross/credits/net for the **whole filtered set**, not just the current page),
  `items`.
- Ordering: `monthly_cost` DESC, then `resource_id` ASC (stable pagination).
- Validation: unknown `environment` values and `page=0` are rejected with `422`.

### `GET /api/resources/{resource_id}`

Full detail for one resource, `404` (structured error + request id) when unknown:

- identity + ownership + labels (same fields as the list item);
- `monthly_cost / monthly_credits / monthly_net_cost` — trailing 30-day window;
- `total_cost / total_net_cost` — all-time;
- `cost_history[]` — daily gross/credits/net for the full available range;
- `utilization[]` — daily CPU/memory/disk/network/requests series;
- `cpu_utilization` / `memory_utilization` — latest sample echoed at top level.

### Cost window convention

Monthly cost = trailing 30 days of cost data **anchored to the data itself**
(`max(usage_date) − 29 … max(usage_date)`), never the wall clock — the same
freshness philosophy as the Phase 2 cost endpoints (CLAUDE.md §4, §41).

## 4. Dashboard

### `/resources` — inventory

- Columns: Resource (name + id + ownership line), Type, Project, Region,
  Environment, Status, Monthly Cost, CPU, Memory, Potential Saving.
- Filter bar with the seven filter dimensions + an **UNALLOCATED only** checkbox;
  project/service options are fetched from the API (Phase 2 breakdowns), not hardcoded.
- Server-side pagination (10/25/50 rows per page) with Previous/Next controls.
- A header line shows the cost window and the filtered-set gross/net totals.
- Rows link to the detail view.

### `/resources/{id}` — detail view

- Header: name, id, status badge, environment badge, UNALLOCATED badge when owner/team missing.
- Summary cards: Monthly Cost (30d, with window), Credits (30d), Total Cost (all time), latest CPU/Memory meters.
- **Cost history** chart (daily gross, reuses the Phase 2 trend chart).
- **Utilization** chart (CPU % and memory % over time).
- **Ownership** card: owner, team, application — `UNALLOCATED` badge for missing values.
- **Metadata** card: type, service, project, region/zone, created, last seen.
- **Labels** card: `key=value` chips; an empty set is shown honestly as "No labels —
  this resource is unattributed."

## 5. Utilization-cost linkage conventions

- CPU/Memory in the inventory are the **latest daily sample**, not an average —
  marked as such in the docs and visible in the detail chart. Averages belong to the
  Phase 4 recommendation engine, where windows and evidence matter.
- Resources without the metric (e.g. storage buckets have no CPU) show `null` →
  rendered as "no data" — never `0`, never a guess.
- `potential_saving` is part of the API/UI contract but is **always `null` in
  Phase 3**: savings require the Phase 4 recommendation engine. The UI renders an
  explicit em-dash column rather than inventing numbers.

## 6. UNALLOCATED rule

Ownership is taken only from the resource's stored `owner` / `team` fields (which in
real mode would come from labels). When they are missing:

- the API returns `null` fields (never a guessed owner);
- the UI shows an `UNALLOCATED` badge (amber) instead of a name;
- the `unallocated=true` filter and the summary allow auditing exactly how much
  spend is unattributed.

This implements CLAUDE.md §12 ("If attribution is missing: UNALLOCATED. Never guess
ownership."). In the mock dataset, `vm-legacy-sandbox-1` is the unallocated resource.

## 7. Testing

`apps/api/tests/test_resources.py` (PostgreSQL test database, seeded with the mock
dataset — run `docker compose up -d postgres` first):

- filtering — each of the 7 dimensions individually, combined filters intersecting,
  exact-match owner/team;
- pagination — page sizes, total pages, page-disjointness, beyond-end empty,
  `page=0` rejected (422), summary equality across pages;
- invalid resource id — structured `404` with request id;
- empty results — unknown filter values return `200` with empty items and a zeroed summary;
- unallocated resources — filter finds the legacy sandbox VM, list + detail expose
  `null` ownership, monthly cost still tracked;
- linkage — monthly cost equals a trailing-window recomputation from the committed
  `data/mock/cost.json`; latest utilization equals the newest `data/mock/usage.json`
  sample; storage buckets expose no CPU;
- contract — all response fields present; `potential_saving` explicitly `null`;
  ordering by monthly cost DESC; summary covers the full filtered set.

Frontend: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.

## 8. Limitations

- Monthly cost is a trailing-30-day sum, not a calendar month — documented and shown
  as a window (`start → end`) in UI and API.
- Only the latest utilization sample reaches the list endpoint; per-resource averages
  and the cost↔utilization evidence views arrive with the Phase 4 recommendation engine.
- Resource metadata (status, machine type, created_at) comes from the mock snapshot;
  a live provider will need a discovery pipeline (Phase 9).
- No search-by-name yet (filters are exact match); add if needed for larger inventories.
