"""Language models, behind one interface.

`resolve()` is the only place that knows which providers exist. Everything else
depends on the port.
"""

from firenze.model.fake import FakeModel
from firenze.model.openai_compatible import OpenAICompatibleModel
from firenze.model.port import ModelGarbled, ModelRefused, ModelUnavailable, StructuredModel


def resolve(
    provider: str,
    *,
    model: str = "",
    base_url: str = "",
    api_key: str = "",
    seed: int | None = None,
) -> StructuredModel:
    """Build the configured model, or raise `ModelUnavailable`.

    `none` is not an error state to be worked around: a build that quietly
    picked a provider would be making the decision on the reader's behalf.

    `seed` asks the provider to sample with it. Callers that want a discount
    leave it alone; callers that need independent samples of the same prompt —
    the eval suite — set a different one per run, because the gateway serves an
    identical request from cache.
    """
    if provider == "none":
        raise ModelUnavailable(
            "no model provider configured; set FIRENZE_MODEL_PROVIDER to one of: aihub, fake"
        )
    if provider == "fake":
        return FakeModel()
    if provider == "aihub":
        # AI Hub speaks the OpenAI dialect (ADR-0008), so the adapter is generic
        # and the provider name is only a label over a base URL. The product was
        # called Prosa when that ADR was written; Magalu renamed it.
        if not model:
            raise ModelUnavailable("provider 'aihub' needs FIRENZE_MODEL_NAME set")
        return OpenAICompatibleModel(model=model, base_url=base_url, api_key=api_key, seed=seed)
    raise ModelUnavailable(f"unknown model provider {provider!r}")


__all__ = [
    "FakeModel",
    "ModelGarbled",
    "ModelRefused",
    "ModelUnavailable",
    "OpenAICompatibleModel",
    "StructuredModel",
    "resolve",
]
