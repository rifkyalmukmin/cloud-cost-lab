/**
 * Typed client for the Cloud Cost Lab API (Phase 1 contract).
 *
 * Types mirror `apps/api/src/costlab/schemas/cost.py` — when the API changes,
 * update them here. The only configuration is NEXT_PUBLIC_API_URL (see
 * `.env.example`); nothing else is hardcoded.
 */

export type Environment = "development" | "staging" | "production";
export type Granularity = "day" | "week" | "month";

export interface Period {
  start: string;
  end: string;
}

export interface CostSummary {
  cost: number;
  credits: number;
  net_cost: number;
}

export interface TrendPoint {
  period: string;
  cost: number;
  credits: number;
  net_cost: number;
}

export interface TrendResponse {
  period: Period;
  granularity: Granularity;
  points: TrendPoint[];
}

export interface ServiceBreakdownRow {
  service: string;
  service_name: string;
  cost: number;
  credits: number;
  net_cost: number;
  share_pct: number;
}

export interface ServiceBreakdownResponse {
  period: Period;
  total: CostSummary;
  rows: ServiceBreakdownRow[];
}

export interface ProjectBreakdownRow {
  project_id: string;
  project_name: string;
  cost: number;
  credits: number;
  net_cost: number;
  share_pct: number;
}

export interface ProjectBreakdownResponse {
  period: Period;
  total: CostSummary;
  rows: ProjectBreakdownRow[];
}

export interface EnvironmentBreakdownRow {
  environment: Environment;
  cost: number;
  credits: number;
  net_cost: number;
  share_pct: number;
}

export interface EnvironmentBreakdownResponse {
  period: Period;
  total: CostSummary;
  rows: EnvironmentBreakdownRow[];
}

export interface CostRecord {
  usage_date: string;
  project_id: string;
  service: string;
  service_name: string;
  resource_id: string | null;
  sku: string;
  region: string;
  environment: Environment;
  usage_amount: number;
  usage_unit: string;
  cost: number;
  credits: number;
  net_cost: number;
  currency: string;
  labels: Record<string, string>;
}

export interface Pagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface CostRecordsResponse {
  period: Period;
  pagination: Pagination;
  summary: CostSummary;
  items: CostRecord[];
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  demo_mode: boolean;
}

/** Filters accepted by every /api/cost endpoint (server-side, validated by the API). */
export interface CostFilters {
  startDate?: string;
  endDate?: string;
  projectId?: string;
  service?: string;
  environment?: Environment;
  region?: string;
  page?: number;
  pageSize?: number;
}

export class ApiError extends Error {
  readonly status: number;
  readonly requestId: string | null;

  constructor(status: number, message: string, requestId: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
  }
}

export function apiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    throw new ApiError(0, "NEXT_PUBLIC_API_URL is not configured (see .env.example).");
  }
  return base.replace(/\/$/, "");
}

function buildFilterParams(filters: CostFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.startDate) params["start_date"] = filters.startDate;
  if (filters.endDate) params["end_date"] = filters.endDate;
  if (filters.projectId) params["project_id"] = filters.projectId;
  if (filters.service) params["service"] = filters.service;
  if (filters.environment) params["environment"] = filters.environment;
  if (filters.region) params["region"] = filters.region;
  if (filters.page) params["page"] = String(filters.page);
  if (filters.pageSize) params["page_size"] = String(filters.pageSize);
  return params;
}

