# ADR-0001: One repository for app, infrastructure, evals and docs

## Status

Accepted — 2026-08-29

## Context

The project has five artefacts that change together often: the AI core
(Python), the front end (TypeScript), the infrastructure (Terraform), the eval
suites (data plus configuration) and the documentation (Markdown, ADRs, agent
cards).

Three couplings define the problem:

- **The HTTP contract.** The front end consumes types generated from the
  backend's OpenAPI. In separate repositories, breaking the contract only
  surfaces later — at runtime, or on the next release of the types package.
- **Prompt and eval.** Changing a prompt requires running the matching evals in
  the same pull request; that is a CI gate, not good intentions. If prompt and
  eval live in different repositories, the gate is bypassable by construction.
- **Doc and code.** The project's principle is docs-as-code: a business rule
  cited by number in the code (`# RN-012`) and defined under `docs/`. Splitting
  them throws away the ability to review both in the same diff.

Operating context: a single developer, one CI environment, no need for distinct
permissions per artefact, and no external consumers of the code.

## Decision

A single repository, with workspaces per language and no monorepo orchestrator:

```
apps/api            FastAPI — AI core and domain
apps/web            Next.js — BFF and UI
packages/contracts  TS types generated from the committed openapi.json
infra/              terraform, compose, k8s
evals/              datasets and suites
docs/               plan, domain, rules, ADRs, agent cards
prompts/            versioned prompts
```

Each app keeps its native toolchain (`uv`/`ruff`/`pytest` on the Python side,
`pnpm`/`eslint`/`tsc` on the TypeScript side). The root exposes a `Makefile` as
a façade — `make dev`, `make evals`, `make migrate` — and CI triggers jobs by
changed path, not through a task graph.

**No Nx, Turborepo or Bazel.** They solve build time in large repositories with
many teams; here they would only add configuration.

## Consequences

+ A broken contract becomes a build error in the same pull request that broke it.
+ One pull request carries the prompt change, the eval and the doc — reviewable
  as a unit.
+ One version, one CHANGELOG, one history. `git bisect` crosses the whole stack.
+ Environment setup in a single clone.
− CI needs path filtering, or every pull request runs everything.
− Mixed history: `git log apps/api` becomes a reflex rather than an option.
− If the front end goes to Vercel and the core to Magalu, deployment reads
  different parts of the same repository — acceptable, but it demands explicit
  build context.
− Publishing the repository exposes infrastructure and evals alongside the code;
  the public/private split stops being per repository and becomes per content.

## Alternatives considered

- **Multiple repositories (api / web / infra / docs).** Real isolation of
  deployment and permissions, at the cost of versioning the contract as a
  package and coordinating pull requests across repositories for any change that
  crosses the boundary. Too expensive for a team of one.
- **Monorepo with Turborepo or Nx.** Build caching and a dependency graph this
  volume does not justify, and Python would sit outside the graph anyway.
- **Two repositories: code and docs.** Reintroduces exactly the drift the
  project's principle attacks — documentation outside the repository rots.
