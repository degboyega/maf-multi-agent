import { NextRequest, NextResponse } from "next/server";
import { BACKEND, safeFetch, safeJson } from "../../lib/proxy-helpers";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const apiKey = req.headers.get("X-Schedule-Api-Key") ?? "";
  const { response, error } = await safeFetch(
    `${BACKEND}/api/schedule/trigger`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Schedule-Api-Key": apiKey,
      },
      cache: "no-store",
    },
  );

  if (error) return error;

  const upstream = response!;
  const { data, error: jsonErr } = await safeJson(upstream);
  if (jsonErr) return jsonErr;

  return NextResponse.json(data, { status: upstream.status });
}
