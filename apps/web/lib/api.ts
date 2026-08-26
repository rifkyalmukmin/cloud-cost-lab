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
