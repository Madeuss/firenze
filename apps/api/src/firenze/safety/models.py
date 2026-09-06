"""What the classifier returns.

`reason` is not used by any decision — it exists so that a wrong label can be
argued with when the adversarial suite disagrees with the classifier. A number
in an eval report with no explanation is a number nobody can act on.
"""

from pydantic import BaseModel, ConfigDict, Field

from firenze.domain import Intent


class Classification(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent: Intent = Field(description="What the player is doing.")
    reason: str = Field(default="", description="One short sentence, for the eval report.")
