"""Case generation, validation and the deducibility gate."""

from mansao.generation.generator import GENERATOR_VERSION, UnsolvableCase, generate
from mansao.generation.solver import SolverResult, solve
from mansao.generation.validation import InvalidCase, validate

__all__ = [
    "GENERATOR_VERSION",
    "InvalidCase",
    "SolverResult",
    "UnsolvableCase",
    "generate",
    "solve",
    "validate",
]
