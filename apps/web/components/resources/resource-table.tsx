"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ResourceListItem } from "@/lib/api";

interface ResourceTableProps {
  data: ResourceListItem[] | null;
  loading?: boolean;
  error?: boolean;
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "active"
      ? "bg-emerald-100 text-emerald-800"
      : "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {status}
    </span>
  );
}

function UtilBar({ value }: { value: number | null }) {
  if (value === null) return <span className="text-xs text-muted-foreground">—</span>;
  const color =
    value > 80 ? "bg-destructive" : value > 50 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs text-muted-foreground">{value.toFixed(0)}%</span>
    </div>
  );
}

export function ResourceTable({ data, loading, error }: ResourceTableProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-base">Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">Failed to load resources</p>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No resources found</p>
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
                <th className="text-left p-3 font-medium">Type</th>
                <th className="text-left p-3 font-medium">Project</th>
                <th className="text-left p-3 font-medium">Region</th>
                <th className="text-left p-3 font-medium">Env</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-right p-3 font-medium">Monthly Cost</th>
                <th className="text-left p-3 font-medium">CPU</th>
                <th className="text-left p-3 font-medium">Memory</th>
                <th className="text-right p-3 font-medium">Potential Saving</th>
              </tr>
            </thead>
            <tbody>
              {data.map((resource) => (
                <tr key={resource.resource_id} className="border-b hover:bg-muted/30">
                  <td className="p-3">
                    <Link
                      href={`/resources/${resource.resource_id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {resource.name}
                    </Link>
                    <div className="text-xs text-muted-foreground">
                      {resource.service}
                    </div>
                  </td>
                  <td className="p-3 font-mono text-xs">{resource.type}</td>
                  <td className="p-3 text-xs">{resource.project}</td>
                  <td className="p-3 text-xs">{resource.region}</td>
                  <td className="p-3 text-xs">{resource.environment}</td>
                  <td className="p-3">
                    <StatusBadge status={resource.status} />
                  </td>
                  <td className="p-3 text-right font-medium">
                    ${resource.monthly_cost.toFixed(2)}
                  </td>
                  <td className="p-3">
                    <UtilBar value={resource.cpu_utilization} />
                  </td>
                  <td className="p-3">
                    <UtilBar value={resource.memory_utilization} />
                  </td>
                  <td className="p-3 text-right">
                    {resource.potential_saving > 0 ? (
                      <span className="text-emerald-600 font-medium">
                        ${resource.potential_saving.toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
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
