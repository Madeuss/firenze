# ADR-0007: One port for any model provider, and the provider chosen later

## Status

Accepted — 2026-08-31

## Context

The veneer was written against the Anthropic SDK directly: the import, the
client, `messages.parse`, `output_format`, `stop_reason == "refusal"`. That was
the right way to get it working and the wrong thing to keep, because the
provider is not decided. Some API will be called; which one is open.

Building the rest of the game on top of an undecided dependency has two failure
modes. The obvious one is a rewrite when the decision lands. The subtler one is
that provider vocabulary spreads: a stance machine that knows what a
`stop_reason` is, an eval suite that counts tokens the way one vendor reports
them, a turn pipeline whose retry logic assumes one provider's error taxonomy.
None of that announces itself as coupling until the day it has to be undone.

There is also a practical constraint worth stating: the next phases have to be
built before any key exists. Most of a turn does not need a model — dossier
assembly (RN-010), schema validation (RN-022), the stance machine (RN-023),
canary and scope filtering (RN-042), turn accounting (RN-030) are all
deterministic. Only the prose needs one.

## Decision

Everything a model can be asked for goes through one interface in
`firenze.model`:

```python
def complete(self, *, system: str, user: str, schema: type[Schema], max_tokens: int) -> Schema
```

A system prompt, a user prompt, a schema; an instance of that schema, or a
failure. Two failures, kept apart: `ModelUnavailable` (no provider, no
credentials, transport) and `ModelRefused` (the provider declined). A refusal is
a fact about the request and belongs in the evals; burying it in a generic
failure would hide it exactly when it matters.

Adapters live in the same package and nowhere else. Two exist:

- **`AnthropicModel`** — the code that was already written, now one
  implementation rather than the implementation. Not a commitment.
- **`FakeModel`** — no network, no key, no money. Deterministic, and it names
  itself `fake` so anything it wrote is traceable to it.

`FIRENZE_MODEL_PROVIDER` defaults to `none`, which raises rather than picking
one. A default provider would be the decision being made quietly by whoever set
the default.

**This interface is affordable because of what this project already decided.**
Nothing in the deduction path asks a model for anything: the solver, the
verdict, the scoring and contradiction detection are code (RN-023, RN-032). A
model writes prose and proposes a stance, and both come back as a validated
schema. An application whose business logic ran through tool calling could not
draw the line this tightly.

## Consequences

+ Choosing a provider is a new file in one package plus a line of configuration.
+ The game can be built and played before that choice, and a front end can be
  developed against a running backend with no key and no bill.
+ Provider vocabulary cannot spread, because no other module can name it.
+ Failures arrive already classified, so callers degrade on a policy rather than
  on a vendor's exception hierarchy.
− Provider features outside the interface are unreachable without widening it:
  streaming, tool calling, prompt caching, thinking budgets. Streaming in
  particular will need a second method when the front end arrives, and that is a
  deliberate later decision rather than an oversight.
− The port cannot express per-provider tuning — cache breakpoints, effort
  levels — so cost optimisation that depends on them is invisible from outside
  the adapter.
− Two adapters to keep working, one of which nothing in production will use.
− A fake that satisfies schemas will still fail domain validation, because it
  invents content that belongs to no case. That is correct, and it means the
  fake proves pipelines, never output quality.

## Alternatives considered

- **Keep calling the SDK directly and abstract when the provider is chosen.**
  Cheaper today. Rejected because the coupling that hurts is not the import — it
  is the vocabulary that leaks into modules written between now and then, and by
  the time it is visible it is spread across the phases that were built in the
  meantime.
- **Adopt a framework's model abstraction (LangChain, LiteLLM).** A ready port
  supporting many providers. Rejected for now: it brings an abstraction far
  wider than one method, and its own release cadence, to solve a problem this
  project has already narrowed to a single call. Worth revisiting if the port
  ever needs streaming, tool calling and caching at once — at which point
  reimplementing it would be the mistake.
- **Decide the provider now.** The honest blocker is that the decision has
  inputs nobody has yet: cost per match against real usage, and injection
  resistance per language measured on the eval suite from phase 6. Deciding
  before those exist would mean deciding on vibes and then defending it.
