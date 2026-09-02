"""The only thing the rest of the codebase knows about language models.

One method: given a system prompt, a user prompt and a schema, return an
instance of that schema. Everything a provider offers beyond that — streaming
shapes, tool calling, thinking budgets, cache controls — stays behind the
adapter, because the day the provider changes, whatever leaked through this
interface is what has to be rewritten.

The narrowness is the point, and it is affordable here for a reason specific to
this project: nothing in the deduction path asks a model for anything. The
solver, the validator, the verdict and the scoring are code (RN-023, RN-032).
A model writes prose and proposes a stance, and both arrive as a validated
schema. An application whose business logic depended on tool calling could not
draw this line so tightly.
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

Schema = TypeVar("Schema", bound=BaseModel)


class ModelUnavailable(RuntimeError):
    """No usable model: no provider configured, no credentials, transport failed.

    Callers degrade rather than retry. Prose is a luxury; the mystery is not.
    """


class ModelRefused(RuntimeError):
    """The provider declined to answer.

    Kept separate from unavailability on purpose. A refusal is a fact about the
    request — worth surfacing, worth counting in the evals — and burying it in a
    generic failure would hide it exactly when it matters.
    """


class StructuredModel(Protocol):
    """What a provider must supply. Adapters live in this package, not elsewhere."""

    @property
    def name(self) -> str:
        """Recorded alongside anything the model wrote, so output can be traced
        back to what produced it. A veneer written by a fake must never be
        mistaken for one written by a real model."""
        ...

    def complete(
        self,
        *,
        system: str,
        user: str,
        schema: type[Schema],
        max_tokens: int,
    ) -> Schema:
        """Return an instance of `schema`, or raise `ModelUnavailable` /
        `ModelRefused`. Never returns partially valid data: a response that does
        not fit the schema is a failure, not a value to repair."""
        ...
