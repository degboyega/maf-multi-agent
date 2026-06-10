/**
 * Proxy for POST /api/mail/cancel/[token] — discards a staged email without sending.
 */

import { NextRequest, NextResponse } from "next/server";
import { BACKEND, safeFetch, safeJson } from "../../../lib/proxy-helpers";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ token: string }> },
) {
  const { token } = await params;

  if (!TOKEN_PATTERN.test(token)) {
    return NextResponse.json({ detail: "Invalid token format" }, { status: 400 });
  }

  const { response, error } = await safeFetch(
    `${BACKEND}/api/mail/cancel/${encodeURIComponent(token)}`,
    { method: "POST", cache: "no-store" },
  );

  if (error) return error;

  const upstream = response!;
  const { data, error: jsonErr } = await safeJson(upstream);
  if (jsonErr) return jsonErr;

  return NextResponse.json(data, { status: upstream.status });
}
