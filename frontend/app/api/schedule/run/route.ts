/**
 * Proxy for POST /api/schedule/run — starts a scheduled workflow run.
 * Called by Logic Apps (or any external scheduler) with X-Schedule-Key header.
 */

import { NextRequest, NextResponse } from "next/server";
import { BACKEND, safeFetch, safeJson } from "../../lib/proxy-helpers";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const scheduleKey = req.headers.get("x-schedule-key") ?? "";

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  const { response, error } = await safeFetch(
    `${BACKEND}/api/schedule/run`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Schedule-Key": scheduleKey,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    },
    60_000,
  );

  if (error) return error;

  const upstream = response!;
  const { data, error: jsonErr } = await safeJson(upstream);
  if (jsonErr) return jsonErr;

  return NextResponse.json(data, { status: upstream.status });
}
