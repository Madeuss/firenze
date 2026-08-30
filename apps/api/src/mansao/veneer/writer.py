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

The prompt lives in `prompts/veneer/`, versioned, never as a string literal.
"""

import os
import re
from pathlib import Path
from typing import Any, Protocol, cast

from mansao.domain import Case
from mansao.i18n import Catalog
from mansao.veneer.models import CaseVeneer, VeneerDraft
from mansao.veneer.validation import check

PROMPT_VERSION = "v1"
# Haiku: the veneer is short, structured, and its failure modes are caught by
# validation rather than by model quality. ~US$ 0.0025 per case against a
# R$ 0,50 per-match budget that phase 2 will spend on six NPCs and a turn each.
DEFAULT_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 4000


class VeneerUnavailable(RuntimeError):
    """The veneer could not be produced. The case is still playable without it."""


class _Parseable(Protocol):
    """The slice of the SDK this module uses, so tests can supply their own."""

    def parse(self, **kwargs: Any) -> Any: ...


class _Client(Protocol):
    @property
    def messages(self) -> _Parseable: ...


def prompts_dir() -> Path:
    """Repository `prompts/`, or wherever `MANSAO_PROMPTS_DIR` points."""
    override = os.environ.get("MANSAO_PROMPTS_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[5] / "prompts"


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


def write(
    case: Case,
    catalog: Catalog,
    *,
    client: _Client | None = None,
    model: str = DEFAULT_MODEL,
) -> CaseVeneer:
    """Write the veneer for an approved case, or raise `VeneerUnavailable`.

    A rejected draft is discarded rather than repaired: a model that broke the
    cast list once will break it differently on a patch, and a half-corrected
    veneer is harder to reason about than none.
    """
    if client is None:
        client = _default_client()

    system, user = _render_prompt(case, catalog)

    try:
        response = client.messages.parse(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=VeneerDraft,
        )
    except Exception as failure:
        raise VeneerUnavailable(f"the model call failed: {failure}") from failure

    if getattr(response, "stop_reason", None) == "refusal":
        raise VeneerUnavailable("the model declined to write this case")

    draft = response.parsed_output
    if draft is None:
        raise VeneerUnavailable("the model returned no parseable draft")

    check(draft, case)

    return CaseVeneer(
        seed=case.seed,
        generator_version=case.generator_version,
        prompt_version=PROMPT_VERSION,
        locale=catalog.locale,
        model=model,
        scene=draft.scene,
        characters=draft.characters,
    )


def _default_client() -> _Client:
    try:
        import anthropic
    except ImportError as missing:  # pragma: no cover - the dependency is declared
        raise VeneerUnavailable("the anthropic sdk is not installed") from missing

    try:
        # The SDK's own `parse` signature is narrower than the slice we use;
        # the cast is the one place where that difference is acknowledged.
        return cast("_Client", anthropic.Anthropic())
    except Exception as failure:
        raise VeneerUnavailable(f"no usable credentials: {failure}") from failure
