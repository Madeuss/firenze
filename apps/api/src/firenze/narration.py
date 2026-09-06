"""Writing the ending of a match whose ending is already decided. (RN-032)

The order is the whole safety argument, and it is worth stating in one line:
**the verdict exists before this module is called.** Score, culprit and whether
the player was right are arithmetic (`firenze.verdict`, which cannot even import
a model). This asks a model to write that up.

A prompt that could be argued into a different outcome would be a prompt that
decides outcomes. This one is shown the answer, so the worst it can do is write
badly — and writing badly is a quality problem, not a fairness one.

## Failure is cosmetic here, and that is designed

If the model is unreachable, refuses, or produces something that fails a check,
the match still ends with the same verdict and the player still sees the truth.
The epilogue is absent, not the ending. Any other arrangement would make the
outcome depend on a model being up, which is the thing RN-032 exists to prevent.
"""

import re

from pydantic import BaseModel, ConfigDict, Field

from firenze.domain import Case
from firenze.i18n import Catalog
from firenze.model import ModelRefused, ModelUnavailable, StructuredModel
from firenze.prompts import prompts_dir
from firenze.verdict import Verdict

PROMPT_VERSION = "v1"
MAX_TOKENS = 800
MAX_EPILOGUE_CHARS = 2000
CANARY = re.compile(r"CN-[0-9a-f]{8}")


class Epilogue(BaseModel):
    """The only thing the model is asked for."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(description="Two or three short paragraphs closing the case.")


class NarrationRejected(ValueError):
    """The epilogue failed a check. The verdict is unaffected."""

    def __init__(self, check: str, detail: str) -> None:
        super().__init__(f"{check}: {detail}")
        self.check = check
        self.detail = detail


def load_prompt(version: str = PROMPT_VERSION) -> tuple[str, str]:
    path = prompts_dir() / "verdict" / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"verdict prompt {version} not found at {path}")

    body = path.read_text(encoding="utf-8").split("---", 2)[-1]
    parts = re.split(r"^## User\s*$", body, flags=re.MULTILINE)
    if len(parts) != 2:
        raise ValueError(f"verdict prompt {version} has no User section")
    return parts[0].strip(), parts[1].strip()


def render(verdict: Verdict, accused: str, case: Case, catalog: Catalog) -> tuple[str, str]:
    system, user = load_prompt()
    return (
        system.format(
            language=catalog.label("language_name"),
            accused=case.name_of(accused),
            culprit=case.name_of(verdict.culprit),
            right_or_wrong=catalog.label("right" if verdict.correct else "wrong"),
            means=catalog.means(verdict.means_key),
            motive=catalog.motive(verdict.motive_key),
        ),
        user,
    )


def check(epilogue: Epilogue, case: Case) -> None:
    """What can be checked mechanically about an ending."""
    text = epilogue.text
    if not text.strip():
        raise NarrationRejected("empty", "the epilogue has no text")
    if len(text) > MAX_EPILOGUE_CHARS:
        raise NarrationRejected("length", f"the epilogue runs {len(text)} chars")
    if CANARY.search(text):
        raise NarrationRejected("canary", "the epilogue carries a canary token")

    # There is no check here for invented characters, and the absence is
    # deliberate. The obvious one — flag capitalised word pairs that are not in
    # the cast — rejected "Foi Vitória Belmiro que..." on its first run, because
    # a sentence-initial verb reads exactly like a first name. Prose defeats
    # that shape of rule, and a false positive here costs a player the ending of
    # a match they finished. It is the same failure the classifier prompt spends
    # most of its words avoiding: refusing good input is worse than accepting
    # imperfect input, when the imperfect input cannot leak anything.


def write(
    verdict: Verdict,
    accused: str,
    case: Case,
    catalog: Catalog,
    *,
    model: StructuredModel,
) -> str | None:
    """Return the epilogue, or `None` if one could not be produced.

    Never raises. The caller has a verdict already and is owed an ending
    regardless of what any model did.
    """
    try:
        system, user = render(verdict, accused, case, catalog)
        epilogue = model.complete(system=system, user=user, schema=Epilogue, max_tokens=MAX_TOKENS)
        check(epilogue, case)
    except (ModelRefused, ModelUnavailable, NarrationRejected, FileNotFoundError, ValueError):
        return None
    return epilogue.text
