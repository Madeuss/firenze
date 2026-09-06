"""One suspect, one question or one piece of evidence, one guarded answer."""

from firenze.interrogation.confrontation import COST, Landed, weigh
from firenze.interrogation.contradictions import Contradiction, contradicts, find
from firenze.interrogation.dossier import Dossier, build
from firenze.interrogation.guard import ReplyRejected
from firenze.interrogation.models import NpcReply
from firenze.interrogation.turn import (
    PROMPT_VERSION,
    NoTurnsLeft,
    TurnResult,
    UnknownEvidence,
    ask,
    confront,
)

__all__ = [
    "COST",
    "PROMPT_VERSION",
    "Contradiction",
    "Dossier",
    "Landed",
    "NoTurnsLeft",
    "NpcReply",
    "ReplyRejected",
    "TurnResult",
    "UnknownEvidence",
    "ask",
    "build",
    "confront",
    "contradicts",
    "find",
    "weigh",
]
