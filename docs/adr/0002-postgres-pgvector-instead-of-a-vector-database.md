# ADR-0002: Postgres with pgvector instead of a dedicated vector database

## Status

Accepted — 2026-08-29

## Context

The NPCs need memory with semantic search: retrieving past statements and
dossier items relevant to the question asked this turn.

Estimated volume: ~500 vectors per match, ~50k across the MVP. Two orders of
magnitude below the point where a dedicated vector index starts paying for its
own operation.

Two domain constraints weigh more than performance:

- **Isolation is an architectural boundary** (RN-010, RN-011, RN-013). Memory
  search is always filtered by `(match, character)` and by fact scope. That is a
  highly selective relational filter coupled to a similarity search — territory
  where vector databases have only recently become competent, and where a
  Postgres `WHERE` is trivial.
- **Game state and memory change in the same turn.** Persisting the statement,
  indexing the vector and debiting the budget must be atomic (RN-030). Across
  two stores, that becomes a dual write and a reconciliation problem.

Magalu Cloud's managed PostgreSQL 16 offers the `vector` extension 0.8.2, with
native HNSW.

## Decision

Managed Postgres (Magalu DBaaS) with pgvector and an HNSW index, as the single
store for both game state and NPC memory.

Extensions enabled at database creation:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- hybrid search
CREATE EXTENSION IF NOT EXISTS unaccent;   -- portuguese
CREATE EXTENSION IF NOT EXISTS pgaudit;    -- audit trail
```

Hybrid search (`pg_trgm` plus vector) rather than purely semantic: proper names
and times — the things players actually ask about — retrieve poorly by
embedding.

## Consequences

+ One fewer dependency to operate, provision and monitor.
+ A single transaction across game state and memory; no dual write.
+ The isolation filter is a `WHERE` in the same `SELECT` as the vector search,
  so isolation is verifiable by query and auditable through `pgaudit`.
+ Backup, snapshot and restore come with the managed service.
+ `pg_cron` is available: expiring abandoned matches and consolidating metrics
  without an external worker.
− Scales worse than Qdrant or Milvus above ~1M vectors. Outside the MVP horizon;
  reaching it would justify a new ADR.
− HNSW tuning is manual (`m`, `ef_construction`, `ef_search`) and index build
  cost shows up in the migration.
− The managed instance only accepts connections from inside the Magalu network:
  local migrations and `psql` need an SSH tunnel through the application VM.
  Recorded in `docs/07-runbook.md`.
− Changing the embedding model means reindexing everything — the vector
  dimension is part of the column.
− Local and managed versions drift: the container image ships pgvector 0.8.6
  while the managed instance is on 0.8.2. A new index feature has to be checked
  against production before it is used.

## Alternatives considered

- **Self-hosted Qdrant on a VM.** Better payload filtering and better
  performance at scale, at the cost of another service to operate, its own
  backups, and eventual consistency with Postgres. No gain at the current
  volume.
- **In-memory Chroma.** Loses state between deployments; unusable for a match
  that spans days.
- **No semantic search at all (`pg_trgm` and recency only).** Tempting, and
  probably sufficient for six NPCs. Rejected because NPC gossip (phase 3) and
  the contradiction detector benefit from similarity — but it stays the fallback
  if HNSW tuning turns into a time sink.
