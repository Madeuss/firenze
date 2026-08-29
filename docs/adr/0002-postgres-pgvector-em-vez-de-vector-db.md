# ADR-0002: Postgres + pgvector em vez de banco vetorial dedicado

## Status

Aceita — 2026-08-29

## Contexto

Os NPCs precisam de memória com busca semântica: recuperar declarações passadas
e itens de dossiê relevantes para a pergunta do turno.

Volume estimado: ~500 vetores por partida, ~50k no total do MVP. Duas ordens de
grandeza abaixo do ponto em que um índice vetorial dedicado começa a pagar sua
operação.

Duas restrições do domínio pesam mais que o desempenho:

- **Isolamento é fronteira arquitetural** (RN-010, RN-011, RN-013). A busca de
  memória é sempre filtrada por `(partida, personagem)` e por escopo do fato.
  Isso é filtro relacional com alta seletividade acoplado à busca por
  similaridade — território onde bancos vetoriais só recentemente ficaram
  competentes e onde um `WHERE` do Postgres é trivial.
- **Estado do jogo e memória mudam no mesmo turno.** Persistir a declaração,
  indexar o vetor e debitar o orçamento devem ser atômicos (RN-030). Em dois
  armazenamentos, isso vira escrita dupla e reconciliação.

O DBaaS PostgreSQL 16 da Magalu Cloud oferece a extensão `vector` 0.8.2, com
HNSW nativo.

## Decisão

Postgres gerenciado (DBaaS Magalu) com pgvector, índice HNSW, como armazenamento
único de estado de jogo e memória de NPC.

Extensões habilitadas na criação do banco:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- busca híbrida
CREATE EXTENSION IF NOT EXISTS unaccent;   -- português
CREATE EXTENSION IF NOT EXISTS pgaudit;    -- trilha de auditoria
```

Busca híbrida (`pg_trgm` + vetor) em vez de puramente semântica: nomes próprios
e horários — o que mais aparece nas perguntas — recuperam mal por embedding.

## Consequências

+ Uma dependência a menos para operar, provisionar e monitorar.
+ Transação única entre estado do jogo e memória; sem escrita dupla.
+ O filtro de isolamento é um `WHERE` no mesmo `SELECT` da busca vetorial — o
  isolamento fica verificável por query, e auditável via `pgaudit`.
+ Backup, snapshot e restore cobertos pelo DBaaS.
+ `pg_cron` disponível: expirar partidas abandonadas e consolidar métricas sem
  worker externo.
− Escala pior que Qdrant/Milvus acima de ~1M vetores. Fora do horizonte do MVP;
  se chegar lá, é ADR nova.
− Tuning de HNSW é manual (`m`, `ef_construction`, `ef_search`) e o custo de
  construção do índice aparece na migration.
− O DBaaS só aceita conexão de dentro da rede Magalu: migration e `psql` locais
  exigem túnel SSH pela VM da aplicação. Registrar em `docs/07-runbook.md`.
− Trocar de modelo de embedding exige reindexar tudo — a dimensão do vetor está
  na coluna.

## Alternativas consideradas

- **Qdrant self-hosted em VM.** Filtro com payload e desempenho melhores em
  escala, ao custo de mais um serviço para operar, backups próprios e
  consistência eventual com o Postgres. Sem ganho no volume atual.
- **Chroma em memória.** Perde estado entre deploys; inviável para partida com
  duração de dias.
- **Sem busca semântica (só `pg_trgm` e recência).** Tentador, e provavelmente
  suficiente para 6 NPCs. Rejeitado porque a fofoca entre NPCs (fase 3) e o
  detector de contradição se beneficiam de similaridade — mas é o plano B se o
  tuning do HNSW virar sumidouro de tempo.
