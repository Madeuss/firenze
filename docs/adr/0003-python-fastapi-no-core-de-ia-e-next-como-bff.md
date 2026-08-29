# ADR-0003: Python/FastAPI no core de IA, Next.js como BFF

## Status

Aceita — 2026-08-29

## Contexto

O sistema tem duas naturezas bem diferentes:

- **Core de IA e domínio** — geração de caso, solver de dedutibilidade, montagem
  de dossiê, orquestração dos NPCs, classificadores, filtros de saída, máquina
  de postura, veredito. É aqui que estão todas as regras determinísticas
  (RN-002, RN-023, RN-032) e a fronteira de isolamento (RN-010/011).
- **Experiência do jogador** — chat com streaming, caderno de anotações, telas
  de acusação e replay. Precisa de UI reativa e primeiro token rápido.

O ecossistema que importa para a primeira metade — saída estruturada validada,
avaliação, tracing, orquestração de agentes, notebooks de análise — é
majoritariamente Python. O ecossistema da segunda é TypeScript.

Restrição adicional: a chave do provedor LLM não pode chegar ao navegador, e a
resposta precisa passar por filtro de canary e checagem de escopo **antes** de
sair para o cliente (RN-042) — inclusive no caminho de streaming.

## Decisão

Duas aplicações, com fronteira explícita:

- **`apps/api` — FastAPI (Python).** Dono de todo o domínio, de toda chamada a
  LLM e de todos os pontos de checagem. Nenhuma regra de negócio vive fora
  daqui. Expõe REST + SSE.
- **`apps/web` — Next.js (TypeScript).** UI e **BFF**: Route Handlers fazem
  proxy do SSE para o navegador, cuidam de sessão e cookies, e agregam chamadas
  para a tela. O front **nunca** fala com o provedor de LLM nem com o banco.

O contrato é o OpenAPI gerado pelo FastAPI, commitado como `openapi.json`, com
tipos TypeScript gerados por `openapi-typescript` em `packages/contracts`
(ADR-0001). Os eventos SSE ficam documentados em `docs/asyncapi.yaml`, porque
OpenAPI não descreve stream.

Escolha do framework de orquestração dentro do core (LangGraph ou orquestração
própria) é decisão separada — ADR-0004.

## Consequências

+ Todo caminho crítico com garantia determinística fica em um processo, numa
  linguagem, com uma suíte de testes.
+ Filtro de canary e checagem de escopo ficam do lado servidor da fronteira, sem
  chance de um atalho no front pular a validação.
+ Evals, tracing e análise usam as mesmas bibliotecas do core.
+ O front pode ir para a Vercel enquanto o core roda na Magalu, sem reescrita.
+ Tipagem atravessa a fronteira: quebrar o contrato quebra o build do front.
− Duas linguagens, duas toolchains, dois lints, dois typecheckers.
− Um salto de rede a mais no streaming (navegador → BFF → API). Custa poucos ms
  e precisa de cuidado para não bufferizar o SSE no meio do caminho.
− Modelo de domínio existe em dois lugares (Pydantic e tipos gerados). Mitigado
  por geração automática — tipo TS escrito à mão é bug esperando.
− Deploy em duas peças, com versionamento de contrato entre elas.

## Alternativas consideradas

- **Tudo em TypeScript (Next.js + Vercel AI SDK).** Uma linguagem, streaming
  trivial, deploy único. Rejeitado pelo ecossistema da metade difícil:
  avaliação, solver e análise de traces em Python são ordens de grandeza mais
  produtivos, e o projeto é sobre a metade difícil.
- **Tudo em Python (FastAPI + HTMX/Jinja).** Elimina a fronteira e o salto de
  rede. Rejeitado porque o caderno de anotações e o replay são interfaces com
  estado de verdade, e porque a experiência de front é parte do que o projeto
  demonstra.
- **Navegador falando direto com a FastAPI, sem BFF.** Um salto a menos, mas
  joga CORS, sessão e agregação de telas para dentro do core de domínio — e
  transforma cada endpoint em superfície pública.
