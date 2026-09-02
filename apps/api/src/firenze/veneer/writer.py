"""Turns an approved case into prose.

Two boundaries decide the shape of this module.

**It takes `Case`, never `CaseWithSolution`.** The same discipline as the solver,
for a different reason: if the writer knew who the culprit was, the writing would
telegraph it. Nobody would mean to — but the guilty character would end up with
the sharper description, and the game would be over before the first question.

**It is only shown public facts.** The veneer has no use for a restricted fact,
so it never receives one, and therefore cannot leak one. The canary check on the
output is not there to catch the model; it is there to catch us, because a canary
in this output means context assembly upstream is broken (RN-010, RN-012).

The prompt lives in `prompts/veneer/`, versioned, never as a string literal,
and the model arrives through the port in `firenze.model` — this module has
never heard of a provider (ADR-0007).
"""

import re

from firenze.domain import Case
from firenze.i18n import Catalog
from firenze.model import ModelRefused, ModelUnavailable, StructuredModel
from firenze.prompts import prompts_dir
from firenze.veneer.models import CaseVeneer, VeneerDraft
from firenze.veneer.validation import check

PROMPT_VERSION = "v1"
MAX_TOKENS = 4000


class VeneerUnavailable(RuntimeError):
    """The veneer could not be produced. The case is still playable without it."""


def load_prompt(version: str = PROMPT_VERSION) -> tuple[str, str]:
    """Return the system and user halves of a versioned prompt file."""
    path = prompts_dir() / "veneer" / f"{version}.md"
    if not path.exists():
        raise VeneerUnavailable(f"prompt {version} not found at {path}")

    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^## (System|User)\s*$", text, flags=re.MULTILINE)
    parts = dict(zip(sections[1::2], sections[2::2], strict=True))
    if "System" not in parts or "User" not in parts:
        raise VeneerUnavailable(f"prompt {version} is missing a System or User section")
    return parts["System"].strip(), parts["User"].strip()


def _render_prompt(case: Case, catalog: Catalog) -> tuple[str, str]:
    system, user = load_prompt()

    public = [f"- {catalog.fact(case, fact)}" for fact in case.facts if fact.scope.public]
    cast = [f"- {suspect.id}: {suspect.name}" for suspect in case.suspects]

    return (
        system.format(language=catalog.label("language_name")),
        user.format(
            victim=case.name_of("victim"),
            public_facts="\n".join(public),
            cast="\n".join(cast),
        ),
    )


def write(case: Case, catalog: Catalog, *, model: StructuredModel) -> CaseVeneer:
    """Write the veneer for an approved case, or raise `VeneerUnavailable`.

    A rejected draft is discarded rather than repaired: a model that broke the
    cast list once will break it differently on a patch, and a half-corrected
    veneer is harder to reason about than none.
    """
    system, user = _render_prompt(case, catalog)

    try:
        draft = model.complete(
            system=system,
            user=user,
            schema=VeneerDraft,
            max_tokens=MAX_TOKENS,
        )
    except ModelRefused as refusal:
        raise VeneerUnavailable(f"the model declined to write this case: {refusal}") from refusal
    except ModelUnavailable as unavailable:
        raise VeneerUnavailable(str(unavailable)) from unavailable

    check(draft, case)

    return CaseVeneer(
        seed=case.seed,
        generator_version=case.generator_version,
        setting=case.setting,
        prompt_version=PROMPT_VERSION,
        locale=catalog.locale,
        model=model.name,
        scene=draft.scene,
        characters=draft.characters,
    )
