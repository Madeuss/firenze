"""What a reply has to survive before a player sees it. (RN-042)

Three checks, in order of severity.

**Canary.** Every restricted fact carries a token (RN-012). One in the output
means a secret reached the model as text and came back out. The reply is
discarded and the event is recorded; there is no version of this that gets
repaired and shown.

**Scope.** A reply may cite a fact — that is what `fact_referenced` is for — but
only one this suspect actually holds. Citing a fact from someone else's dossier
means the context was assembled wrong, which is a bug on our side rather than a
lie on theirs (RN-010).

**Shape.** An empty line is not an answer, and a runaway one is a model that
stopped playing a character and started narrating.

The stance is not checked here. An illegal stance is not a violation to reject —
it is a suggestion to overrule, and `stance.settle` does that.
"""

import re

from firenze.interrogation.dossier import Dossier
from firenze.interrogation.models import NpcReply

CANARY = re.compile(r"CN-[0-9a-f]{8}")
MAX_LINE_CHARS = 1200


class ReplyRejected(ValueError):
    """A reply that leaked, cited what it could not know, or was not an answer."""

    def __init__(self, check: str, detail: str) -> None:
        super().__init__(f"{check}: {detail}")
        self.check = check
        self.detail = detail


def check(reply: NpcReply, dossier: Dossier) -> None:
    """Raise `ReplyRejected` on the first violation."""
    no_canary(reply)
    only_known_facts(reply, dossier)
    is_an_answer(reply)


def no_canary(reply: NpcReply) -> None:
    """RN-012. Critical: the response is discarded, never edited."""
    leaked = CANARY.findall(reply.line)
    if leaked:
        raise ReplyRejected("canary", f"secret token in the reply: {sorted(set(leaked))}")


def only_known_facts(reply: NpcReply, dossier: Dossier) -> None:
    """A suspect may only cite what is in their own dossier. (RN-010)"""
    known = {fact.id for fact in dossier.facts}
    for field, cited in (
        ("fact_referenced", reply.fact_referenced),
        ("clue_revealed", reply.clue_revealed),
    ):
        if cited and cited not in known:
            raise ReplyRejected(
                "scope",
                f"{dossier.character} cited {cited} via {field}, which is not in their dossier",
            )


def is_an_answer(reply: NpcReply) -> None:
    if not reply.line.strip():
        raise ReplyRejected("empty", "the reply has no line")
    if len(reply.line) > MAX_LINE_CHARS:
        raise ReplyRejected("length", f"the line runs {len(reply.line)} chars")
