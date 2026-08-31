"""Port and adapter tests.

The contract is one method, so these are short. What they protect is the
boundary: if an adapter starts leaking provider vocabulary through the port, or
the fake starts looking like a real model, the next provider change stops being
a new file and becomes a refactor.
"""

from typing import Any

import pytest
from pydantic import BaseModel

from firenze.domain import Role
from firenze.model import AnthropicModel, FakeModel, ModelRefused, ModelUnavailable, resolve
from firenze.model.fake import MARKER


class Nested(BaseModel):
    label: str


class Answer(BaseModel):
    line: str
    stance: Role
    lied: bool
    turns: int
    parts: tuple[Nested, ...]


def test_the_fake_fills_any_schema() -> None:
    answer = FakeModel().complete(system="s", user="u", schema=Answer, max_tokens=100)

    assert MARKER in answer.line
    assert answer.stance is Role.victim  # first member, deterministically
    assert answer.lied is False
    assert answer.turns == 0
    assert len(answer.parts) == 1, "collections get one element, never zero"
    assert MARKER in answer.parts[0].label


def test_the_fake_is_deterministic() -> None:
    """A fake that varied would make a failing test look flaky."""
    first = FakeModel().complete(system="s", user="u", schema=Answer, max_tokens=100)
    second = FakeModel().complete(system="s", user="u", schema=Answer, max_tokens=100)

    assert first == second


def test_the_fake_answers_differently_to_a_different_prompt() -> None:
    first = FakeModel().complete(system="s", user="one", schema=Answer, max_tokens=100)
    second = FakeModel().complete(system="s", user="two", schema=Answer, max_tokens=100)

    assert first.line != second.line


def test_the_fake_never_claims_to_be_a_real_model() -> None:
    """Its name is recorded on everything it writes, so output stays traceable."""
    assert FakeModel().name == "fake"


def test_the_fake_can_be_asked_to_refuse() -> None:
    with pytest.raises(ModelRefused):
        FakeModel(refuse=True).complete(system="s", user="u", schema=Answer, max_tokens=10)


def test_no_provider_configured_is_an_explicit_failure() -> None:
    """Not a silent default. The provider for this project is not chosen yet."""
    with pytest.raises(ModelUnavailable, match="no model provider configured"):
        resolve("none", "whatever")


def test_an_unknown_provider_says_so() -> None:
    with pytest.raises(ModelUnavailable, match="unknown model provider"):
        resolve("mistral-via-carrier-pigeon", "x")


@pytest.mark.parametrize(
    ("provider", "expected"),
    [("fake", "fake"), ("anthropic", "claude-haiku-4-5")],
)
def test_resolve_builds_what_it_was_asked_for(provider: str, expected: str) -> None:
    assert resolve(provider, "claude-haiku-4-5").name == expected


def test_the_anthropic_adapter_translates_a_refusal() -> None:
    class Refusing:
        def parse(self, **kwargs: Any) -> Any:
            return type("R", (), {"stop_reason": "refusal", "parsed_output": None})

    model = AnthropicModel(client=type("C", (), {"messages": Refusing()})())

    with pytest.raises(ModelRefused):
        model.complete(system="s", user="u", schema=Answer, max_tokens=10)


def test_the_anthropic_adapter_translates_a_transport_failure() -> None:
    """A provider exception must never escape the adapter as itself."""

    class Exploding:
        def parse(self, **kwargs: Any) -> Any:
            raise ConnectionError("no route to host")

    model = AnthropicModel(client=type("C", (), {"messages": Exploding()})())

    with pytest.raises(ModelUnavailable, match="model call failed"):
        model.complete(system="s", user="u", schema=Answer, max_tokens=10)


def test_the_anthropic_adapter_rejects_an_unparseable_response() -> None:
    class Empty:
        def parse(self, **kwargs: Any) -> Any:
            return type("R", (), {"stop_reason": "end_turn", "parsed_output": None})

    model = AnthropicModel(client=type("C", (), {"messages": Empty()})())

    with pytest.raises(ModelUnavailable, match="nothing that fits the schema"):
        model.complete(system="s", user="u", schema=Answer, max_tokens=10)


def test_no_module_outside_the_port_imports_a_provider_sdk() -> None:
    """The boundary this ADR draws has to survive people who have not read it.

    Provider vocabulary spreading module by module is the failure ADR-0007
    exists to prevent, and it never announces itself — it looks like one
    reasonable import at a time.
    """
    import pathlib
    import re

    source = pathlib.Path(__file__).resolve().parents[1] / "src" / "firenze"
    # Naming a provider as a valid config value is not coupling; importing its
    # SDK is. So this looks for the import, not for the word.
    sdks = "anthropic|openai|google|mistralai|cohere|ollama"
    sdk_import = re.compile(rf"^\s*(?:import|from)\s+({sdks})\b", re.MULTILINE)

    offenders = [
        path.relative_to(source).as_posix()
        for path in source.rglob("*.py")
        if path.parent.name != "model" and sdk_import.search(path.read_text(encoding="utf-8"))
    ]

    assert not offenders, f"provider SDK imported outside firenze.model: {offenders}"
