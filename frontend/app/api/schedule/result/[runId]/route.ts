/**
 * Proxy for GET /api/schedule/result/[runId] — polls for scheduled run result.
 * Called by Logic Apps in an Until loop until status === "done".
 */

import { NextRequest, NextResponse } from "next/server";
import { BACKEND, validateRunId, safeFetch, safeJson } from "../../../lib/proxy-helpers";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const scheduleKey = req.headers.get("x-schedule-key") ?? "";

  const runIdError = validateRunId(runId);
  if (runIdError) return runIdError;

  const { response, error } = await safeFetch(
    `${BACKEND}/api/schedule/result/${encodeURIComponent(runId)}`,
    {
      headers: { "X-Schedule-Key": scheduleKey },
      cache: "no-store",
    },
  );

  if (error) return error;

  const upstream = response!;
  const { data, error: jsonErr } = await safeJson(upstream);
  if (jsonErr) return jsonErr;

  return NextResponse.json(data, { status: upstream.status });
}
