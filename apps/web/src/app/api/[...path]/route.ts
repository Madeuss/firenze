/**
 * The only door between the browser and the API. (ADR-0003)
 *
 * One handler rather than a file per endpoint, because this is a proxy and
 * pretending otherwise would mean writing the same six lines six times. What
 * makes it a boundary instead of a hole is the allowlist: it forwards to
 * `/matches`, and nothing else. A path this file does not recognise is a 404
 * here, not a request to the API.
 *
 * The API's address lives on the server. The browser never learns it, which
 * matters more than usual while T-11 is open — nothing authenticates a match,
 * so the API must not be reachable from outside this process.
 */

import { NextRequest, NextResponse } from "next/server";

const API = process.env.FIRENZE_API_URL ?? "http://localhost:8000";
const ALLOWED = /^matches(\/|$)/;

async function forward(request: NextRequest, path: string[]): Promise<NextResponse> {
  const route = path.join("/");
  if (!ALLOWED.test(route)) {
    return NextResponse.json({ detail: `no route for ${route}` }, { status: 404 });
  }

  const body = request.method === "GET" ? undefined : await request.text();

  let response: Response;
  try {
    response = await fetch(`${API}/${route}`, {
      method: request.method,
      headers: { "content-type": "application/json" },
      body,
      cache: "no-store",
    });
  } catch {
    // The API being down is not the player's fault and not a game event.
    return NextResponse.json({ detail: "o jogo está fora do ar" }, { status: 502 });
  }

  return NextResponse.json(await response.json().catch(() => null), {
    status: response.status,
  });
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: Context): Promise<NextResponse> {
  return forward(request, (await context.params).path);
}

export async function POST(request: NextRequest, context: Context): Promise<NextResponse> {
  return forward(request, (await context.params).path);
}
