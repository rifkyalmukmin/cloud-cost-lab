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
};
