# ADR-0001: Monorepo único para app, infra, evals e docs

## Status

Aceita — 2026-08-29

## Contexto

O projeto tem cinco artefatos que mudam juntos com frequência: o core de IA
(Python), o front (TypeScript), a infraestrutura (Terraform), as suítes de eval
(dados + configuração) e a documentação (Markdown, ADRs, agent cards).

Três acoplamentos definem o problema:

- **Contrato HTTP.** O front consome tipos gerados do OpenAPI do backend. Em
  repositórios separados, quebrar o contrato só aparece depois — em runtime, ou
  na próxima release do pacote de tipos.
- **Prompt ↔ eval.** Mudar um prompt exige rodar os evals correspondentes no
  mesmo PR; é gate de CI, não boa intenção. Se prompt e eval vivem em repos
  diferentes, o gate é contornável por construção.
- **Doc ↔ código.** O princípio do projeto é docs-as-code: regra de negócio
  citada por número no código (`# RN-012`) e definida em `docs/`. Separar joga
  fora a possibilidade de revisar os dois no mesmo diff.

Contexto de operação: desenvolvedor solo, um ambiente de CI, sem necessidade de
permissões distintas por artefato e sem consumidores externos do código.

## Decisão

Um repositório único, com workspaces por linguagem e sem orquestrador de
monorepo:

```
apps/api          FastAPI — core de IA e domínio
apps/web          Next.js — BFF e UI
packages/contracts  tipos TS gerados do openapi.json commitado
infra/            terraform, compose, k8s
evals/            datasets e suítes
docs/             plano, domínio, regras, ADRs, agent cards
prompts/          prompts versionados
```

Cada app mantém a própria toolchain nativa (`uv`/`ruff`/`pytest` no Python,
`pnpm`/`eslint`/`tsc` no TS). A raiz expõe um `Makefile` como fachada — `make
dev`, `make evals`, `make migrate` — e o CI dispara jobs por caminho alterado
(`paths:` no workflow), não um grafo de tarefas.

**Sem Nx, Turborepo ou Bazel.** Eles resolvem tempo de build em repositório
grande com muitos times; aqui só somariam configuração.

## Consequências

+ Contrato quebrado vira erro de build no mesmo PR que o quebrou.
+ Um PR carrega mudança de prompt, eval e doc — revisável como uma unidade.
+ Uma versão, um CHANGELOG, um histórico. `git bisect` atravessa a stack inteira.
+ Setup de ambiente em um clone.
− CI precisa de filtro por caminho, senão todo PR roda tudo.
− Histórico misturado: `git log apps/api` passa a ser reflexo, não opção.
− Se um dia o front for para a Vercel e o core para a Magalu, o deploy lê partes
  diferentes do mesmo repo — aceitável, mas exige contexto de build explícito.
− Publicar o repositório expõe infra e evals junto com o código; a separação
  público/privado deixa de ser por repo e passa a ser por conteúdo.

## Alternativas consideradas

- **Polirrepo (api / web / infra / docs).** Isolamento real de deploy e
  permissão, ao custo de versionar o contrato como pacote e de PRs coordenados
  entre repos para qualquer mudança que atravesse a fronteira. Custo alto demais
  para um time de uma pessoa.
- **Monorepo com Turborepo ou Nx.** Cache de build e grafo de dependências que
  este volume não justifica; o Python ficaria de fora do grafo de qualquer
  forma.
- **Dois repos: código e docs.** Reintroduz exatamente a divergência que o
  princípio do projeto ataca — doc fora do repo apodrece.
