"""The stance machine. Deterministic, and the model does not get a vote.

RN-023: a model may *suggest* a stance; this decides whether the suggestion is a
legal move and keeps the current stance when it is not. The machine is the one
in `docs/01-dominio.md` §6, and the reason it is code rather than instruction is
that a stance drives scoring and pacing — a model that could set it at will
could talk its way out of pressure.

`broken` is absorbing and unreachable from any suggestion: a suspect breaks when
confronted with evidence that invalidates what they said, which is a game event
computed from a confrontation (phase 4), not a mood a model may adopt because
the question felt intense.
"""

from firenze.domain import Stance

MOVES: dict[Stance, frozenset[Stance]] = {
    Stance.cooperative: frozenset({Stance.cooperative, Stance.evasive}),
    Stance.evasive: frozenset({Stance.evasive, Stance.cooperative, Stance.hostile}),
    Stance.hostile: frozenset({Stance.hostile, Stance.evasive}),
    Stance.broken: frozenset({Stance.broken}),
}


def is_legal(current: Stance, suggested: Stance) -> bool:
    return suggested in MOVES[current]


def settle(current: Stance, suggested: Stance) -> Stance:
    """The stance this turn ends on.

    Never raises. An illegal suggestion is not an error to surface to the
    player — it is a model being a model, and the turn still has to produce an
    answer. It is worth counting in the evals, which is why `is_legal` is
    public.
    """
    return suggested if is_legal(current, suggested) else current
