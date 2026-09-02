# ADR-0008: Magalu Prosa as the model provider

## Status

Accepted — 2026-08-31. Blocked on the product leaving pilot.

## Context

ADR-0007 put every model call behind one port and deliberately left the provider
open, saying the decision needed inputs that did not exist yet: cost measured
against real usage, and injection resistance per language measured on the phase-6
eval suite.

The decision is being made before those inputs exist, on different grounds. That
is worth stating plainly rather than pretending the evidence arrived early.

The grounds that do exist:

- **The credits are already there.** Magalu Cloud credits are held; an API
  billed to a card is not. For a study project, the difference between spending
  credits and spending money is the difference between experimenting freely and
  rationing.
- **The infrastructure is already there.** ADR-0002 puts Postgres with pgvector
  on Magalu, and phase 7 puts the application there. Inference in the same place
  means one account, one bill, one network.
- **Prosa speaks the OpenAI dialect.** Its documentation is explicit: *"uma API
  compatível com o padrão OpenAI"*. So the adapter is not a Prosa adapter — it
  is an OpenAI-compatible adapter with a base URL, and every other compatible
  endpoint is reachable by configuration.
- **A monthly budget in R$ that pauses consumption at the limit.** The eval plan
  caps cost per match; a provider that enforces a ceiling is closer to that
  requirement than one that emails an invoice.
- **Supporting a Brazilian cloud is a reason the author holds.** Not an
  engineering argument, and it does not need to pretend to be one.

## Decision

Magalu Prosa, through a generic OpenAI-compatible adapter in
`firenze.model.openai_compatible`, configured by `FIRENZE_MODEL_BASE_URL`,
`FIRENZE_MODEL_NAME` and `FIRENZE_MODEL_API_KEY`.

The default provider stays `none` until the product leaves pilot and credentials
exist. `fake` covers development in the meantime.

**Structured output is handled by the adapter, because the documentation does
not say what the gateway supports.** It tries a server-enforced JSON schema,
then JSON mode with the schema in the prompt, then a plain request parsed out of
the reply — keeping whichever works. All three failing is a failure; a response
that does not validate is discarded, never repaired (RN-022).

## Consequences

+ Inference, database and hosting on one account, paid with credits already
  held.
+ A hard monthly ceiling in the currency the eval plan is written in.
+ The adapter is generic, so a second provider — or a local vLLM — is a base URL
  away. Nothing about this decision is expensive to reverse, which is what makes
  it safe to take early.
+ The project gets an unusual measurement out of it: open-weights models, served
  from a Brazilian cloud, answering in Portuguese, scored on an adversarial
  suite. That is a more interesting result than passing with a frontier model.
− **The catalog is open-weights — Google, Meta, NVIDIA, Qwen — and those models
  are weaker exactly where phase 3 is hardest.** Injection resistance ≥ 95% and
  persona consistency are the axes where model strength shows most, and ADR-0005
  already records that resistance degrades outside English. Portuguese plus
  open weights is likely the hardest combination this project could pick.
− **Pilot means no guarantees**: the catalog can change, rate limits are
  undocumented, and there is no SLA. Acceptable for a study project and not
  acceptable for anything else.
− Structured output may cost an extra round trip on every call if the gateway
  supports neither schema enforcement nor JSON mode.
− The provider cannot be exercised until launch, so the adapter ships tested
  against fakes only. Its first contact with a real endpoint will find something.

### What does not degrade with a weaker model

Worth being precise, because "weaker model" sounds like it threatens everything
and does not. The canary gate is 0% and stays 0%: isolation is a data boundary,
the model is never given a secret fact, and the filter is code (RN-010, RN-012).
The verdict, the score and contradiction detection are deterministic (RN-032).
What a weaker model costs is **quality** — a character who breaks voice, a reply
in the wrong shape, an injection classified wrong. Those are measurable, and the
eval suite exists to measure them.

## Alternatives considered

- **A frontier provider billed to a card.** Stronger on precisely the axes
  phase 3 measures. Rejected for now: it spends money the project does not need
  to spend, and it would leave R$ 300 of credits unused while making the
  cheapest possible interesting experiment impossible.
- **Wait for the phase-6 evals, as ADR-0007 said.** Consistent, and it would
  block phases 2 to 5 on a decision whose reversal costs one file. The port is
  what makes deciding early cheap; refusing to use it would waste the design.
- **Self-hosted model on a Magalu GPU VM.** Investigated: the account currently
  lists 50 machine types and none with a GPU, so it needs a quota request. Also
  bills per hour of uptime rather than per token, which inverts the economics
  for intermittent development use. Stays a phase-8 experiment, to be run
  against the eval suite and written up.
