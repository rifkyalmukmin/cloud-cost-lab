"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface CostSummaryCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: {
    value: number;
    label: string;
  };
  loading?: boolean;
  error?: boolean;
}

export function CostSummaryCard({
  title,
  value,
  subtitle,
  trend,
  loading,
  error,
}: CostSummaryCardProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-32 mb-1" />
          <Skeleton className="h-3 w-20" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">Failed to load</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend && (
          <p
            className={`text-xs mt-1 ${
              trend.value > 0
                ? "text-destructive"
                : trend.value < 0
                  ? "text-emerald-600"
                  : "text-muted-foreground"
            }`}
          >
            {trend.value > 0 ? "+" : ""}
            {trend.value.toFixed(1)}% {trend.label}
          </p>
        )}
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}
