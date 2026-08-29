# Contribuindo

Projeto de uma pessoa só. As convenções abaixo existem porque disciplina sozinho
é mais frágil que disciplina em time, não porque há um time.

## Fluxo

Nada vai direto para a `main` — a branch é protegida por ruleset (PR
obrigatório, histórico linear, sem force push, sem deleção).

```bash
git switch -c feat/case-generator
# trabalha
gh pr create --fill
# CI verde
gh pr merge --squash --delete-branch
```

Branch curta: 1–2 dias, com nome **em inglês** — como o commit e o PR. Se uma
fase do roadmap virou uma branch de duas semanas, ela era três PRs.

**Prefixos de branch:** `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`,
`test/`, `ci/`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), **em inglês** — a
documentação é em português, o histórico do git não. O merge é **squash**, então
o **título do PR** vira a mensagem na `main` — é ele que o `release-please` vai
ler para gerar o CHANGELOG. Título fora do padrão reprova no check `pr-title`.

```
feat(api): build dossier from fact scope
fix(npc): posture no longer leaves the broken state
docs: add ADR-0004 on orchestration
```

Corpo do commit cita regra por número (`RN-012`), nunca transcreve o texto dela.
Sem trailers de coautoria.

Nunca `--no-verify`. Se o hook atrapalha, conserte o hook.

## O que o CI cobra

| Check | O que roda |
|---|---|
| `lint` | `ruff check` + `ruff format --check` |
| `typecheck` | `mypy` |
| `test` | `pytest` e verificação de que o `openapi.json` commitado está atualizado |
| `pr-title` | título do PR no formato conventional |

Rodar tudo localmente antes de abrir o PR: `make check`.

Os gates de eval entram na fase 3, com uma regra que vale registrar desde já:
**vazamento de canary é gate bloqueante e binário** (um único vazamento reprova);
métricas estatísticas — persona, consistência — são comentário no PR com delta
contra a baseline, e só bloqueiam num limite de pânico. Gate que reprova por
ruído é gate que se aprende a ignorar.

Nenhum job de CI usa filtro `paths:` enquanto for check obrigatório: check que
não roda fica *pending* para sempre e trava o merge.

## Docs

Documentação vive no repositório, versionada com o código que descreve.
Decisão arquitetural vira ADR em `docs/adr/` (template MADR) — com a seção de
consequências negativas preenchida. Regra de negócio nova entra em
`docs/02-regras-de-negocio.md` e é citada por número no código.
