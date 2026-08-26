"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ResourceUtilization } from "@/lib/api";

interface UtilizationTableProps {
  data: ResourceUtilization[] | null;
  loading?: boolean;
  error?: boolean;
}

function PatternBadge({ pattern }: { pattern: { status: string; evidence: string } }) {
  const colorMap: Record<string, string> = {
    low: "bg-amber-100 text-amber-800",
    high: "bg-red-100 text-red-800",
    unstable: "bg-orange-100 text-orange-800",
    normal: "bg-emerald-100 text-emerald-800",
    missing: "bg-gray-100 text-gray-600",
  };
  const color = colorMap[pattern.status] || "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {pattern.status}
    </span>
  );
}

function StatCell({ stats }: { stats: { avg: number | null; min: number | null; max: number | null; p95: number | null } }) {
  if (stats.avg === null) {
    return <span className="text-xs text-muted-foreground">N/A</span>;
  }
  return (
    <div className="text-xs">
      <div className="font-medium">{stats.avg.toFixed(1)}%</div>
      <div className="text-muted-foreground">
        min {stats.min?.toFixed(0)} / max {stats.max?.toFixed(0)} / p95 {stats.p95?.toFixed(0)}
      </div>
    </div>
  );
}

export function UtilizationTable({ data, loading, error }: UtilizationTableProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="p-4">
          <p className="text-sm text-destructive">Failed to load utilization data</p>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">No utilization data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 font-medium">Resource</th>
                <th className="text-left p-3 font-medium">Environment</th>
                <th className="text-right p-3 font-medium">Cost</th>
                <th className="text-left p-3 font-medium">CPU</th>
                <th className="text-left p-3 font-medium">CPU Pattern</th>
                <th className="text-left p-3 font-medium">Memory</th>
                <th className="text-left p-3 font-medium">Memory Pattern</th>
              </tr>
            </thead>
            <tbody>
              {data.map((resource) => (
                <tr key={resource.resource_id} className="border-b hover:bg-muted/30">
                  <td className="p-3">
                    <div className="font-medium">{resource.name}</div>
                    <div className="text-xs text-muted-foreground">{resource.service}</div>
                  </td>
                  <td className="p-3 text-xs">{resource.environment}</td>
                  <td className="p-3 text-right font-medium">
                    ${resource.monthly_cost.toFixed(2)}
                  </td>
                  <td className="p-3">
                    <StatCell stats={resource.cpu} />
                  </td>
                  <td className="p-3">
                    <PatternBadge pattern={resource.cpu_pattern} />
                    <div className="text-xs text-muted-foreground mt-1 max-w-xs">
                      {resource.cpu_pattern.evidence}
                    </div>
                  </td>
                  <td className="p-3">
                    <StatCell stats={resource.memory} />
                  </td>
                  <td className="p-3">
                    <PatternBadge pattern={resource.memory_pattern} />
                    <div className="text-xs text-muted-foreground mt-1 max-w-xs">
                      {resource.memory_pattern.evidence}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
