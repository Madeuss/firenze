# ADR-0010: Classify before the character hears it, and charge for what happened

## Status

Accepted — 2026-08-31

## Context

RN-040 puts a classifier in front of every player message, and RN-041 says a
message labelled `injection` never reaches the NPC. Implementing that raised two
questions the rules do not answer.

**What does the classifying?** A heuristic is free and instant; a model call
costs a second request on every turn, and the turn budget notices.

**What does a turn cost when something goes wrong?** The existing code charged
for everything, which conflated three different situations under one rule.

## Decision

### The classifier is a model call, with its own prompt and no case in reach

`firenze.safety.classify` sends one sentence and a fixed prompt, and gets back
`{intent, reason}`. It is never given the case, a dossier, or anything worth
extracting.

That last part is the design, not a detail. **The classifier is a deliberately
poor target**: a model with no secrets cannot be talked out of any. An attacker
who fully compromises it wins the ability to be labelled `question`, which is
what they would have been labelled anyway — and the message still meets the
output filters (RN-042) and a character who was never told the solution
(RN-011).

The prompt states two rules that matter more than the category definitions: a
hostile question is still a question, because labelling good play as an attack
punishes the player; and the label does not depend on the language, because
ADR-0005 records that resistance does.

`FIRENZE_CLASSIFIER_MODEL_NAME` is separate from the NPC's, because this call
reads one sentence and the cheapest model in a catalogue is usually enough.

### A hostile message is answered without asking any model

The deflection comes from the locale catalog, picked by turn number so the same
probe in the same position always gets the same answer — a probe that produced
varying replies would itself be a signal worth reading. The NPC model is not
called at all, which is the whole value of ordering the classifier first: the
defence is that the attack does not arrive, not that the character resists it.

### A turn costs what happened, and there are three cases

| What happened | Charged | Why |
|---|---|---|
| A reply was produced and then discarded — filters, or a provider refusal | yes | The player had their go; the system chose not to show it. A budget that only charged for answers the system liked would be a budget to farm by provoking failures. |
| The message was labelled an attack | yes | It reached a checkpoint and got an answer, just not from a model. |
| No model could be reached at all | **no** | Nothing was asked of anybody, so nothing happened. It surfaces as 503. |

The previous code charged the third case too. Under it, an outage silently ate a
player's budget — the failure of a component they do not know exists, billed to
them.

## Consequences

+ An injection never reaches a character, so the strongest defence does not
  depend on any character resisting anything.
+ The classifier can be scored on its own against an adversarial golden set,
  independently of whether an NPC would have leaked.
+ The category is recorded per statement, so "how often does this player try" is
  a query rather than a log search.
+ Fail-safe without punishing: an unreachable classifier stops the turn and
  costs nothing.
− **Two model calls per turn.** At Prosa's catalogue prices this is small, and it
  is still the largest single cost increase the turn has taken. A separate,
  cheaper classifier model is the lever; measuring it is phase 6 work.
− A wrong `injection` label costs a player a turn and gives them a canned line —
  the worst failure mode available here, and the reason the prompt spends more
  words on "a hard question is still a question" than on anything else.
− The deflection is fixed text, so a determined player will recognise it. That is
  acceptable: they learn that the wall is a wall.
− `FakeModel` labels everything `question`, so the offline pipeline cannot
  exercise the injection path. The tests use a scripted classifier instead, which
  is what the adversarial suite will replace in phase 6.

## Alternatives considered

- **A deterministic pre-filter — regex, keyword lists.** Free, instant, and
  trivially bypassed by rephrasing; worse, it produces false positives on
  legitimate play ("ignore what I said before, where were you at ten?"). Rejected
  as the primary check. Worth revisiting as a cheap first pass **only** if the
  measured cost of classification becomes a problem, and only for patterns with
  no legitimate reading.
- **No classifier; rely on the NPC prompt and the output filters.** Two
  checkpoints instead of three, and one fewer model call. Rejected because it
  moves the defence into the character, where it depends on the model's
  instruction-following — precisely the property that varies most between the
  open-weights models this project chose (ADR-0008).
- **Classify and continue anyway, using the label only for scoring.** Cheaper to
  reason about and it defeats the purpose: RN-041 exists so the text does not
  arrive.
