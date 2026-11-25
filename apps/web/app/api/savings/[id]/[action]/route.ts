import { NextResponse } from "next/server";

const ACTIONS = new Set(["approve", "reject", "implement", "verify"]);

export async function POST(
  request: Request,
  context: { params: Promise<{ id: string; action: string }> },
) {
  const { id, action } = await context.params;
  if (!ACTIONS.has(action)) {
    return NextResponse.json({ detail: "Unknown action" }, { status: 404 });
  }

  const token = process.env.API_TOKEN?.trim();
  if (!token) {
    return NextResponse.json({ detail: "API principal is not configured" }, { status: 401 });
  }

  const payload = await request.json().catch(() => ({}));
  const apiBase = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const response = await fetch(`${apiBase}/api/savings/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const text = await response.text();
  return new NextResponse(text || "{}", {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
