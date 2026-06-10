/**
 * Proxy for POST /api/mail/confirm/[token] — confirms and sends a staged email.
 */

import { NextRequest, NextResponse } from "next/server";
import { BACKEND, safeFetch, safeJson } from "../../../lib/proxy-helpers";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

export async function POST(
  _req: NextRequest,
  { params }: { params: { token: string } },
) {
  const { token } = params;

  if (!TOKEN_PATTERN.test(token)) {
    return NextResponse.json({ detail: "Invalid token format" }, { status: 400 });
  }

  const { response, error } = await safeFetch(
    `${BACKEND}/api/mail/confirm/${encodeURIComponent(token)}`,
    { method: "POST", cache: "no-store" },
  );

  if (error) return error;

  const upstream = response!;
  const { data, error: jsonErr } = await safeJson(upstream);
  if (jsonErr) return jsonErr;

  return NextResponse.json(data, { status: upstream.status });
}
