/**
 * Typed client for the Cloud Cost Lab API (Phase 1 contract).
 *
 * Types mirror `apps/api/src/costlab/schemas/cost.py` — when the API changes,
 * update them here. The only configuration is NEXT_PUBLIC_API_URL (see
 * `.env.example`); nothing else is hardcoded.
 */

export type Environment = "development" | "staging" | "production" | "UNALLOCATED";
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
  method: "GET" | "POST" = "GET",
  jsonBody?: unknown,
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
      method,
      headers: jsonBody === undefined ? { Accept: "application/json" } : {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: jsonBody === undefined ? undefined : JSON.stringify(jsonBody),
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
  listUtilization: (filters: UtilizationQueryFilters = {}) =>
    request<UtilizationListResponse>("/api/utilization", filters, buildUtilizationParams(filters)),
  getUtilization: (resourceId: string, filters: UtilizationQueryFilters = {}) =>
    request<UtilizationDetailResponse>(
      `/api/utilization/${encodeURIComponent(resourceId)}`,
      filters,
    ),
  listRecommendations: (filters: RecommendationFilters = {}) =>
    request<RecommendationListResponse>(
      "/api/recommendations",
      {},
      buildRecommendationParams(filters),
    ),
  getRecommendation: (id: string) =>
    request<RecommendationItem>(`/api/recommendations/${encodeURIComponent(id)}`),
  runRecommendationEngine: () =>
    // Recommendation mode only: regenerates rows in the backend's own database.
    request<RecommendationRunResponse>("/api/recommendations/run", {}, {}, "POST"),
  approveRecommendation: (id: string) =>
    request<{ id: string; status: string }>(
      `/api/recommendations/${encodeURIComponent(id)}/approve`,
      {},
      {},
      "POST",
    ),
  rejectRecommendation: (id: string) =>
    request<{ id: string; status: string }>(
      `/api/recommendations/${encodeURIComponent(id)}/reject`,
      {},
      {},
      "POST",
    ),
  listBudgets: () => request<BudgetListResponse>("/api/budget"),
  createBudget: (payload: BudgetCreate) =>
    request<BudgetOut>("/api/budget", {}, {}, "POST", payload),
  listPolicies: () => request<PolicyListResponse>("/api/policies"),
  getFreshness: () => request<FreshnessResponse>("/api/freshness"),
  getForecast: (filters: ForecastFilters = {}) =>
    request<ForecastResponse>("/api/forecast", {}, buildForecastParams(filters)),
  listAnomalies: (filters: AnomalyFilters = {}) =>
    request<AnomalyListResponse>("/api/anomalies", {}, buildAnomalyParams(filters)),
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
  connections: number | null;
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

// ---------------------------------------------------------------------------
// Utilization analytics (Phase 4) — evidence only, no recommendations
// ---------------------------------------------------------------------------

/** Stats for one metric over the window. A metric with no samples at all is
 * missing (never 0) and is listed in `missingMetrics` instead. */
export interface UtilizationMetricStats {
  avg: number;
  min: number;
  max: number;
  p95: number;
  stddev: number | null;
  sample_count: number;
}

/** Heuristic evidence flags computed from CPU utilization; null when the
 * resource has no CPU samples, so "no signal" ≠ "signal false". */
export interface EvidenceSignals {
  low_utilization: boolean | null;
  high_utilization: boolean | null;
  unstable_utilization: boolean | null;
}

export interface SignalCounts {
  low_utilization: number;
  high_utilization: number;
  unstable_utilization: number;
  missing_cpu: number;
}

export interface UtilizationItem {
  resource_id: string;
  resource_name: string;
  resource_type: string;
  service_id: string;
  service_name: string;
  project_id: string;
  project_name: string;
  environment: Environment;
  region: string;
  window: Period;
  metrics: Record<string, UtilizationMetricStats>;
  missing_metrics: string[];
  avg_cpu: number | null;
  cost_in_window: number | null;
  cost_credits_in_window: number | null;
  cost_net_in_window: number | null;
  signals: EvidenceSignals;
}

export interface UtilizationListResponse {
  window: Period | null;
  pagination: Pagination;
  signal_counts: SignalCounts;
  items: UtilizationItem[];
}

export interface UtilizationDetailResponse extends UtilizationItem {
  machine_type: string | null;
  series: UtilizationPoint[];
}

/** Filters accepted by the /api/utilization endpoints. */
export interface UtilizationQueryFilters {
  startDate?: string;
  endDate?: string;
  projectId?: string;
  service?: string;
  environment?: Environment;
  page?: number;
  pageSize?: number;
}

function buildUtilizationParams(filters: UtilizationQueryFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.startDate) params["start_date"] = filters.startDate;
  if (filters.endDate) params["end_date"] = filters.endDate;
  if (filters.projectId) params["project_id"] = filters.projectId;
  if (filters.service) params["service"] = filters.service;
  if (filters.environment) params["environment"] = filters.environment;
  if (filters.page) params["page"] = String(filters.page);
  if (filters.pageSize) params["page_size"] = String(filters.pageSize);
  return params;
}

