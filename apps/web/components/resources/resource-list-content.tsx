"use client";

import { useEffect, useState } from "react";
import { ResourceTable } from "./resource-table";
import type { ResourceListResponse } from "@/lib/api";
import { getResources } from "@/lib/api";

export function ResourceListContent() {
  const [resources, setResources] = useState<ResourceListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [page, setPage] = useState(1);
  const [envFilter, setEnvFilter] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(false);
        const params: { page: number; page_size: number; environment?: string } = {
          page,
          page_size: 20,
        };
        if (envFilter) params.environment = envFilter;
        const data = await getResources(params);
        setResources(data);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [page, envFilter]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <select
          value={envFilter}
          onChange={(e) => {
            setEnvFilter(e.target.value);
            setPage(1);
          }}
          className="text-sm border rounded px-3 py-1.5 bg-background"
        >
          <option value="">All Environments</option>
          <option value="production">Production</option>
          <option value="staging">Staging</option>
          <option value="development">Development</option>
        </select>
        {resources && (
          <span className="text-sm text-muted-foreground">
            {resources.total} resource{resources.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      <ResourceTable
        data={resources?.data ?? null}
        loading={loading}
        error={error}
      />

      {resources && resources.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="text-sm px-3 py-1.5 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
          >
            Previous
          </button>
          <span className="text-sm text-muted-foreground">
            Page {resources.page} of {resources.total_pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(resources.total_pages, p + 1))}
            disabled={page === resources.total_pages}
            className="text-sm px-3 py-1.5 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
