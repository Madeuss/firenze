# Firenze

Jogo de mistério investigativo com NPCs agênticos.
Next.js (front) + FastAPI/LangGraph (core de IA) + Postgres com pgvector.

## Invariantes — nunca viole sem ADR novo

- O LLM NUNCA decide veredito, pontuação ou detecção de contradição.
  Ele narra desfecho já calculado por código determinístico. (RN-032)
- A entidade Solucao NUNCA entra no contexto de um NPC suspeito.
  Isolamento é fronteira arquitetural, não prompt hardening. (RN-011)
- Todo fato secreto carrega canary token. Canary na saída = falha
  crítica, resposta descartada. (RN-012)
- Memória de NPC só aceita fatos do dossiê, nunca texto do jogador. (RN-006)

## Convenções

- Regras de negócio se referenciam por número, nunca se transcrevem.
  No código: `# RN-012`. Docs em `docs/02-regras-de-negocio.md`.
- Toda saída de LLM é validada por schema Pydantic versionado.
  Mudou o schema, roda os evals antes de commitar.
- Prompts vivem em `prompts/`, versionados, nunca em string literal.
- Modelo só se chama pela porta em `firenze.model`. Nenhum outro módulo
  importa SDK de fornecedor. (ADR-0007)
- Código em inglês, docs em português, conteúdo do jogo em português.
  Domínio guarda estrutura; frase pronta só no catálogo. (ADR-0005/0006)
- Conventional Commits. Nada direto na main.

## Comandos

- `make install` cria `.venv` e instala `apps/api` em modo editável
- `make dev` sobe o compose local (API, Postgres+pgvector, Redis)
- `make api` roda só a API com reload, sem container
- `make case SEED=42 [LOCALE=en] [REVEAL=1]` gera e imprime um caso
- `make check` roda o que o CI cobra (lint, typecheck, test)
- `make openapi` regenera `apps/api/openapi.json` — commitar junto
- `make evals` roda a suíte de avaliação
- `make migrate` aplica alembic

## Armadilhas

- O DBaaS da Magalu só aceita conexão de dentro da rede deles.
  Migration local exige túnel SSH pela VM. Ver `docs/07-runbook.md`.
- Temperatura > 0: eval rodado uma vez não prova nada. Sempre 5 runs.

## Onde procurar

Domínio e glossário: `docs/01-dominio.md`
Regras de negócio: `docs/02-regras-de-negocio.md`
Decisões arquiteturais e o porquê delas: `docs/adr/`
