# ADR-0005: The domain holds structure, not prose, and locale belongs to the match

## Status

Accepted — 2026-08-29

## Context

The game is meant to be played in more than one language. That looks like a
normal internationalisation problem and is not, because most of what a player
reads does not exist until the moment they play: an NPC's answer is generated at
runtime, while the briefing and the notebook are rendered from stored data.

There are four layers of text, and they need different treatment:

| Layer | Example | Produced |
|---|---|---|
| Interface | buttons, menus | at build time |
| Structural text | "Ondina was in the cellar at 22:00" | from stored data |
| Generated text | an NPC's reply, the verdict narration | at runtime, by a model |
| Player input | the question typed into the box | by the player |

The first version of the generator wrote finished Portuguese sentences into
`Fato.descricao`, kept pre-formatted times in `INTERVALOS`, used room display
names as identifiers, and carried a `PREPOSICAO` map so that "adega" got *na*
and "porão" got *no*. That last one is the clearest symptom: Portuguese grammar
had leaked into the domain model. English does not contract prepositions at all;
German would need three different articles.

## Decision

**The domain holds structure. Prose is produced at the edge, per locale.**

A `Fact` carries a kind and slots — character, room id, interval index. Rooms
are stable identifiers (`cellar`), never display names. Time is minutes on a
clock the case defines, not a formatted string. Secrets, means and motives are
message keys. Nothing in `mansao.domain` contains a sentence.

Catalogs live in `mansao/i18n/messages/<locale>.json` and ship with `pt-BR` and
`en` from day one — a second locale is the only way to know the first one is
actually separable. **Grammar lives in the catalog**: each locale declares the
preposition its rooms need, and its own clock format.

**Locale is a property of the match, chosen at the start and immutable.**

The server renders too, not only the front end: a model asked to play a
character has to read the facts in the language it must answer in. The front end
keeps its own catalog and renders with ICU, so templates here stay simple enough
to translate mechanically between the two.

## Consequences

+ The solver, the contradiction detector and scoring already reason over
  structured fields (RN-021, RN-022), so they are locale-independent for free.
  Had any of them parsed prose, every new language would have multiplied that
  work.
+ Canary filtering (RN-012) is unaffected: a canary is a token, not a language.
+ A missing translation fails a test instead of reaching a player — the suite
  asserts that every key the generator can emit exists in every catalog.
+ Adding a language is a JSON file plus prompt work, not a refactor.
− Reading a fact now costs a catalog lookup; nothing in the data is
  human-readable on its own. Debugging a stored case means rendering it.
− Two catalogs to keep in sync, in two languages, in two places (server and
  front end).
− **Injection resistance varies by language.** A jailbreak that fails in
  Portuguese can succeed in English, because models are unevenly trained across
  languages. The adversarial golden sets (RN-040) need real per-language cases,
  not machine translations of the Portuguese set, and every new locale
  multiplies eval cost. Mitigation: the blocking gate runs the primary locale on
  every PR, the full matrix runs nightly.

### Why locale is immutable within a match

If a player switched language mid-match, previous statements would sit in one
language and new ones in another. Then contradiction detection compares across
languages; NPC memory in pgvector mixes languages in one index and semantic
search degrades; and the character reads as if it had changed personality.
Switching language means starting another match.

## Alternatives considered

- **Keep prose in the data, translate on the way out.** Machine-translating a
  stored Portuguese sentence is cheap, but it doubles generation cost for NPC
  dialogue and flattens the voice the persona work exists to build. It also
  makes the canary filter run on text the model never produced.
- **Render only on the front end, no server catalog.** Tempting, and it works
  right up to the prompt builder: the model needs facts as words. Keeping a
  server catalog means the API can also serve rendered text where a client
  cannot render, at the cost of the two catalogs staying in sync.
- **Full ICU MessageFormat on the server (PyICU).** Correct for plurals and
  gendered agreement, and a heavy native dependency for four templates. The
  current formats are simple enough for slot substitution; when a locale needs
  real plural rules, that is the moment to reconsider — not before.
