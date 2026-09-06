"""The first of four checkpoints. (RN-040)

Every player message is labelled before any suspect sees it. What makes this
worth doing is not the label — it is that the classifier is a **poor target**:
it is shown one sentence, never the case, never a dossier, never a system prompt
worth extracting. A model with no secrets cannot be talked out of any.

The message classified as `injection` never reaches the NPC (RN-041). That is
the point of ordering it first: the defence is that the attack does not arrive,
not that the character resists it.

## When the classifier itself is unreachable

The turn stops and is not charged. Failing open would send unlabelled input to a
character; failing closed by treating it as an attack would punish a player for
an outage. Neither is right, and neither is necessary — nothing was asked of
anybody, so nothing happened.
"""

import re

from firenze.domain import Intent
from firenze.model import StructuredModel
from firenze.prompts import prompts_dir
from firenze.safety.models import Classification

PROMPT_VERSION = "v1"
MAX_TOKENS = 200
MAX_MESSAGE_CHARS = 500


def load_prompt(version: str = PROMPT_VERSION) -> tuple[str, str]:
    path = prompts_dir() / "classifier" / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"classifier prompt {version} not found at {path}")

    body = path.read_text(encoding="utf-8").split("---", 2)[-1]
    parts = re.split(r"^## User\s*$", body, flags=re.MULTILINE)
    if len(parts) != 2:
        raise ValueError(f"classifier prompt {version} has no User section")
    return parts[0].strip(), parts[1].strip()


def classify(message: str, *, model: StructuredModel) -> Classification:
    """Label one player message. Raises `ModelUnavailable` if it cannot."""
    system, user = load_prompt()

    return model.complete(
        system=system,
        # Truncated before the model sees it. A long message is either a paste
        # or an attempt to bury an instruction past the point anyone reads, and
        # neither needs more than this to classify.
        user=user.format(message=message[:MAX_MESSAGE_CHARS]),
        schema=Classification,
        max_tokens=MAX_TOKENS,
    )


def is_hostile(intent: Intent) -> bool:
    """Whether the message stops here instead of reaching a character."""
    return intent is Intent.injection
