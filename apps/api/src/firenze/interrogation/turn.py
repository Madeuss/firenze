"""One turn: a question in, a guarded statement out.

The order matters and is the whole design:

    dossier → prompt → model → schema → scope → canary → stance → statement

Everything before the model is projection, and everything after it is
verification. The model sits in the middle producing one thing — a line of
dialogue — and every consequence of that line is decided by code around it
(RN-022, RN-023, RN-042).

What a turn costs depends on what happened, and the three cases are not the
same:

- **produced, then discarded** — charged. The system chose not to show it; the
  player still had their go, and a budget that only charged for answers the
  system liked would be a budget to farm.
- **classified as an attack** — charged. It reached a checkpoint and got an
  answer, just not from a model (RN-041).
- **never produced** — not charged. No provider, no credentials, no route to the
  host: nothing was asked of anybody, so nothing happened.
"""

import re

from pydantic import BaseModel, ConfigDict

from firenze.domain import Intent, Match, Stance, Statement
from firenze.i18n import Catalog
from firenze.interrogation import stance as stance_machine
from firenze.interrogation.dossier import Dossier, build
from firenze.interrogation.guard import ReplyRejected, check
from firenze.interrogation.models import NpcReply
from firenze.model import ModelRefused, StructuredModel
from firenze.prompts import prompts_dir
from firenze.safety import classify, is_hostile

PROMPT_VERSION = "v1"
MAX_TOKENS = 1000


class NoTurnsLeft(RuntimeError):
    """The budget is spent. The match moves on to the accusation. (RN-030)"""


class TurnResult(BaseModel):
    """What a turn produced, and what it cost."""

    model_config = ConfigDict(frozen=True)

    match: Match
    statement: Statement | None
    rejection: str | None = None
    stance_overruled: bool = False
    """True when the model suggested a move the machine would not allow."""
    intent: Intent = Intent.question
    """How the question was labelled before anyone answered it."""


def load_prompt(version: str = PROMPT_VERSION) -> tuple[str, str]:
    path = prompts_dir() / "npc" / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt {version} not found at {path}")

    text = path.read_text(encoding="utf-8")
    body = text.split("---", 2)[-1]
    parts = re.split(r"^## User\s*$", body, flags=re.MULTILINE)
    if len(parts) != 2:
        raise ValueError(f"prompt {version} has no User section")
    return parts[0].strip(), parts[1].strip()


def render(dossier: Dossier, catalog: Catalog, match: Match, question: str) -> tuple[str, str]:
    """Fill the prompt from the dossier. Nothing else is in scope to fill it from."""
    system, user = load_prompt()
    case = match.case

    facts = "\n".join(f"- [{fact.id}] {catalog.fact(case, fact)}" for fact in dossier.facts)
    history = (
        "\n".join(f'- Você disse: "{said.line}"' for said in dossier.said_before)
        or "- Nada ainda. Esta é a primeira pergunta que lhe fazem."
    )
    guilt = (
        "Você matou a vítima. Ninguém viu. Você não sabe o que os outros sabem, "
        "nem o que descobriram."
        if dossier.is_culprit
        else ""
    )

    return (
        system.format(
            name=dossier.name,
            language=catalog.label("language_name"),
            facts=facts,
            guilt=guilt,
            stance=dossier.stance.value,
            history=history,
        ),
        user.format(question=question),
    )


def ask(
    match: Match,
    character: str,
    question: str,
    *,
    catalog: Catalog,
    model: StructuredModel,
    classifier: StructuredModel | None = None,
) -> TurnResult:
    """Put a question to one suspect.

    Raises `ModelUnavailable` when no model could be reached at all — the caller
    turns that into a 503 and the turn is not charged. Everything a model did
    produce, including a refusal, comes back as a result.
    """
    if match.turns_left <= 0:
        raise NoTurnsLeft("no turns left in this match")

    dossier = build(match, character)
    spent = match.model_copy(update={"turns_left": match.turns_left - 1})

    # First checkpoint, and the only one that can stop the message from ever
    # reaching a character (RN-040, RN-041).
    intent = classify(question, model=classifier or model).intent
    if is_hostile(intent):
        return _deflect(match, spent, dossier, catalog, question, intent)

    system, user = render(dossier, catalog, match, question)

    try:
        reply = model.complete(system=system, user=user, schema=NpcReply, max_tokens=MAX_TOKENS)
    except ModelRefused as refusal:
        # Produced: the provider decided. Charged, and worth counting.
        return TurnResult(match=spent, statement=None, rejection=str(refusal), intent=intent)

    try:
        check(reply, dossier)
    except ReplyRejected as rejected:
        # Discarded, not repaired. The turn is still spent.
        return TurnResult(match=spent, statement=None, rejection=str(rejected), intent=intent)

    settled = stance_machine.settle(dossier.stance, reply.stance)
    statement = Statement(
        turn=len(match.statements) + 1,
        character=character,
        question=question,
        line=reply.line,
        stance=settled,
        lied=reply.lied,
        fact_referenced=reply.fact_referenced,
        intent=intent,
    )

    return TurnResult(
        match=spent.model_copy(
            update={
                "statements": (*match.statements, statement),
                "stances": {**match.stances, character: settled},
            }
        ),
        statement=statement,
        stance_overruled=settled is not reply.stance,
        intent=intent,
    )


def _deflect(
    match: Match,
    spent: Match,
    dossier: Dossier,
    catalog: Catalog,
    question: str,
    intent: Intent,
) -> TurnResult:
    """Answer a hostile message in character, without asking a model anything.

    This is the whole value of classifying first: the attack does not arrive.
    Nothing about the case, the dossier or the system prompt was in reach of the
    text that produced this reply (RN-041).
    """
    statement = Statement(
        turn=len(match.statements) + 1,
        character=dossier.character,
        question=question,
        line=catalog.deflection(len(match.statements)),
        stance=dossier.stance,
        lied=False,
        intent=intent,
    )
    return TurnResult(
        match=spent.model_copy(update={"statements": (*match.statements, statement)}),
        statement=statement,
        intent=intent,
    )


def opening_stance() -> Stance:
    return Stance.cooperative
