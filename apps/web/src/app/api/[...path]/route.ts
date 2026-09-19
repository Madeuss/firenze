/**
 * The only door between the browser and the API. (ADR-0003)
 *
 * One handler rather than a file per endpoint, because this is a proxy and
 * pretending otherwise would mean writing the same six lines six times. What
 * makes it a boundary instead of a hole is the allowlist: it forwards to
 * `/matches`, and nothing else. A path this file does not recognise is a 404
 * here, not a request to the API.
 *
 * The API's address lives on the server, and so does the access key. The
 * browser never learns either: the key is this deployment's invitation to
 * start matches at all (T-11), and shipping it to the browser would be the
 * same as not having one.
 *
 * The owner token is the opposite — it belongs to the player, proves the match
 * is theirs, and would be useless kept here. It travels through, untouched.
 */

import { NextRequest, NextResponse } from "next/server";

const API = process.env.FIRENZE_API_URL ?? "http://localhost:8000";
const KEY = process.env.FIRENZE_ACCESS_KEY ?? "";
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
      headers: {
        "content-type": "application/json",
        // Do jogador, sobre a partida dele. Chega vazio quando não há.
        ...forwardToken(request),
        // Desta instalação, sobre o direito de começar. Nunca do navegador.
        ...(KEY ? { "x-firenze-key": KEY } : {}),
      },
      body,
      cache: "no-store",
    });
  } catch {
    // The API being down is not the player's fault and not a game event.
    return NextResponse.json({ detail: "o jogo está fora do ar" }, { status: 502 });
  }

  return NextResponse.json(await response.json().catch(() => null), {
    status: response.status,
    // Sem isto o navegador guarda o GET da partida por heuristica propria — e
    // servia o caderno de antes do turno que o jogador acabou de gastar. O
    // sintoma era intermitente porque a heuristica e do navegador, nao nossa.
    headers: { "cache-control": "no-store" },
  });
}

function forwardToken(request: NextRequest): Record<string, string> {
  const token = request.headers.get("x-firenze-token");
  return token ? { "x-firenze-token": token } : {};
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: Context): Promise<NextResponse> {
  return forward(request, (await context.params).path);
}

export async function POST(request: NextRequest, context: Context): Promise<NextResponse> {
  return forward(request, (await context.params).path);
}
