"""One suspect, one question, one guarded answer."""

from firenze.interrogation.dossier import Dossier, build
from firenze.interrogation.guard import ReplyRejected
from firenze.interrogation.models import NpcReply
from firenze.interrogation.turn import PROMPT_VERSION, TurnResult, ask

__all__ = [
    "PROMPT_VERSION",
    "Dossier",
    "NpcReply",
    "ReplyRejected",
    "TurnResult",
    "ask",
    "build",
]
