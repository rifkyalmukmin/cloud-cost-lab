"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { UtilizationTable } from "./utilization-table";
import { CostVsUtilChart } from "./cost-vs-util-chart";
import type { UtilizationSummaryResponse, CostVsUtilResponse } from "@/lib/api";
import { getUtilizationSummary, getCostVsUtilization } from "@/lib/api";

export function UtilizationContent() {
  const [summary, setSummary] = useState<UtilizationSummaryResponse | null>(null);
  const [costVsUtil, setCostVsUtil] = useState<CostVsUtilResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(false);
        const [s, cvu] = await Promise.all([
          getUtilizationSummary(),
          getCostVsUtilization(),
        ]);
        setSummary(s);
        setCostVsUtil(cvu);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="text-xs text-muted-foreground">Total Resources</div>
            <div className="text-2xl font-bold">
              {loading ? "—" : summary?.total_resources ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-xs text-muted-foreground">Low Utilization</div>
            <div className="text-2xl font-bold text-amber-600">
              {loading ? "—" : summary?.low_utilization_count ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-xs text-muted-foreground">High Utilization</div>
            <div className="text-2xl font-bold text-red-600">
              {loading ? "—" : summary?.high_utilization_count ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-xs text-muted-foreground">Unstable</div>
            <div className="text-2xl font-bold text-orange-600">
              {loading ? "—" : summary?.unstable_count ?? 0}
            </div>
          </CardContent>
        </Card>
      </div>

      <CostVsUtilChart
        data={costVsUtil?.data ?? null}
        loading={loading}
        error={error}
      />

      <UtilizationTable
        data={summary?.resources ?? null}
        loading={loading}
        error={error}
      />
    </div>
  );
}
