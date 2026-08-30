"""Message catalogs.

The domain holds structure; sentences are produced here, per locale, from JSON
under `messages/` (ADR-0005).

Grammar lives in the catalog, not in the data. Portuguese contracts the
preposition with the room's gender ("na adega", "no porão"); English does not
contract at all. So each locale ships its own room entry with the preposition
it needs, and the template just places a slot. A language with cases or a
different word order changes its catalog and touches nothing else.

Two consumers, one catalog: the CLI, and later the prompt builder — a model
asked to play a character has to read the facts in the language it is meant to
answer in. The front end renders with ICU from its own copy, which is why
templates here stay simple enough to translate mechanically.
"""

import json
from functools import cache
from pathlib import Path
from typing import Any

from firenze.domain import Case, Fact

MESSAGES_DIR = Path(__file__).parent / "messages"
DEFAULT_LOCALE = "pt-BR"


class MissingMessage(KeyError):
    """A key the generator produced has no text in this locale."""


class UnknownLocale(ValueError):
    """No catalog shipped for this locale."""


def available_locales() -> tuple[str, ...]:
    return tuple(sorted(p.stem for p in MESSAGES_DIR.glob("*.json")))


@cache
def load(locale: str = DEFAULT_LOCALE) -> "Catalog":
    path = MESSAGES_DIR / f"{locale}.json"
    if not path.exists():
        raise UnknownLocale(f"{locale!r}; available: {', '.join(available_locales())}")
    return Catalog(locale=locale, data=json.loads(path.read_text(encoding="utf-8")))


class Catalog:
    """Renders domain structure into one locale's prose."""

    def __init__(self, locale: str, data: dict[str, Any]) -> None:
        self.locale = locale
        self._data = data

    def _section(self, section: str, key: str) -> Any:
        try:
            return self._data[section][key]
        except KeyError as missing:
            raise MissingMessage(f"{self.locale}: {section}.{key}") from missing

    def room(self, room_id: str) -> str:
        entry: dict[str, str] = self._section("rooms", room_id)
        return entry["name"]

    def room_phrase(self, room_id: str) -> str:
        """The room with the preposition its language requires."""
        entry: dict[str, str] = self._section("rooms", room_id)
        return f"{entry['preposition']} {entry['name']}"

    def secret(self, key: str) -> str:
        return str(self._section("secrets", key))

    def means(self, key: str) -> str:
        return str(self._section("means", key))

    def motive(self, key: str) -> str:
        return str(self._section("motives", key))

    def label(self, key: str) -> str:
        return str(self._section("labels", key))

    def time(self, minutes: int) -> str:
        hour, minute = divmod(minutes, 60)
        suffix = self._data["clock"].get("am" if hour < 12 else "pm", "")
        display_hour = hour if self._data["clock"]["cycle"] == 24 else (hour % 12) or 12
        pattern: str = self._data["clock"]["pattern"]
        return pattern.format(hour=display_hour, minute=f"{minute:02d}", suffix=suffix).strip()

    def fact(self, case: Case, fact: Fact) -> str:
        template: str = self._section("facts", fact.kind.value)
        slots = {
            "victim": next((c.name for c in case.cast if c.id == "victim"), ""),
            "character": case.name_of(fact.character) if fact.character else "",
            "witness": case.name_of(fact.witness) if fact.witness else "",
            "room": self.room_phrase(fact.room) if fact.room else "",
            "time": self.time(case.minutes_at(fact.interval)) if fact.interval is not None else "",
            "secret": self.secret(fact.secret_key) if fact.secret_key else "",
        }
        return template.format(**slots)
