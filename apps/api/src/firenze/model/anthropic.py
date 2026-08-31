"""Anthropic adapter.

One of possibly several. Everything provider-specific lives here — the SDK
import, the client construction, the shape of a structured-output call — so that
choosing a different provider is a new file in this package and a line of
configuration, not a change anywhere in the game.

The provider for this project is not decided yet. This adapter exists because it
was written first and works; it is a reference implementation of the port, not a
commitment.
"""

from typing import Any, cast

from firenze.model.port import ModelRefused, ModelUnavailable, Schema

DEFAULT_MODEL = "claude-haiku-4-5"


class AnthropicModel:
    """Calls the Anthropic Messages API with a schema as the output format."""

    def __init__(self, model: str = DEFAULT_MODEL, client: Any | None = None) -> None:
        self._model = model
        self._client = client

    @property
    def name(self) -> str:
        return self._model

    def _connect(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import anthropic
        except ImportError as missing:  # pragma: no cover - the dependency is declared
            raise ModelUnavailable("the anthropic sdk is not installed") from missing
        try:
            self._client = anthropic.Anthropic()
        except Exception as failure:
            raise ModelUnavailable(f"no usable credentials: {failure}") from failure
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
        try:
            response = client.messages.parse(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
            )
        except Exception as failure:
            raise ModelUnavailable(f"the model call failed: {failure}") from failure

        if getattr(response, "stop_reason", None) == "refusal":
            raise ModelRefused("the model declined to answer")

        parsed = getattr(response, "parsed_output", None)
        if parsed is None:
            raise ModelUnavailable("the model returned nothing that fits the schema")
        return cast("Schema", parsed)
