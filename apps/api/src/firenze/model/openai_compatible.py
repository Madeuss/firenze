"""Adapter for any endpoint that speaks the OpenAI chat-completions dialect.

Written for Magalu Prosa (ADR-0008), which exposes exactly that. It is not a
Prosa adapter, though: the only thing that ties it to one provider is a base
URL, so pointing it at another compatible endpoint — or at a vLLM of your own —
is configuration rather than code.

## Getting a schema back from a gateway that may not support schemas

The port promises a validated instance or a failure. OpenAI-compatible gateways
vary in how much of that they help with, and Prosa's documentation does not say
which parts it implements. So this tries, in order:

1. `response_format` with a JSON schema — the server enforces the shape;
2. `response_format: json_object` plus the schema in the prompt — the server
   guarantees valid JSON, the shape is the model's problem;
3. a plain request with the schema in the prompt, extracting the first JSON
   object out of whatever comes back.

Whichever works first is remembered for the life of the adapter, so the cost of
not knowing is paid once. All three failing is a failure, never a repair: a
response that does not validate is discarded, because a half-parsed answer that
reaches the game is worse than no answer.
"""

import json
import re
from typing import Any

from pydantic import ValidationError

from firenze.model.port import ModelRefused, ModelUnavailable, Schema

MODES = ("json_schema", "json_object", "prompt")
JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


class OpenAICompatibleModel:
    """Calls a chat-completions endpoint and returns a validated schema."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url
        self._api_key = api_key
        self._client = client
        self._mode: str | None = None

    @property
    def name(self) -> str:
        return self._model

    def _connect(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as missing:  # pragma: no cover - the dependency is declared
            raise ModelUnavailable("the openai sdk is not installed") from missing
        if not self._api_key:
            raise ModelUnavailable("no api key: set FIRENZE_MODEL_API_KEY")
        if not self._base_url:
            raise ModelUnavailable("no base url: set FIRENZE_MODEL_BASE_URL")
        self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def complete(
        self,
        *,
        system: str,
        user: str,
        schema: type[Schema],
        max_tokens: int,
    ) -> Schema:
        client = self._connect()
        attempts = (self._mode,) if self._mode else MODES
        failures: list[str] = []

        for mode in attempts:
            try:
                text = self._ask(client, mode, system, user, schema, max_tokens)
            except ModelRefused:
                raise
            except Exception as failure:  # the gateway rejected this mode, or the call failed
                failures.append(f"{mode}: {failure}")
                continue

            try:
                parsed = schema.model_validate_json(_only_json(text))
            except (ValidationError, ValueError) as invalid:
                failures.append(f"{mode}: response did not fit the schema ({invalid})")
                continue

            self._mode = mode
            return parsed

        raise ModelUnavailable("; ".join(failures) or "no usable response")

    def _ask(
        self,
        client: Any,
        mode: str,
        system: str,
        user: str,
        schema: type[Schema],
        max_tokens: int,
    ) -> str:
        instructions = system
        request: dict[str, Any] = {}

        if mode == "json_schema":
            request["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": _strict(schema.model_json_schema()),
                },
            }
        else:
            instructions = f"{system}\n\n{_schema_instructions(schema)}"
            if mode == "json_object":
                request["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": user},
            ],
            **request,
        )

        choice = response.choices[0]
        if getattr(choice, "finish_reason", None) == "content_filter":
            raise ModelRefused("the provider's content filter stopped the response")
        content = choice.message.content
        if not content:
            raise ValueError("the response carried no content")
        return str(content)


def _schema_instructions(schema: type[Schema]) -> str:
    return (
        "Answer with a single JSON object and nothing else — no prose before it, "
        "no code fence around it. It must validate against this JSON Schema:\n"
        f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
    )


def _only_json(text: str) -> str:
    """Pull the JSON object out of a reply that may be wrapped in prose or fences."""
    stripped = text.strip()
    if stripped.startswith("{"):
        return stripped
    found = JSON_OBJECT.search(stripped)
    if not found:
        raise ValueError(f"no JSON object in the response: {stripped[:120]!r}")
    return found.group(0)


def _strict(schema: dict[str, Any]) -> dict[str, Any]:
    """Tighten a Pydantic schema into the shape strict mode expects.

    Every object closed to extra properties, every property required. Gateways
    that enforce schemas tend to demand this, and Pydantic does not emit it.
    """
    if schema.get("type") == "object" or "properties" in schema:
        schema["additionalProperties"] = False
        if "properties" in schema:
            schema["required"] = list(schema["properties"])
    for key in ("properties", "$defs", "definitions"):
        for value in schema.get(key, {}).values():
            if isinstance(value, dict):
                _strict(value)
    for key in ("items", "prefixItems"):
        value = schema.get(key)
        if isinstance(value, dict):
            _strict(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _strict(item)
    for combinator in ("anyOf", "oneOf", "allOf"):
        for item in schema.get(combinator, []):
            if isinstance(item, dict):
                _strict(item)
    return schema
