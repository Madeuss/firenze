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
from firenze.model import (
    FakeModel,
    ModelRefused,
    ModelUnavailable,
    OpenAICompatibleModel,
    resolve,
)
from firenze.model.fake import MARKER
from firenze.model.openai_compatible import _strict


class Nested(BaseModel):
    label: str


class Answer(BaseModel):
    line: str
    stance: Role
    lied: bool
    turns: int
    parts: tuple[Nested, ...]
    cited: str | None = None


def test_the_fake_fills_any_schema() -> None:
    answer = FakeModel().complete(system="s", user="u", schema=Answer, max_tokens=100)

    assert MARKER in answer.line
    assert answer.stance is Role.victim  # first member, deterministically
    assert answer.lied is False
    assert answer.turns == 0
    assert len(answer.parts) == 1, "collections get one element, never zero"
    assert MARKER in answer.parts[0].label
    assert answer.cited is None, "optional fields are omitted, never invented"


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
        resolve("none")


def test_an_unknown_provider_says_so() -> None:
    with pytest.raises(ModelUnavailable, match="unknown model provider"):
        resolve("mistral-via-carrier-pigeon")


def test_resolve_builds_what_it_was_asked_for() -> None:
    assert resolve("fake").name == "fake"
    assert resolve("prosa", model="qwen-whatever", base_url="https://x").name == "qwen-whatever"


def test_prosa_without_a_model_name_fails_loudly() -> None:
    with pytest.raises(ModelUnavailable, match="needs FIRENZE_MODEL_NAME"):
        resolve("prosa")


class Reply:
    """The slice of an OpenAI-shaped response this adapter reads."""

    def __init__(self, content: str | None, finish_reason: str = "stop") -> None:
        message = type("M", (), {"content": content})
        choice = type("C", (), {"message": message, "finish_reason": finish_reason})
        self.choices = [choice]


class Gateway:
    """A chat-completions endpoint that supports only the modes it was told to."""

    PADRAO = (
        '{"line": "ok", "stance": "victim", "lied": false, "turns": 1, "parts": [{"label": "x"}]}'
    )

    def __init__(self, supports: set[str], reply: str = PADRAO) -> None:
        self._supports = supports
        self._reply = reply
        self.modes_tried: list[str] = []

    @property
    def chat(self) -> "Gateway":
        return self

    @property
    def completions(self) -> "Gateway":
        return self

    def create(self, **kwargs: Any) -> Reply:
        fmt = kwargs.get("response_format") or {}
        mode = fmt.get("type", "prompt")
        self.modes_tried.append(mode)
        if mode not in self._supports:
            raise ValueError(f"unsupported response_format: {mode}")
        return Reply(self._reply)


def _model(gateway: Gateway) -> OpenAICompatibleModel:
    return OpenAICompatibleModel(
        model="qwen-whatever", base_url="https://x", api_key="k", client=gateway
    )


def test_it_uses_a_server_enforced_schema_when_the_gateway_supports_one() -> None:
    gateway = Gateway(supports={"json_schema"})

    answer = _model(gateway).complete(system="s", user="u", schema=Answer, max_tokens=10)

    assert gateway.modes_tried == ["json_schema"]
    assert answer.line == "ok"


def test_it_falls_back_to_json_mode_when_schemas_are_rejected() -> None:
    """Prosa's documentation does not say which modes it implements."""
    gateway = Gateway(supports={"json_object"})

    answer = _model(gateway).complete(system="s", user="u", schema=Answer, max_tokens=10)

    assert gateway.modes_tried == ["json_schema", "json_object"]
    assert answer.line == "ok"


def test_it_falls_back_to_asking_in_the_prompt() -> None:
    gateway = Gateway(supports={"prompt"})

    answer = _model(gateway).complete(system="s", user="u", schema=Answer, max_tokens=10)

    assert gateway.modes_tried == ["json_schema", "json_object", "prompt"]
    assert answer.line == "ok"


def test_the_working_mode_is_remembered() -> None:
    """The cost of not knowing what the gateway supports is paid once."""
    gateway = Gateway(supports={"prompt"})
    model = _model(gateway)

    model.complete(system="s", user="u", schema=Answer, max_tokens=10)
    model.complete(system="s", user="u", schema=Answer, max_tokens=10)

    assert gateway.modes_tried == ["json_schema", "json_object", "prompt", "prompt"]


def test_json_wrapped_in_prose_is_still_read() -> None:
    """A model told to answer in JSON often says "here you go:" first."""
    corpo = (
        '{"line": "ok", "stance": "victim", "lied": false, "turns": 1, "parts": [{"label": "x"}]}'
    )
    envelope = f"""Claro! ```json
{corpo}
``` espero ter ajudado"""
    gateway = Gateway(supports={"prompt"}, reply=envelope)

    answer = _model(gateway).complete(system="s", user="u", schema=Answer, max_tokens=10)

    assert answer.line == "ok"


def test_a_response_that_does_not_fit_the_schema_is_discarded() -> None:
    """Never repaired. A half-parsed answer reaching the game is worse than none."""
    gateway = Gateway(supports={"json_schema"}, reply='{"line": "ok"}')

    with pytest.raises(ModelUnavailable, match="did not fit the schema"):
        _model(gateway).complete(system="s", user="u", schema=Answer, max_tokens=10)


def test_a_content_filter_is_a_refusal_not_a_failure() -> None:
    class Filtered(Gateway):
        def create(self, **kwargs: Any) -> Reply:
            return Reply(None, finish_reason="content_filter")

    with pytest.raises(ModelRefused):
        _model(Filtered(supports={"json_schema"})).complete(
            system="s", user="u", schema=Answer, max_tokens=10
        )


def test_strict_mode_closes_every_object_in_the_schema() -> None:
    """Gateways that enforce schemas demand this; Pydantic does not emit it."""
    tightened = _strict(Answer.model_json_schema())

    assert tightened["additionalProperties"] is False
    assert set(tightened["required"]) == set(tightened["properties"])
    nested = tightened["$defs"]["Nested"]
    assert nested["additionalProperties"] is False


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
