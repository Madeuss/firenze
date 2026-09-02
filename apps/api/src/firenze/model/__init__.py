"""Language models, behind one interface.

`resolve()` is the only place that knows which providers exist. Everything else
depends on the port.
"""

from firenze.model.fake import FakeModel
from firenze.model.openai_compatible import OpenAICompatibleModel
from firenze.model.port import ModelRefused, ModelUnavailable, StructuredModel


def resolve(
    provider: str,
    *,
    model: str = "",
    base_url: str = "",
    api_key: str = "",
) -> StructuredModel:
    """Build the configured model, or raise `ModelUnavailable`.

    `none` is not an error state to be worked around: a build that quietly
    picked a provider would be making the decision on the reader's behalf.
    """
    if provider == "none":
        raise ModelUnavailable(
            "no model provider configured; set FIRENZE_MODEL_PROVIDER to one of: prosa, fake"
        )
    if provider == "fake":
        return FakeModel()
    if provider == "prosa":
        # Prosa speaks the OpenAI dialect (ADR-0008), so the adapter is generic
        # and the provider name is only a label over a base URL.
        if not model:
            raise ModelUnavailable("provider 'prosa' needs FIRENZE_MODEL_NAME set")
        return OpenAICompatibleModel(model=model, base_url=base_url, api_key=api_key)
    raise ModelUnavailable(f"unknown model provider {provider!r}")


__all__ = [
    "FakeModel",
    "ModelRefused",
    "ModelUnavailable",
    "OpenAICompatibleModel",
    "StructuredModel",
    "resolve",
]
