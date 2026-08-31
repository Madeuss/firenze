"""Veneer tests.

Every one of these runs without an API key. The model is replaced by a stub
that returns whatever the test needs it to return — which is the point: the
interesting cases are the drafts a real model might plausibly produce and that
must not reach a player, and waiting for a real model to produce one of them by
chance is not a test strategy.
"""

from typing import Any

import pytest

from firenze.domain import Case
from firenze.generation import generate
from firenze.i18n import load
from firenze.model import ModelRefused, ModelUnavailable
from firenze.veneer import (
    CharacterVeneer,
    VeneerDraft,
    VeneerRejected,
    VeneerUnavailable,
    check,
    load_prompt,
    write,
)
from firenze.veneer.writer import _render_prompt


class ScriptedModel:
    """A model that returns exactly what a test needs it to return."""

    def __init__(self, draft: VeneerDraft | None = None, failure: Exception | None = None) -> None:
        self._draft = draft
        self._failure = failure
        self.calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "scripted"

    def complete(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._failure is not None:
            raise self._failure
        return self._draft


@pytest.fixture(scope="module")
def case() -> Case:
    return generate(seed=42).case


def _good_draft(case: Case) -> VeneerDraft:
    return VeneerDraft(
        scene="A chuva não parou a noite toda.",
        characters=tuple(
            CharacterVeneer(
                id=suspect.id,
                role_title="mordomo",
                appearance="Alto, de luvas brancas.",
                manner="Fala pouco e olha para o chão.",
            )
            for suspect in case.suspects
        ),
    )


def test_the_prompt_only_ever_shows_public_facts(case: Case) -> None:
    """The veneer cannot leak a restricted fact it was never given. (RN-010)"""
    _, user = _render_prompt(case, load("pt-BR"))

    restricted = [f for f in case.facts if not f.scope.public]
    assert restricted, "this case should have restricted facts, or the test proves nothing"
    for fact in restricted:
        assert fact.canary not in user
        if fact.secret_key:
            assert fact.secret_key not in user


def test_nothing_in_the_prompt_singles_out_the_culprit(case: Case) -> None:
    """`write` takes `Case`, so a culprit has no parameter to arrive through.

    The stronger property is that the prompt cannot betray one either: every
    suspect appears exactly once, in the cast list, and nothing else in the text
    distinguishes them. A model that cannot tell them apart cannot write the
    guilty one as guiltier.
    """
    full = generate(seed=42)
    _, user = _render_prompt(case, load("pt-BR"))

    assert full.solution.means_key not in user
    assert full.solution.motive_key not in user
    for suspect in case.suspects:
        assert user.count(suspect.name) == 1, f"{suspect.name} appears more than in the cast"
        assert user.count(suspect.id) == 1


def test_a_good_draft_becomes_a_veneer(case: Case) -> None:
    model = ScriptedModel(_good_draft(case))

    veneer = write(case, load("pt-BR"), model=model)

    assert veneer.seed == case.seed
    assert veneer.locale == "pt-BR"
    assert veneer.prompt_version == "v1"
    assert veneer.model == "scripted", "output records what wrote it"
    # Prose is written for one setting. Carrying it keeps a cached veneer from
    # being reused for a different world that happened to share a seed.
    assert veneer.setting == case.setting
    assert {c.id for c in veneer.characters} == {s.id for s in case.suspects}
    assert veneer.for_character("sus-1").role_title == "mordomo"


def test_an_invented_character_is_rejected(case: Case) -> None:
    draft = _good_draft(case)
    tampered = draft.model_copy(
        update={
            "characters": (
                *draft.characters,
                CharacterVeneer(id="sus-99", role_title="jardineiro", appearance="x", manner="y"),
            )
        }
    )

    with pytest.raises(VeneerRejected) as raised:
        check(tampered, case)

    assert raised.value.check == "cast"


def test_a_dropped_character_is_rejected(case: Case) -> None:
    draft = _good_draft(case)
    tampered = draft.model_copy(update={"characters": draft.characters[:-1]})

    with pytest.raises(VeneerRejected, match="missing"):
        check(tampered, case)


def test_a_leaked_canary_is_rejected(case: Case) -> None:
    """RN-012. A canary here means context assembly upstream is broken."""
    secret = next(f for f in case.facts if not f.scope.public and f.canary)
    draft = _good_draft(case)
    tampered = draft.model_copy(update={"scene": f"A casa dormia. {secret.canary}"})

    with pytest.raises(VeneerRejected) as raised:
        check(tampered, case)

    assert raised.value.check == "canary"
    assert secret.canary in raised.value.detail


def test_a_swapped_name_is_rejected(case: Case) -> None:
    """Describing one suspect as another contradicts every alibi in the case."""
    first, second = case.suspects[0], case.suspects[1]
    draft = _good_draft(case)
    tampered = draft.model_copy(
        update={
            "characters": (
                draft.characters[0].model_copy(
                    update={"appearance": f"Parece muito com {second.name}."}
                ),
                *draft.characters[1:],
            )
        }
    )

    with pytest.raises(VeneerRejected, match="names"):
        check(tampered, case)

    assert first.id


def test_a_blank_field_is_rejected(case: Case) -> None:
    draft = _good_draft(case)
    tampered = draft.model_copy(
        update={
            "characters": (
                draft.characters[0].model_copy(update={"manner": "   "}),
                *draft.characters[1:],
            )
        }
    )

    with pytest.raises(VeneerRejected, match="empty"):
        check(tampered, case)


def test_a_refusal_is_not_a_crash(case: Case) -> None:
    model = ScriptedModel(failure=ModelRefused("policy"))

    with pytest.raises(VeneerUnavailable, match="declined"):
        write(case, load("pt-BR"), model=model)


def test_an_unavailable_model_is_not_a_crash(case: Case) -> None:
    model = ScriptedModel(failure=ModelUnavailable("no route to host"))

    with pytest.raises(VeneerUnavailable, match="no route"):
        write(case, load("pt-BR"), model=model)


def test_a_fake_veneer_is_rejected_by_domain_validation(case: Case) -> None:
    """The fake fits the schema and not the case, and that is the right outcome.

    It invents a cast that belongs to no mystery, so `check` refuses it. Worth
    asserting: it is the line between "this pipeline runs offline" and "this
    pipeline produces something a player could be shown".
    """
    from firenze.model import FakeModel

    with pytest.raises(VeneerRejected, match="cast"):
        write(case, load("pt-BR"), model=FakeModel())


def test_the_prompt_file_is_the_source_of_truth() -> None:
    """Prompts live in `prompts/`, versioned, never as a string literal."""
    system, user = load_prompt("v1")

    assert "{language}" in system
    assert "{public_facts}" in user
    assert "Never state or imply who killed the victim" in system


def test_an_unknown_prompt_version_fails_loudly() -> None:
    with pytest.raises(VeneerUnavailable, match="not found"):
        load_prompt("v999")


@pytest.mark.parametrize("locale", ["pt-BR", "en"])
def test_the_prompt_asks_for_the_locale_language(case: Case, locale: str) -> None:
    catalog = load(locale)
    system, _ = _render_prompt(case, catalog)

    assert catalog.label("language_name") in system
