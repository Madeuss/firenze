"""Geração e validação de casos."""

from mansao.geracao.gerador import VERSAO_GERADOR, CasoInsoluvel, gerar
from mansao.geracao.solver import Resultado, resolver
from mansao.geracao.validacao import CasoInvalido, validar

__all__ = [
    "VERSAO_GERADOR",
    "CasoInsoluvel",
    "CasoInvalido",
    "Resultado",
    "gerar",
    "resolver",
    "validar",
]