// ---------------------------------------------------------------------------
// Recommendations (Phase 5) — evidence-backed, human-approved
// ---------------------------------------------------------------------------

export type RecommendationStatus = "OPEN" | "APPROVED" | "REJECTED" | "IMPLEMENTED" | "VERIFIED";

export interface RecommendationEvidenceItem {
  statement: string;
  metric: string | null;
  value: number | null;
  threshold: number | null;
  unit: string | null;
}

export interface RecommendationItem {
  id: string;
  rule_id: string;
  title: string;
  resource_id: string | null;
  resource_label: string;
  project_id: string | null;
  service_id: string | null;
  problem: string;
  evidence: RecommendationEvidenceItem[];
  recommendation: string;
  current_cost: number;
  potential_cost: number;
  potential_savings: number;
  savings_percentage: number;
  risk: "LOW" | "MEDIUM" | "HIGH";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  effort: "LOW" | "MEDIUM" | "HIGH";
  priority_score: number;
  priority: "HIGH" | "MEDIUM" | "LOW";
  approval_required: boolean;
  status: RecommendationStatus;
  window: Period | null;
  created_at: string;
  updated_at: string;
}

export interface RecommendationSummary {
  by_status: Record<RecommendationStatus, number>;
  open_potential_savings: number;
}

export interface RecommendationListResponse {
  summary: RecommendationSummary;
  pagination: Pagination;
  items: RecommendationItem[];
}

export interface RecommendationRunResponse {
  generated: number;
  status_preserved: number;
  removed: number;
}

export interface RecommendationFilters {
  status?: RecommendationStatus;
  ruleId?: string;
  risk?: "LOW" | "MEDIUM" | "HIGH";
  priority?: "HIGH" | "MEDIUM" | "LOW";
  resourceId?: string;
  projectId?: string;
  sort?: "priority" | "savings" | "recent";
  page?: number;
  pageSize?: number;
}

function buildRecommendationParams(filters: RecommendationFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.status) params["status"] = filters.status;
  if (filters.ruleId) params["rule_id"] = filters.ruleId;
  if (filters.risk) params["risk"] = filters.risk;
  if (filters.priority) params["priority"] = filters.priority;
  if (filters.resourceId) params["resource_id"] = filters.resourceId;
  if (filters.projectId) params["project_id"] = filters.projectId;
  if (filters.sort) params["sort"] = filters.sort;
  if (filters.page) params["page"] = String(filters.page);
  if (filters.pageSize) params["page_size"] = String(filters.pageSize);
  return params;
}

// ---------------------------------------------------------------------------
// Budget & governance (Phase 6)
// ---------------------------------------------------------------------------

export type BudgetStatus = "HEALTHY" | "WARNING" | "CRITICAL" | "EXCEEDED";
export type PolicyStatus = "PASS" | "WARNING" | "VIOLATION";

export interface SpendPeriod {
  start: string;
  end: string;
  days_elapsed: number;
  days_in_month: number;
}

export interface SpendOut {
  amount: number;
  gross_amount: number;
  daily_average: number;
  period: SpendPeriod;
}

export interface BudgetOut {
  id: string;
  name: string;
  scope_type: "all" | "project" | "service" | "environment";
  scope_value: string | null;
  period: string;
  limit: number;
  warning_threshold: number;
  critical_threshold: number;
  status: BudgetStatus | null;
  spend: SpendOut | null;
  remaining: number | null;
  spend_percentage: number | null;
  projected_month_end: number | null;
  forecast_over_budget: boolean | null;
}

