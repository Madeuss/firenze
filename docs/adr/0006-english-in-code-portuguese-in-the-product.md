# ADR-0006: English in the code, Portuguese in the product

## Status

Accepted — 2026-08-29

## Context

The code started in Portuguese — `Caso`, `Fato`, `dossie`, `comodo`,
`rn_004_sem_sobreposicao` — on a domain-driven argument: use the ubiquitous
language of the domain, and the domain is a Brazilian mystery game. The
glossary in `docs/01-dominio.md` even warned against half-translating, which
produces the worst of both worlds (`FactRepository.buscar_por_escopo`).

Two things changed that.

**The product speaks more than one language.** ADR-0005 makes locale a property
of the match and ships `en` alongside `pt-BR`. "The domain is Portuguese" stops
being true the moment the game answers in English.

**The repository is public and part of a portfolio.** The reader who matters is
an engineer doing a technical screen: they spend five to fifteen minutes, read
the README, then open one or two files. A reader who cannot skim
`def rn_004_sem_sobreposicao(completo: CasoCompleto)` cannot evaluate anything,
and the work that went into the design becomes invisible.

The terms translate one to one with no loss — Caso/Case, Fato/Fact,
Dossiê/Dossier, Prova/Evidence, Postura/Stance. This is not a domain with
untranslatable vocabulary, which is where the DDD argument would have real
force.

## Decision

- **Code is English**: identifiers, docstrings, comments, test names, module and
  package names, CLI commands and flags.
- **Rule references stay as they are**: `# RN-012` is a reference code, not a
  word.
- **Documentation stays in Portuguese** for now, except ADRs, which are written
  in English from this one onward. The existing three get translated when time
  allows; they are the highest-value documents for the reader described above.
- **Product content stays Portuguese where it is setting**: character names, the
  manor, the `pt-BR` catalog. A Brazilian manor keeps Brazilian names in every
  locale — translating them would read like bad dubbing.

Timing: the rename lands in the same commit as the ADR-0005 restructuring, which
already rewrites every domain model. Doing it separately would have meant
rewriting the same files twice.

## Consequences

+ A reader can skim the code without knowing Portuguese, which is the point.
+ The split is clean and stateable in one line — interface in English, setting
  in Portuguese — instead of a per-file judgement call.
+ Renaming now costs one PR. After cases are persisted and a front end consumes
  the fields, it would be a migration.
− The glossary in `docs/01-dominio.md` now maps two vocabularies, and both have
  to stay correct.
− Portuguese docs describing English code is a seam. It is a smaller seam than
  half-translated code, and it disappears as the ADRs and the README move to
  English.
− Anyone joining who thinks in the Portuguese domain terms has one extra hop.
  For a solo project this cost is zero today.

## Alternatives considered

- **Keep everything in Portuguese.** Internally consistent, and it makes the
  strongest DDD case. Rejected: it hides the work from exactly the audience the
  repository is public for, and ADR-0005 undercut the premise.
- **Translate the docs too, now.** Two days of work for the documents almost
  nobody opens. Better spent on the README and on the ADRs, which are what gets
  read.
- **English domain names, Portuguese helper names.** The hybrid the glossary
  already warned about. It reads as an unfinished migration, because that is
  what it looks like.
