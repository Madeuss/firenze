"""Reading a model's bookkeeping in the house's vocabulary.

Every case here was seen coming out of a real model. The module exists because
a turn the player paid for was being thrown away over spelling, and these tests
are the record of which spellings — not a list of things a model might do.
"""

from firenze.domain import Stance
from firenze.generation import generate
from firenze.i18n import load
from firenze.interrogation.models import NpcReply
from firenze.interrogation.vocabulary import normalise

CATALOG = load("pt-BR")
CASE = generate(seed=42).case


def _reply(**campos: object) -> NpcReply:
    base: dict[str, object] = {
        "line": "Estive por aí.",
        "stance": Stance.cooperative,
        "lied": False,
    }
    return NpcReply(**{**base, **campos})  # type: ignore[arg-type]


def test_a_blank_room_is_no_claim_not_a_room_called_nothing() -> None:
    assert normalise(_reply(claimed_room=""), CASE, CATALOG).claimed_room is None
    assert normalise(_reply(claimed_room="nenhum"), CASE, CATALOG).claimed_room is None


def test_a_negative_hour_is_no_claim_either() -> None:
    """Strict schema mode requires the field, so "I am not saying" arrives as -1."""
    assert normalise(_reply(claimed_interval=-1), CASE, CATALOG).claimed_interval is None


def test_an_hour_this_night_has_is_left_alone() -> None:
    assert normalise(_reply(claimed_interval=2), CASE, CATALOG).claimed_interval == 2
    assert normalise(_reply(claimed_interval=0), CASE, CATALOG).claimed_interval == 0


def test_a_display_name_is_translated_back_to_the_id() -> None:
    """The character says "a biblioteca" out loud and writes that where the id goes."""
    room = CASE.rooms[0]

    spoken = normalise(_reply(claimed_room=CATALOG.room(room)), CASE, CATALOG)

    assert spoken.claimed_room == room


def test_an_hour_the_night_does_not_reach_is_left_for_the_guard() -> None:
    """Not a sentinel and not a spelling: a claim about a time that does not exist.

    Repairing it would mean choosing an hour nobody named, which is the one
    thing this module will not do (RN-021)."""
    assert normalise(_reply(claimed_interval=99), CASE, CATALOG).claimed_interval == 99


def test_a_room_the_case_does_not_have_is_left_for_the_guard() -> None:
    assert normalise(_reply(claimed_room="ballroom"), CASE, CATALOG).claimed_room == "ballroom"
