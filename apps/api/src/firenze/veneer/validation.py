"""Checks a draft has to survive before it becomes prose anyone reads.

The model is not malicious and is still not trusted. It is a text generator
pointed at a mystery, and the failure that matters is not a jailbreak — it is a
model that quietly writes something the structure does not support, and a case
that reads as broken three questions into the interrogation.

What can be checked mechanically is checked here. What cannot — whether the
prose is any good — is not pretended to be checked.
"""

import re

from firenze.domain import Case
from firenze.veneer.models import VeneerDraft


class VeneerRejected(ValueError):
    """A draft that contradicts the case, or leaks. Discarded, never repaired."""

    def __init__(self, check: str, detail: str) -> None:
        super().__init__(f"{check}: {detail}")
        self.check = check
        self.detail = detail


CANARY = re.compile(r"CN-[0-9a-f]{8}")
MAX_FIELD_CHARS = 400


def check(draft: VeneerDraft, case: Case) -> None:
    """Run every check. Raises `VeneerRejected` on the first failure."""
    no_canary_leaked(draft, case)
    exactly_the_cast(draft, case)
    names_are_not_reassigned(draft, case)
    fields_are_within_bounds(draft)


def _all_text(draft: VeneerDraft) -> str:
    parts = [draft.scene]
    for character in draft.characters:
        parts += [character.role_title, character.appearance, character.manner]
    return "\n".join(parts)


def no_canary_leaked(draft: VeneerDraft, case: Case) -> None:
    """A canary in model output is a critical failure. (RN-012)

    The veneer is only shown facts that are public, so a canary here means the
    context assembly is wrong — a bug upstream, not a bad sentence. The response
    is discarded either way.
    """
    text = _all_text(draft)
    known = {fact.canary for fact in case.facts if fact.canary}
    leaked = sorted(token for token in CANARY.findall(text) if token in known)
    if leaked:
        raise VeneerRejected("canary", f"secret fact tokens in the output: {leaked}")
    if CANARY.search(text):
        raise VeneerRejected("canary", "output carries a canary-shaped token")


def exactly_the_cast(draft: VeneerDraft, case: Case) -> None:
    """No invented character, none dropped, no id renamed."""
    expected = {c.id for c in case.suspects}
    received = {c.id for c in draft.characters}
    if received != expected:
        raise VeneerRejected(
            "cast",
            f"invented {sorted(received - expected)}, missing {sorted(expected - received)}",
        )
    if len(draft.characters) != len(received):
        raise VeneerRejected("cast", "the same id appears twice")


def names_are_not_reassigned(draft: VeneerDraft, case: Case) -> None:
    """A character must not be described using another character's name.

    Cheap to check and worth checking: swapping two names is the kind of mistake
    that survives a read-through and then contradicts every alibi in the case.
    """
    for character in draft.characters:
        own = case.name_of(character.id)
        others = {c.name for c in case.suspects if c.id != character.id} - {own}
        text = f"{character.role_title} {character.appearance} {character.manner}"
        intruders = sorted(name for name in others if name in text)
        if intruders:
            raise VeneerRejected("names", f"{character.id} is described as {intruders}")


def fields_are_within_bounds(draft: VeneerDraft) -> None:
    """A field that runs long is a model that started narrating the case."""
    for character in draft.characters:
        for field, value in (
            ("role_title", character.role_title),
            ("appearance", character.appearance),
            ("manner", character.manner),
        ):
            if not value.strip():
                raise VeneerRejected("empty", f"{character.id}.{field} is blank")
            if len(value) > MAX_FIELD_CHARS:
                raise VeneerRejected("length", f"{character.id}.{field} is {len(value)} chars")
    if not draft.scene.strip():
        raise VeneerRejected("empty", "scene is blank")