async function request<T>(
  path: string,
  filters: CostFilters = {},
  extraParams: Record<string, string> = {},
): Promise<T> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(buildFilterParams(filters))) {
    params.set(key, value);
  }
  for (const [key, value] of Object.entries(extraParams)) {
    params.set(key, value);
  }
  const query = params.size ? `?${params.toString()}` : "";
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}${query}`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch {
    // Network/DNS/CORS failure — surface a single actionable message.
    throw new ApiError(0, `Cannot reach the API at ${apiBaseUrl()}. Is the backend running (docker compose up -d)?`);
  }
  if (!response.ok) {
    let message = `API error ${response.status}`;
    let requestId: string | null = null;
    try {
      const body = (await response.json()) as { error?: { message?: string; request_id?: string | null } };
      if (body.error?.message) message = body.error.message;
      requestId = body.error?.request_id ?? null;
    } catch {
      // non-JSON error body — keep the generic message
    }
    throw new ApiError(response.status, message, requestId);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  costTrend: (filters: CostFilters, granularity: Granularity) =>
    request<TrendResponse>("/api/cost/trend", filters, { granularity }),
  costByService: (filters: CostFilters) => request<ServiceBreakdownResponse>("/api/cost/by-service", filters),
  costByProject: (filters: CostFilters) => request<ProjectBreakdownResponse>("/api/cost/by-project", filters),
  costByEnvironment: (filters: CostFilters) =>
    request<EnvironmentBreakdownResponse>("/api/cost/by-environment", filters),
  listCostRecords: (filters: CostFilters) => request<CostRecordsResponse>("/api/cost", filters),
  listResources: (filters: ResourceFilters = {}) =>
    request<ResourceListResponse>("/api/resources", {}, buildResourceParams(filters)),
  getResource: (resourceId: string) =>
    request<ResourceDetailResponse>(`/api/resources/${encodeURIComponent(resourceId)}`),
};

// ---------------------------------------------------------------------------
// Resource inventory (Phase 3)
// ---------------------------------------------------------------------------

export interface ResourceWindow {
  start: string;
  end: string;
}

export interface ResourceCostSummary {
  monthly_cost: number;
  monthly_credits: number;
  monthly_net_cost: number;
}

/** Monthly cost covers a trailing 30-day window anchored to the data.
 * potential_saving stays null until the Phase 4 recommendation engine exists. */
export interface ResourceItem {
  resource_id: string;
  resource_name: string;
  resource_type: string;
  service_id: string;
  service_name: string;
  project_id: string;
  project_name: string;
  region: string;
  zone: string | null;
  status: string;
  environment: Environment;
  machine_type: string | null;
  owner: string | null;
  team: string | null;
  application: string | null;
  labels: Record<string, string>;
  created_at: string | null;
  last_seen: string | null;
  monthly_cost: number | null;
  monthly_credits: number | null;
  monthly_net_cost: number | null;
  cpu_utilization: number | null;
  memory_utilization: number | null;
  potential_saving: null;
}

export interface ResourceListResponse {
  window: ResourceWindow | null;
  pagination: Pagination;
  summary: ResourceCostSummary | null;
  items: ResourceItem[];
}

export interface CostHistoryPoint {
  date: string;
  cost: number;
  credits: number;
  net_cost: number;
}

export interface UtilizationPoint {
  date: string;
  cpu_utilization: number | null;
  memory_utilization: number | null;
  disk_utilization: number | null;
  network_in_mb: number | null;
  network_out_mb: number | null;
  request_count: number | null;
  error_rate_pct: number | null;
}

export interface ResourceDetailResponse extends Omit<ResourceItem, "potential_saving"> {
  potential_saving: null;
  window: ResourceWindow | null;
  total_cost: number | null;
  total_net_cost: number | null;
  cost_history: CostHistoryPoint[];
  utilization: UtilizationPoint[];
}

export interface ResourceFilters {
  projectId?: string;
  service?: string;
  region?: string;
  environment?: Environment;
  status?: string;
  owner?: string;
  team?: string;
  unallocated?: boolean;
  page?: number;
  pageSize?: number;
}

function buildResourceParams(filters: ResourceFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.projectId) params["project_id"] = filters.projectId;
  if (filters.service) params["service"] = filters.service;
  if (filters.region) params["region"] = filters.region;
  if (filters.environment) params["environment"] = filters.environment;
  if (filters.status) params["status"] = filters.status;
  if (filters.owner) params["owner"] = filters.owner;
  if (filters.team) params["team"] = filters.team;
  if (filters.unallocated) params["unallocated"] = "true";
  if (filters.page) params["page"] = String(filters.page);
  if (filters.pageSize) params["page_size"] = String(filters.pageSize);
  return params;
}
