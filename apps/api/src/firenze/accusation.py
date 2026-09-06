"""Turning what a player typed into the form they would otherwise have filled.

Two paths reach one accusation. A front end can let somebody pick a suspect and
tick evidence, or let them write *"foi a governanta, por causa da herança, e a
prova é o lenço"*. Both arrive at the same structure, and **only the structure
can be submitted**.

That is what makes the confirmation real rather than a habit: there is no
endpoint that accuses in prose. Parsing produces a draft; the player confirms it
by sending the fields back. An accusation is irreversible (RN-031), so a
misreading that went straight through would cost somebody their match for a
sentence they did not write.

## The model is a parser here, never a judge

It is shown the cast, the evidence the player actually holds, and the motives
they could name — and it may answer only with ids from those lists. Whether the
accusation is *right* is arithmetic that runs afterwards (RN-032), and this file
imports nothing that could compute it.

Anything it cannot place goes to `unresolved` and is shown back to the player.
Guessing would put words in their mouth at the one moment that cannot be undone.
"""

import re

from pydantic import BaseModel, ConfigDict, Field

from firenze.domain import Case, FactKind, Match
from firenze.i18n import Catalog
from firenze.model import StructuredModel
from firenze.prompts import prompts_dir

PROMPT_VERSION = "v1"
MAX_TOKENS = 600
MAX_TEXT_CHARS = 1000


class Draft(BaseModel):
    """What the parser produced. Not an accusation until the player says so."""

    model_config = ConfigDict(frozen=True)

    culprit: str | None = Field(default=None, description="Suspect id, or nothing.")
    motive_key: str | None = Field(default=None, description="Motive key, or nothing.")
    evidence: tuple[str, ...] = Field(default=(), description="Fact ids offered in support.")
    unresolved: tuple[str, ...] = Field(
        default=(), description="What could not be placed, in the player's own words."
    )


def known_motives(match: Match) -> tuple[str, ...]:
    """Motives the player could name, from the motive facts they hold.

    Not the full catalogue. Offering every motive would turn twenty points into
    a one-in-four guess, and a player who never found the quarrel has not earned
    a shortlist of what it might have been.
    """
    held = match.evidence
    return tuple(
        sorted(
            {
                fact.motive_key
                for fact in match.case.facts
                if fact.kind is FactKind.motive and fact.motive_key and fact.id in held
            }
        )
    )


def load_prompt(version: str = PROMPT_VERSION) -> tuple[str, str]:
    path = prompts_dir() / "accusation" / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"accusation prompt {version} not found at {path}")

    body = path.read_text(encoding="utf-8").split("---", 2)[-1]
    parts = re.split(r"^## User\s*$", body, flags=re.MULTILINE)
    if len(parts) != 2:
        raise ValueError(f"accusation prompt {version} has no User section")
    return parts[0].strip(), parts[1].strip()


def render(match: Match, catalog: Catalog, text: str) -> tuple[str, str]:
    case = match.case
    suspects = "\n".join(f"- {s.id}: {s.name}" for s in case.suspects)
    evidence = (
        "\n".join(
            f"- {fact.id}: {catalog.fact(case, fact)}"
            for fact in case.facts
            if fact.id in match.evidence
        )
        or "- (none — they have been told nothing they could present)"
    )
    motives = (
        "\n".join(f"- {key}: {catalog.motive(key)}" for key in known_motives(match))
        or "- (none — they never found out why)"
    )

    system, user = load_prompt()
    return (
        system.format(suspects=suspects, evidence=evidence, motives=motives),
        user.format(text=text[:MAX_TEXT_CHARS]),
    )


def parse(match: Match, catalog: Catalog, text: str, *, model: StructuredModel) -> Draft:
    """Read an accusation out of prose. Raises if no model can be reached."""
    system, user = render(match, catalog, text)
    draft = model.complete(system=system, user=user, schema=Draft, max_tokens=MAX_TOKENS)
    return tidy(draft, match)


def tidy(draft: Draft, match: Match) -> Draft:
    """Drop anything the case does not recognise, and say what was dropped.

    The prompt asks for ids from the lists it was given; this is what happens
    when it answers with something else anyway. Silently keeping an unknown id
    would push the failure to the moment the accusation is committed, which is
    the moment there is no going back.
    """
    suspects = {s.id for s in match.case.suspects}
    motives = set(known_motives(match))

    culprit = draft.culprit if draft.culprit in suspects else None
    motive = draft.motive_key if draft.motive_key in motives else None
    evidence = tuple(e for e in draft.evidence if e in match.evidence)

    dropped = [
        *([f"suspect {draft.culprit!r}"] if draft.culprit and culprit is None else []),
        *([f"motive {draft.motive_key!r}"] if draft.motive_key and motive is None else []),
        *[f"evidence {e!r}" for e in draft.evidence if e not in match.evidence],
    ]
    return Draft(
        culprit=culprit,
        motive_key=motive,
        evidence=evidence,
        unresolved=(*draft.unresolved, *dropped),
    )


def summarise(draft: Draft, case: Case, catalog: Catalog) -> str:
    """The sentence the player confirms. Plain, and never persuasive."""
    who = case.name_of(draft.culprit) if draft.culprit else catalog.label("nobody")
    why = catalog.motive(draft.motive_key) if draft.motive_key else catalog.label("no_motive")
    what = (
        ", ".join(catalog.fact(case, case.fact(e)) for e in draft.evidence)
        if draft.evidence
        else catalog.label("no_evidence")
    )
    return catalog.label("accusation_summary").format(who=who, why=why, what=what)
