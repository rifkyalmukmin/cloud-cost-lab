"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Recommendation } from "@/lib/api";
import { getRecommendations } from "@/lib/api";

async function postAction(id: string, action: string, body?: Record<string, unknown>) {
  const response = await fetch(`/api/savings/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return payload;
}

export function ApprovalsContent() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [costsAfter, setCostsAfter] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await getRecommendations();
      setRecommendations(data.recommendations);
    } catch {
      setError("Failed to load recommendations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    getRecommendations()
      .then((data) => {
        if (!cancelled) {
          setRecommendations(data.recommendations);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load recommendations");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function run(id: string, action: string, body?: Record<string, unknown>) {
    try {
      setPendingId(id);
      setError(null);
      await postAction(id, action, body);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setPendingId(null);
    }
  }

  if (loading && recommendations.length === 0) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    );
  }

  if (error && recommendations.length === 0) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="py-8 text-center space-y-3">
          <p className="text-destructive">{error}</p>
          <button type="button" onClick={() => void load()} className="text-sm px-3 py-1.5 border rounded">
            Retry
          </button>
        </CardContent>
      </Card>
    );
  }

  if (recommendations.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          No recommendations to review
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {recommendations.map((rec) => {
        const busy = pendingId === rec.id;
        return (
          <Card key={rec.id}>
            <CardContent className="pt-4 space-y-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-semibold">{rec.title}</h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    <Link href={`/resources/${encodeURIComponent(rec.resource_id)}`} className="hover:underline">
                      {rec.resource_name}
                    </Link>
                    {" · "}
                    {rec.environment} · {rec.status}
                  </p>
                </div>
                <div className="text-right">
                  <div className="font-semibold">${rec.potential_savings.toFixed(2)}/mo</div>
                  <div className="text-xs text-muted-foreground">estimated</div>
                </div>
              </div>
              <p className="text-sm">{rec.evidence}</p>
              {rec.status === "OPEN" ? (
                <div className="flex flex-wrap items-end gap-3">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void run(rec.id, "approve")}
                    className="text-sm px-3 py-1.5 border rounded bg-foreground text-background disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <label className="text-xs text-muted-foreground flex flex-col gap-1">
                    Rejection reason
                    <input
                      value={reasons[rec.id] ?? ""}
                      maxLength={500}
                      onChange={(event) =>
                        setReasons((current) => ({ ...current, [rec.id]: event.target.value }))
                      }
                      className="text-sm border rounded px-2 py-1 bg-background text-foreground"
                    />
                  </label>
                  <button
                    type="button"
                    disabled={busy || !(reasons[rec.id] ?? "").trim()}
                    onClick={() => void run(rec.id, "reject", { reason: (reasons[rec.id] ?? "").trim() })}
                    className="text-sm px-3 py-1.5 border rounded disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              ) : null}
              {rec.status === "APPROVED" ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void run(rec.id, "implement")}
                  className="text-sm px-3 py-1.5 border rounded disabled:opacity-50"
                >
                  Mark implemented
                </button>
              ) : null}
              {rec.status === "IMPLEMENTED" ? (
                <div className="flex flex-wrap items-end gap-3">
                  <label className="text-xs text-muted-foreground flex flex-col gap-1">
                    Cost after change (USD)
                    <input
                      type="number"
                      min={0}
                      step="0.01"
                      value={costsAfter[rec.id] ?? ""}
                      onChange={(event) =>
                        setCostsAfter((current) => ({ ...current, [rec.id]: event.target.value }))
                      }
                      className="text-sm border rounded px-2 py-1 bg-background text-foreground"
                    />
                  </label>
                  <button
                    type="button"
                    disabled={busy || costsAfter[rec.id] === undefined || costsAfter[rec.id] === ""}
                    onClick={() =>
                      void run(rec.id, "verify", { cost_after: Number(costsAfter[rec.id]) })
                    }
                    className="text-sm px-3 py-1.5 border rounded disabled:opacity-50"
                  >
                    Verify savings
                  </button>
                </div>
              ) : null}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
