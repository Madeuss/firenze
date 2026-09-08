/**
 * Talking to the game, in types the API generated itself.
 *
 * Every shape here comes from `contracts.ts`, which is produced from
 * `apps/api/openapi.json` by `npm run contracts`. Nothing is hand-typed, so the
 * front cannot quietly disagree with the API about what a match looks like —
 * and CI fails if the checked-in contracts drift from the spec.
 *
 * These call the Next route handler at `/api`, never FastAPI. The browser has
 * no address for the API and no way to reach it (ADR-0003).
 */

import type { components } from "@/lib/contracts";

type Schemas = components["schemas"];

export type MatchState = Schemas["MatchState"];
export type CastMember = Schemas["CastMember"];
export type KnownFact = Schemas["KnownFact"];
export type Said = Schemas["Said"];
export type FloorPlan = Schemas["FloorPlan"];
export type Answer = Schemas["Answer"];
export type DraftAccusation = Schemas["DraftAccusation"];
export type Outcome = Schemas["Outcome"];
export type Review = Schemas["Review"];
export type Stance = Schemas["Stance"];

/** The API answered, and said no. Carries the status so a caller can tell
 * "you have no turns left" (409) from "that is not a suspect" (422). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    ...init,
    // O estado da partida muda a cada turno; resposta guardada e resposta
    // errada. O `no-store` tambem esta no route handler, porque nenhum dos
    // dois lados deveria depender do outro lembrar disso.
    cache: "no-store",
    headers: { "content-type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, detailOf(body) ?? response.statusText);
  }
  return (await response.json()) as T;
}

function detailOf(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const { detail } = body as { detail: unknown };
    if (typeof detail === "string") return detail;
  }
  return null;
}

export function startMatch(seed: number, locale = "pt-BR"): Promise<MatchState> {
  return call<MatchState>("matches", {
    method: "POST",
    body: JSON.stringify({ seed, locale }),
  });
}

export function readMatch(id: string): Promise<MatchState> {
  return call<MatchState>(`matches/${id}`);
}

export function ask(id: string, suspect: string, question: string): Promise<Answer> {
  return call<Answer>(`matches/${id}/turns`, {
    method: "POST",
    body: JSON.stringify({ suspect, question }),
  });
}

export function confront(id: string, suspect: string, evidence: string): Promise<Answer> {
  return call<Answer>(`matches/${id}/confrontations`, {
    method: "POST",
    body: JSON.stringify({ suspect, evidence }),
  });
}

export function draftAccusation(id: string, text: string): Promise<DraftAccusation> {
  return call<DraftAccusation>(`matches/${id}/accusation/draft`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export function accuse(
  id: string,
  accusation: { culprit: string; motive_key?: string | null; evidence?: string[] },
): Promise<Outcome> {
  return call<Outcome>(`matches/${id}/accusation`, {
    method: "POST",
    body: JSON.stringify(accusation),
  });
}

export function readReview(id: string): Promise<Review> {
  return call<Review>(`matches/${id}/review`);
}
