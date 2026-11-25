const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CostSummary {
  current_month_cost: number;
  previous_month_cost: number;
  mom_change_percent: number;
  average_daily_cost: number;
  projected_month_cost: number;
  month_length: number;
  potential_savings: number;
  currency: string;
  data_freshness: string;
  freshness_status: string;
  snapshot_label: string;
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

// Utilization

export interface UtilizationStats {
  avg: number | null;
  min: number | null;
  max: number | null;
  p95: number | null;
}

export interface UtilizationPattern {
  status: "low" | "high" | "unstable" | "normal" | "missing";
  evidence: string;
}

export interface ResourceUtilization {
  resource_id: string;
  name: string;
  service: string;
  environment: string;
  monthly_cost: number;
  cpu: UtilizationStats;
  memory: UtilizationStats;
  disk: UtilizationStats;
  cpu_pattern: UtilizationPattern;
  memory_pattern: UtilizationPattern;
}

export interface UtilizationSummaryResponse {
  period_start: string;
  period_end: string;
  total_resources: number;
  low_utilization_count: number;
  high_utilization_count: number;
  unstable_count: number;
  missing_metrics_count: number;
  resources: ResourceUtilization[];
}

export interface CostVsUtilData {
  resource_id: string;
  name: string;
  service: string;
  environment: string;
  cost: number;
  cpu_avg: number | null;
  memory_avg: number | null;
}

export interface CostVsUtilResponse {
  period_start: string;
  period_end: string;
  data: CostVsUtilData[];
}

export async function getUtilizationSummary(): Promise<UtilizationSummaryResponse> {
  return fetchApi<UtilizationSummaryResponse>("/api/utilization");
}

export async function getCostVsUtilization(): Promise<CostVsUtilResponse> {
  return fetchApi<CostVsUtilResponse>("/api/utilization/cost-vs-utilization/data");
}

// Recommendations

export interface Recommendation {
  id: string;
  title: string;
  resource_id: string;
  resource_name: string;
  service: string;
  environment: string;
  problem: string;
  evidence: string;
  recommendation: string;
  current_cost: number;
  potential_cost: number;
  potential_savings: number;
  savings_percentage: number;
  risk: "LOW" | "MEDIUM" | "HIGH";
  confidence: "LOW" | "MEDIUM" | "HIGH";
  effort: "LOW" | "MEDIUM" | "HIGH";
  priority: number;
  status: "OPEN" | "APPROVED" | "REJECTED" | "IMPLEMENTED" | "VERIFIED";
  approval_required: boolean;
}

export interface RecommendationsResponse {
  recommendations: Recommendation[];
  total: number;
}

export async function getRecommendations(): Promise<RecommendationsResponse> {
  return fetchApi<RecommendationsResponse>("/api/recommendations");
}

export async function getRecommendation(id: string): Promise<Recommendation> {
  return fetchApi<Recommendation>(`/api/recommendations/${encodeURIComponent(id)}`);
}

export interface BudgetAlert {
  severity: string;
  message: string;
  recommendation: string;
}

export interface BudgetStatus {
  budget: {
    id: string;
    name: string;
    scope: string;
    period: string;
    limit: number;
    warning_threshold: number;
    critical_threshold: number;
    currency: string;
  };
  current: {
    spend: number;
    utilization_pct: number;
    remaining: number;
    status: string;
  };
  projected: {
    spend: number;
    utilization_pct: number;
    status: string;
  };
  alerts: BudgetAlert[];
}

export interface ForecastPoint {
  date: string;
  expected: number;
  lower_bound: number;
  upper_bound: number;
  confidence: string;
}

export interface ForecastResponse {
  period_start?: string;
  period_end?: string;
  method?: string;
  forecast_days?: number;
  daily_forecast?: ForecastPoint[];
  monthly_summary?: {
    expected: number;
    lower_bound: number;
    upper_bound: number;
    range_description: string;
  };
  error?: string;
}

export async function getBudget(): Promise<BudgetStatus> {
  return fetchApi<BudgetStatus>("/api/budget");
}

export async function getForecast(): Promise<ForecastResponse> {
  return fetchApi<ForecastResponse>("/api/forecast");
}
