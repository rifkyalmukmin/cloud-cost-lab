"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Recommendation } from "@/lib/api";
import { getRecommendations } from "@/lib/api";

function RiskBadge({ risk }: { risk: string }) {
  const colors = {
    LOW: "bg-emerald-100 text-emerald-800",
    MEDIUM: "bg-amber-100 text-amber-800",
    HIGH: "bg-red-100 text-red-800",
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${colors[risk as keyof typeof colors] || colors.LOW}`}>
      {risk}
    </span>
  );
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const colors = {
    HIGH: "bg-blue-100 text-blue-800",
    MEDIUM: "bg-gray-100 text-gray-700",
    LOW: "bg-gray-50 text-gray-600",
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${colors[confidence as keyof typeof colors] || colors.MEDIUM}`}>
      {confidence}
    </span>
  );
}

export function RecommendationsContent() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [sortBy, setSortBy] = useState<"priority" | "savings">("priority");

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(false);
        const data = await getRecommendations();
        setRecommendations(data.recommendations);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const sortedRecs = [...recommendations].sort((a, b) => {
    if (sortBy === "priority") return b.priority - a.priority;
    return b.potential_savings - a.potential_savings;
  });

  const totalSavings = recommendations.reduce((sum, r) => sum + r.potential_savings, 0);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="py-8 text-center">
          <p className="text-destructive">Failed to load recommendations</p>
        </CardContent>
      </Card>
    );
  }

  if (recommendations.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">No recommendations at this time</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground">Total Potential Savings</div>
              <div className="text-2xl font-bold text-emerald-600">
                ${totalSavings.toFixed(2)}/mo
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Active Recommendations</div>
              <div className="text-2xl font-bold">{recommendations.length}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">Sort by:</span>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as "priority" | "savings")}
          className="text-sm border rounded px-3 py-1.5 bg-background"
        >
          <option value="priority">Priority</option>
          <option value="savings">Potential Savings</option>
        </select>
      </div>

      <div className="space-y-4">
        {sortedRecs.map((rec) => (
          <Card key={rec.id}>
            <CardContent className="pt-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-base">{rec.title}</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {rec.resource_name} &middot; {rec.service} &middot; {rec.environment}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-emerald-600">
                    ${rec.potential_savings.toFixed(2)}/mo
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {rec.savings_percentage.toFixed(0)}% savings
                  </div>
                </div>
              </div>

              <div className="space-y-2 text-sm mb-3">
                <div>
                  <span className="font-medium">Problem:</span> {rec.problem}
                </div>
                <div>
                  <span className="font-medium">Evidence:</span> {rec.evidence}
                </div>
                <div>
                  <span className="font-medium">Recommendation:</span> {rec.recommendation}
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t">
                <div className="flex items-center gap-3 text-xs">
                  <div className="flex items-center gap-1">
                    <span className="text-muted-foreground">Risk:</span>
                    <RiskBadge risk={rec.risk} />
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-muted-foreground">Confidence:</span>
                    <ConfidenceBadge confidence={rec.confidence} />
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-muted-foreground">Effort:</span>
                    <span>{rec.effort}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-muted-foreground">Priority:</span>
                    <span className="font-medium">{rec.priority}</span>
                  </div>
                </div>
                <div className="text-xs font-medium text-right">
                  <div>{rec.status}</div>
                  {rec.status === "OPEN" ? (
                    <Link href="/approvals" className="text-amber-700 hover:underline">
                      Approval required
                    </Link>
                  ) : null}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
