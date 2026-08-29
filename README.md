# Mansão

Jogo de mistério investigativo onde os suspeitos são NPCs com LLM. Você
interroga em texto livre, confronta com provas e acusa. A parte difícil não é o
chat — é gerar casos que sejam de fato dedutíveis e impedir que um NPC conte o
que ele não deveria saber.

**Estado:** fase 0 (fundação). Ainda não é jogável.

## Rodar local

Requisitos: Docker, [uv](https://docs.astral.sh/uv/) e `make`. O uv cuida do
Python — não precisa instalar a 3.13 na mão.

```bash
cp .env.example .env
make dev        # sobe Postgres 16 + pgvector, Redis e a API
curl localhost:8000/health
```

A API sobe em `localhost:8000` (docs em `/docs`), o Postgres em `localhost:5433`
— porta 5433 de propósito, para não conflitar com um Postgres instalado na
máquina.

Sem Docker, dá para rodar só a API contra serviços seus:

```bash
make install    # uv sync a partir do uv.lock
make api        # uvicorn com reload
```

## O que ler primeiro

| Documento | Para quê |
|---|---|
| [`docs/00-plano-de-projeto.md`](docs/00-plano-de-projeto.md) | escopo, roadmap, método |
| [`docs/01-dominio.md`](docs/01-dominio.md) | glossário e modelo de domínio |
| [`docs/02-regras-de-negocio.md`](docs/02-regras-de-negocio.md) | RN-001 a RN-042 |
| [`docs/adr/`](docs/adr/) | as decisões e o porquê delas |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | fluxo de branch, commit e PR |

## Licença

MIT — veja [`LICENSE`](LICENSE).
