"""Language models, behind one interface.

`resolve()` is the only place that knows which providers exist. Everything else
depends on the port.
"""

from firenze.model.anthropic import AnthropicModel
from firenze.model.fake import FakeModel
from firenze.model.port import ModelRefused, ModelUnavailable, StructuredModel


def resolve(provider: str, model: str) -> StructuredModel:
    """Build the configured model, or raise `ModelUnavailable`.

    `none` is the default and is not an error state to be worked around: the
    provider for this project is not chosen yet, and a build that quietly picked
    one would be making the decision on the reader's behalf.
    """
    if provider == "none":
        raise ModelUnavailable(
            "no model provider configured; set FIRENZE_MODEL_PROVIDER to one of: anthropic, fake"
        )
    if provider == "fake":
        return FakeModel()
    if provider == "anthropic":
        if not model:
            raise ModelUnavailable("provider 'anthropic' needs FIRENZE_MODEL_NAME set")
        return AnthropicModel(model=model)
    raise ModelUnavailable(f"unknown model provider {provider!r}")


__all__ = [
    "AnthropicModel",
    "FakeModel",
    "ModelRefused",
    "ModelUnavailable",
    "StructuredModel",
    "resolve",
]
