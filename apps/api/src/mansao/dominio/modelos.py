"""Entidades do caso.

`Solucao` é entidade separada de `Caso` de propósito: o isolamento vira
assinatura de função, não disciplina de quem escreve o prompt. Nenhuma rotina
que monta contexto de NPC recebe `CasoCompleto` — só `Caso`. (RN-011)
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Papel(StrEnum):
    vitima = "vitima"
    suspeito = "suspeito"


class TipoFato(StrEnum):
    corpo = "corpo"
    """Onde e quando o corpo foi encontrado. Sempre público."""
    presenca = "presenca"
    """Quem estava em qual cômodo, em qual intervalo, atestado por quem."""
    objeto = "objeto"
    """Prova física que amarra alguém a um lugar e hora."""
    segredo = "segredo"
    """O segredo pessoal de um suspeito. Motivo para mentir sem ser culpado."""


class Personagem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    nome: str
    papel: Papel


class Escopo(BaseModel):
    """Quem está autorizado a conhecer um fato. (RN-010)"""

    model_config = ConfigDict(frozen=True)

    publico: bool = False
    personagens: frozenset[str] = frozenset()

    def inclui(self, personagem: str) -> bool:
        return self.publico or personagem in self.personagens


class Fato(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    tipo: TipoFato
    descricao: str
    escopo: Escopo

    personagem: str | None = None
    """De quem o fato fala."""
    comodo: str | None = None
    intervalo: int | None = None
    testemunha: str | None = None
    """Quem pode atestar o fato além do próprio personagem."""
    expoe_segredo_de: str | None = None
    """Se preenchido, esse suspeito mente sobre este fato. (RN-020)"""
    incrimina: str | None = None
    """Se preenchido, o fato liga esse suspeito ao crime."""
    canary: str | None = None
    """Token único em fato não-público. Canary na saída é falha crítica. (RN-012)"""


class Caso(BaseModel):
    """O que pode circular pelo sistema. Não contém a solução."""

    model_config = ConfigDict(frozen=True)

    semente: int
    versao_gerador: str
    comodos: tuple[str, ...]
    intervalos: tuple[str, ...]
    elenco: tuple[Personagem, ...]
    fatos: tuple[Fato, ...]
    comodo_crime: str
    intervalo_crime: int

    @property
    def suspeitos(self) -> tuple[Personagem, ...]:
        return tuple(p for p in self.elenco if p.papel is Papel.suspeito)

    def dossie(self, personagem: str) -> tuple[Fato, ...]:
        """Projeção dos fatos visíveis para um personagem. (RN-010)"""
        return tuple(f for f in self.fatos if f.escopo.inclui(personagem))

    def fato(self, fato_id: str) -> Fato:
        for f in self.fatos:
            if f.id == fato_id:
                return f
        raise KeyError(fato_id)


class Solucao(BaseModel):
    """Nunca entra no contexto de um suspeito. (RN-011)"""

    model_config = ConfigDict(frozen=True)

    culpado: str
    meio: str
    motivo: str
    cadeia: tuple[str, ...] = Field(default=())
    """Ids dos fatos que provam o culpado, na ordem em que se encadeiam."""


class CasoCompleto(BaseModel):
    """Caso + solução. Só o gerador, o solver e o veredito veem isto."""

    model_config = ConfigDict(frozen=True)

    caso: Caso
    solucao: Solucao
