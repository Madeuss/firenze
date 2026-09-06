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

**Claim.** A reply that says where the character was must name a room the case
has and an interval it covers. An invented room is not a lie the game can reason
about — RN-021 compares claims, and a claim about a room that does not exist
cannot be compared with anything.

**Shape.** An empty line is not an answer, and a runaway one is a model that
stopped playing a character and started narrating.

The stance is not checked here. An illegal stance is not a violation to reject —
it is a suggestion to overrule, and `stance.settle` does that.
"""

import re

from firenze.domain import Case
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


def check(reply: NpcReply, dossier: Dossier, case: Case | None = None) -> None:
    """Raise `ReplyRejected` on the first violation."""
    no_canary(reply)
    only_known_facts(reply, dossier)
    if case is not None:
        claim_is_about_this_case(reply, case)
    is_an_answer(reply)


def claim_is_about_this_case(reply: NpcReply, case: Case) -> None:
    """A claimed whereabouts has to be somewhere and somewhen in this case."""
    if reply.claimed_room is not None and reply.claimed_room not in case.rooms:
        raise ReplyRejected("claim", f"{reply.claimed_room!r} is not a room in this case")
    if reply.claimed_interval is not None and not 0 <= reply.claimed_interval < case.interval_count:
        raise ReplyRejected("claim", f"interval {reply.claimed_interval} is outside this night")
    if (reply.claimed_room is None) != (reply.claimed_interval is None):
        raise ReplyRejected("claim", "a room without an interval says nothing comparable")


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
