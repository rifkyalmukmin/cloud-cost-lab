"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ResourceDetail } from "@/lib/api";
import { getResource } from "@/lib/api";

interface ResourceDetailContentProps {
  resourceId: string;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function MetadataRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex justify-between py-2 border-b last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value || "—"}</span>
    </div>
  );
}

export function ResourceDetailContent({ resourceId }: ResourceDetailContentProps) {
  const [resource, setResource] = useState<ResourceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const data = await getResource(resourceId);
        setResource(data);
      } catch (e) {
        if (e instanceof Error && e.message.includes("404")) {
          setError("Resource not found");
        } else {
          setError("Failed to load resource");
        }
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [resourceId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link href="/resources" className="text-sm text-primary hover:underline">
          &larr; Back to Resources
        </Link>
        <Card className="border-destructive/50">
          <CardContent className="py-8 text-center">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!resource) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/resources" className="text-sm text-primary hover:underline">
          &larr; Resources
        </Link>
        <div>
          <h1 className="text-xl font-bold">{resource.name}</h1>
          <p className="text-sm text-muted-foreground">
            {resource.service} &middot; {resource.type} &middot; {resource.region}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="text-xs text-muted-foreground">Monthly Cost</div>
            <div className="text-xl font-bold">${resource.monthly_cost.toFixed(2)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-xs text-muted-foreground">Potential Saving</div>
            <div className="text-xl font-bold text-emerald-600">
              ${resource.potential_saving.toFixed(2)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-xs text-muted-foreground">CPU Avg</div>
            <div className="text-xl font-bold">
              {resource.utilization.cpu_avg !== null
                ? `${resource.utilization.cpu_avg.toFixed(0)}%`
                : "N/A"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-xs text-muted-foreground">Memory Avg</div>
            <div className="text-xl font-bold">
              {resource.utilization.memory_avg !== null
                ? `${resource.utilization.memory_avg.toFixed(0)}%`
                : "N/A"}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cost History</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={resource.cost_history}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDate}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tickFormatter={(v) => `$${v}`}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={45}
                />
                <Tooltip
                  formatter={(value) => [`$${Number(value).toFixed(4)}`, "Cost"]}
                  labelFormatter={(label) => formatDate(String(label))}
                />
                <Area
                  type="monotone"
                  dataKey="cost"
                  stroke="#2563eb"
                  strokeWidth={2}
                  fill="#2563eb"
                  fillOpacity={0.1}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {resource.utilization.cpu_avg !== null && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">CPU Utilization</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={resource.utilization_history}>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={formatDate}
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={40}
                  />
                  <Tooltip
                    formatter={(value) => [`${Number(value).toFixed(1)}%`, "CPU"]}
                    labelFormatter={(label) => formatDate(String(label))}
                  />
                  <Area
                    type="monotone"
                    dataKey="cpu_utilization"
                    stroke="#059669"
                    strokeWidth={2}
                    fill="#059669"
                    fillOpacity={0.1}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Metadata</CardTitle>
          </CardHeader>
          <CardContent>
            <MetadataRow label="Resource ID" value={resource.resource_id} />
            <MetadataRow label="Type" value={resource.type} />
            <MetadataRow label="Service" value={resource.service} />
            <MetadataRow label="Project" value={resource.project} />
            <MetadataRow label="Region" value={resource.region} />
            <MetadataRow label="Zone" value={resource.zone} />
            <MetadataRow label="Status" value={resource.status} />
            <MetadataRow label="Created" value={resource.created_at} />
            <MetadataRow label="Last Seen" value={resource.last_seen} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ownership</CardTitle>
          </CardHeader>
          <CardContent>
            <MetadataRow label="Environment" value={resource.environment} />
            <MetadataRow label="Owner" value={resource.owner} />
            <MetadataRow label="Team" value={resource.team} />
            <MetadataRow label="Application" value={resource.application} />
            <div className="mt-4">
              <span className="text-sm text-muted-foreground">Labels</span>
              {Object.keys(resource.labels).length > 0 ? (
                <div className="mt-1 flex flex-wrap gap-1">
                  {Object.entries(resource.labels).map(([key, val]) => (
                    <span
                      key={key}
                      className="inline-flex px-2 py-0.5 bg-muted rounded text-xs"
                    >
                      {key}: {val}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm mt-1 text-amber-600">No labels assigned</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
