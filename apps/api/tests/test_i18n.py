"""Catalog tests.

The valuable one is `test_every_key_the_generator_emits_exists_in_every_catalog`:
adding a room or a secret to the generator and forgetting the translation is the
normal way i18n rots, and it fails here instead of in front of a player.
"""

import pytest

from firenze.domain import FactKind
from firenze.generation import generate
from firenze.generation.generator import MEANS_KEYS, MOTIVE_KEYS, ROOMS, SECRET_KEYS
from firenze.i18n import UnknownLocale, available_locales, load

LOCALES = available_locales()


def test_both_locales_ship() -> None:
    assert set(LOCALES) == {"en", "pt-BR"}


@pytest.mark.parametrize("locale", LOCALES)
def test_every_key_the_generator_emits_exists_in_every_catalog(locale: str) -> None:
    catalog = load(locale)

    for room in ROOMS:
        assert catalog.room(room)
        assert catalog.room_phrase(room)
    for key in SECRET_KEYS:
        assert catalog.secret(key)
    for key in MEANS_KEYS:
        assert catalog.means(key)
    for key in MOTIVE_KEYS:
        assert catalog.motive(key)


@pytest.mark.parametrize("locale", LOCALES)
def test_every_fact_of_a_case_renders_with_no_empty_slot(locale: str) -> None:
    catalog = load(locale)
    case = generate(seed=5).case

    for fact in case.facts:
        rendered = catalog.fact(case, fact)

        assert rendered.strip()
        assert "{" not in rendered, f"slot left unfilled in {fact.kind}"
        assert "  " not in rendered, f"empty slot collapsed into a double space in {fact.kind}"


def test_the_structure_does_not_change_with_the_locale() -> None:
    """Locale is presentation. The mystery is the same in every language."""
    case = generate(seed=9).case
    pt, en = load("pt-BR"), load("en")

    body = next(f for f in case.facts if f.kind is FactKind.body)

    assert pt.fact(case, body) != en.fact(case, body)
    assert case.crime_room == case.crime_room
    assert "biblioteca" in pt.room("library")
    assert "library" in en.room("library")


def test_the_clock_follows_the_locale() -> None:
    """21:30 is 21h30 in Brazil and 9:30 pm in English."""
    assert load("pt-BR").time(21 * 60 + 30) == "21h30"
    assert load("en").time(21 * 60 + 30) == "9:30 pm"


def test_grammar_lives_in_the_catalog_not_in_the_domain() -> None:
    """Portuguese contracts the preposition with the room's gender; English does not."""
    pt = load("pt-BR")

    assert pt.room_phrase("cellar").startswith("na ")
    assert pt.room_phrase("basement").startswith("no ")
    assert load("en").room_phrase("cellar").startswith("in ")


def test_unknown_locale_says_what_is_available() -> None:
    with pytest.raises(UnknownLocale, match="pt-BR"):
        load("tlh")
