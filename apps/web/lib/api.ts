const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CostSummary {
  current_month_cost: number;
  previous_month_cost: number;
  mom_change_percent: number;
  average_daily_cost: number;
  projected_month_cost: number;
  potential_savings: number;
  currency: string;
  data_freshness: string;
}

export interface DailyCost {
  date: string;
  cost: number;
  net_cost: number;
}

export interface CostTrendResponse {
  daily_costs: DailyCost[];
  period_start: string;
  period_end: string;
  total_cost: number;
}

export interface CostByDimension {
  dimension: string;
  value: string;
  total_cost: number;
  net_cost: number;
  percentage: number;
}

export interface CostBreakdownResponse {
  breakdown: CostByDimension[];
  total_cost: number;
  period_start: string;
  period_end: string;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new ApiError(res.status, `API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function getCostSummary(): Promise<CostSummary> {
  return fetchApi<CostSummary>("/api/cost");
}

export async function getCostTrend(): Promise<CostTrendResponse> {
  return fetchApi<CostTrendResponse>("/api/cost/trend");
}

export async function getCostByService(): Promise<CostBreakdownResponse> {
  return fetchApi<CostBreakdownResponse>("/api/cost/by-service");
}

export async function getCostByProject(): Promise<CostBreakdownResponse> {
  return fetchApi<CostBreakdownResponse>("/api/cost/by-project");
}

export async function getCostByEnvironment(): Promise<CostBreakdownResponse> {
  return fetchApi<CostBreakdownResponse>("/api/cost/by-environment");
}

// Resources

export interface ResourceListItem {
  resource_id: string;
  name: string;
  type: string;
  project: string;
  service: string;
  region: string;
  zone: string | null;
  environment: string;
  status: string;
  owner: string;
  team: string;
  application: string;
  monthly_cost: number;
  cpu_utilization: number | null;
  memory_utilization: number | null;
  potential_saving: number;
}

export interface ResourceListResponse {
  data: ResourceListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UtilizationRecord {
  date: string;
  cpu_utilization: number | null;
  memory_utilization: number | null;
  disk_utilization: number | null;
  network_in_mb: number;
  network_out_mb: number;
}

export interface CostHistoryRecord {
  date: string;
  cost: number;
}

export interface ResourceDetail {
  resource_id: string;
  name: string;
  type: string;
  project: string;
  service: string;
  service_id: string;
  region: string;
  zone: string | null;
  environment: string;
  status: string;
  owner: string;
  team: string;
  application: string;
  labels: Record<string, string>;
  created_at: string;
  last_seen: string;
  monthly_cost: number;
  potential_saving: number;
  utilization: {
    cpu_avg: number | null;
    memory_avg: number | null;
    disk_avg: number | null;
  };
  utilization_history: UtilizationRecord[];
  cost_history: CostHistoryRecord[];
}

export async function getResources(params?: {
  page?: number;
  page_size?: number;
  environment?: string;
  project?: string;
  service?: string;
  owner?: string;
}): Promise<ResourceListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.environment) searchParams.set("environment", params.environment);
  if (params?.project) searchParams.set("project", params.project);
  if (params?.service) searchParams.set("service", params.service);
  if (params?.owner) searchParams.set("owner", params.owner);
  const qs = searchParams.toString();
  return fetchApi<ResourceListResponse>(`/api/resources${qs ? `?${qs}` : ""}`);
}

export async function getResource(resourceId: string): Promise<ResourceDetail> {
  return fetchApi<ResourceDetail>(`/api/resources/${encodeURIComponent(resourceId)}`);
}