export interface BudgetSummary {
  evaluation_month: string | null;
  data_end: string | null;
  budget_count: number;
  by_status: Record<BudgetStatus, number>;
  forecast_over_budget_count: number;
}

export interface BudgetListResponse {
  summary: BudgetSummary;
  budgets: BudgetOut[];
}

export interface BudgetCreate {
  name: string;
  scope_type: "all" | "project" | "service" | "environment";
  scope_value?: string | null;
  period?: "monthly";
  limit: number;
  warning_threshold: number;
  critical_threshold: number;
}

export interface PolicyFinding {
  resource_id: string | null;
  resource_name: string;
  detail: string;
}

export interface PolicyOut {
  policy_id: string;
  name: string;
  description: string;
  enabled: boolean;
  config: Record<string, string | number>;
  status: PolicyStatus;
  summary: string;
  findings: PolicyFinding[];
}

export interface PolicySummary {
  policy_count: number;
  by_status: Record<PolicyStatus, number>;
  finding_count: number;
}

export interface PolicyListResponse {
  summary: PolicySummary;
  policies: PolicyOut[];
}

// ---------------------------------------------------------------------------
// Forecasting & anomaly detection (Phase 7)
// ---------------------------------------------------------------------------

export interface ForecastPoint {
  date: string;
  moving_average: number;
  linear_trend: number;
  expected: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastTotals {
  expected_30d: number;
  lower_bound_30d: number;
  upper_bound_30d: number;
}

export interface ForecastResponse {
  sufficient_data: boolean;
  message: string | null;
  history_days: number;
  horizon_days: number;
  history: { start: string; end: string; daily_average: number } | null;
  methods: Record<string, Record<string, number>> | null;
  trend: "increasing" | "decreasing" | "stable" | null;
  interval: string | null;
  confidence: "HIGH" | "MEDIUM" | "LOW" | null;
  forecast: ForecastPoint[];
  totals: ForecastTotals | null;
}

export interface ForecastFilters {
  horizonDays?: number;
  projectId?: string;
  service?: string;
  environment?: Environment;
}

function buildForecastParams(filters: ForecastFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.horizonDays) params["horizon_days"] = String(filters.horizonDays);
  if (filters.projectId) params["project_id"] = filters.projectId;
  if (filters.service) params["service"] = filters.service;
  if (filters.environment) params["environment"] = filters.environment;
  return params;
}

export interface AnomalyItem {
  date: string;
  project_id: string;
  project_name: string;
  service_id: string;
  service_name: string;
  resource_id: string | null;
  resource_name: string | null;
  actual: number;
  expected: number;
  difference: number;
  percentage_change: number;
  z_score: number | null;
  severity: "LOW" | "MEDIUM" | "HIGH";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  baseline_samples: number;
}

export interface AnomalySummary {
  total: number;
  by_severity: Record<"LOW" | "MEDIUM" | "HIGH", number>;
  by_service: Record<string, number>;
}

export interface AnomalyListResponse {
  summary: AnomalySummary;
  pagination: Pagination;
  items: AnomalyItem[];
}

export interface AnomalyFilters {
  minZScore?: number;
  severity?: "LOW" | "MEDIUM" | "HIGH";
  projectId?: string;
  service?: string;
  environment?: Environment;
  resourceId?: string;
  page?: number;
  pageSize?: number;
}

function buildAnomalyParams(filters: AnomalyFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.minZScore) params["min_z_score"] = String(filters.minZScore);
  if (filters.severity) params["severity"] = filters.severity;
  if (filters.projectId) params["project_id"] = filters.projectId;
  if (filters.service) params["service"] = filters.service;
  if (filters.environment) params["environment"] = filters.environment;
  if (filters.resourceId) params["resource_id"] = filters.resourceId;
  if (filters.page) params["page"] = String(filters.page);
  if (filters.pageSize) params["page_size"] = String(filters.pageSize);
  return params;
}

// ---------------------------------------------------------------------------
// Data freshness (Phase 8, CLAUDE.md §41)
// ---------------------------------------------------------------------------

export interface FreshnessResponse {
  status: "FRESH" | "STALE" | "UNKNOWN";
  last_updated: string | null;
  data_age_hours: number | null;
  max_age_hours: number;
}
