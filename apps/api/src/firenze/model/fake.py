"""A model that needs no network, no key and no money.

It exists so the game can be built and played before a provider is chosen, and
so a front end can be developed against a running backend without anyone paying
per keystroke. It fills a schema with deterministic, obviously-synthetic text.

Two rules keep it honest:

- **It never pretends to be a real model.** `name` says `fake`, and that string
  is recorded on everything it writes. A veneer produced here is traceable as
  produced here.
- **It is deterministic.** Same prompt, same output. A fake that varied would
  make a failing test look flaky, which is worse than no fake at all.

It is not a mock of any provider and does not imitate one. It satisfies the
port, nothing more — and note what that means: it produces output that fits a
**schema**, never output that fits a **case**. Domain validation will reject a
fake veneer, because the cast it invents is not the cast of any real mystery,
and that rejection is correct rather than a shortcoming. The fake earns its keep
on pipelines whose correctness does not depend on the content: schema
validation, stance transitions, output filters, turn accounting.
"""

import hashlib
from enum import Enum
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from firenze.model.port import ModelRefused, Schema

MARKER = "[fake]"


class FakeModel:
    """Fills any schema with placeholder text derived from the prompt."""

    def __init__(self, *, refuse: bool = False) -> None:
        self._refuse = refuse

    @property
    def name(self) -> str:
        return "fake"

    def complete(
        self,
        *,
        system: str,
        user: str,
        schema: type[Schema],
        max_tokens: int,
    ) -> Schema:
        if self._refuse:
            raise ModelRefused("the fake model was asked to refuse")

        seed = hashlib.blake2s(f"{system}{user}".encode(), digest_size=4).hexdigest()
        return _fill(schema, seed=seed, path="")


def _fill(schema: type[Schema], *, seed: str, path: str) -> Schema:
    values: dict[str, Any] = {}
    for name, field in schema.model_fields.items():
        values[name] = _value_for(field.annotation, seed=seed, path=f"{path}.{name}")
    return schema(**values)


def _value_for(annotation: Any, *, seed: str, path: str) -> Any:
    if annotation is str:
        return f"{MARKER} {path.lstrip('.')} {seed}"
    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if annotation is bool:
        return False

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (tuple, list, set, frozenset):
        # One element, not zero: an empty collection would pass a schema and
        # then fail a validation rule for a reason unrelated to the fake.
        inner = args[0] if args else str
        item = _value_for(inner, seed=seed, path=f"{path}[0]")
        return origin([item]) if origin is not tuple else (item,)

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        # The first member, deterministically. A stance machine fed a random
        # enum would fail for a reason that has nothing to do with the code.
        return next(iter(annotation))

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _fill(annotation, seed=seed, path=path)

    if args:  # Optional[X], X | None, Literal[...]
        for candidate in args:
            if candidate is not type(None):
                return _value_for(candidate, seed=seed, path=path)

    return f"{MARKER} {path.lstrip('.')}"
