"""What the model is allowed to produce.

This schema is the contract with the model, and it is deliberately narrow: the
veneer writes *about* the cast and the house, and has no field in which to
invent a fact, move somebody, or name a culprit. Anything outside these fields
cannot reach the game because there is nowhere to put it (RN-022).
"""

from pydantic import BaseModel, ConfigDict, Field


class CharacterVeneer(BaseModel):
    """One character's surface. No knowledge, no whereabouts, no guilt."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="The character id given in the prompt, unchanged.")
    role_title: str = Field(description="Their place in the house: butler, cook, nephew.")
    appearance: str = Field(description="One sentence. What the player sees.")
    manner: str = Field(description="One sentence. How they speak.")


class CaseVeneer(BaseModel):
    """Prose for one case, in one locale.

    Keyed by seed, generator version, setting, prompt version and locale: the
    five things that decide what the text should be. A cached veneer whose key still matches
    is still correct; when any of them moves, the text is regenerated.
    """

    model_config = ConfigDict(frozen=True)

    seed: int
    generator_version: str
    setting: str
    prompt_version: str
    locale: str
    model: str
    scene: str = Field(description="Two or three sentences setting the house and the night.")
    characters: tuple[CharacterVeneer, ...]

    def for_character(self, character_id: str) -> CharacterVeneer:
        for character in self.characters:
            if character.id == character_id:
                return character
        raise KeyError(character_id)


class VeneerDraft(BaseModel):
    """Exactly what the model returns, before any of it is trusted."""

    model_config = ConfigDict(frozen=True)

    scene: str
    characters: tuple[CharacterVeneer, ...]
