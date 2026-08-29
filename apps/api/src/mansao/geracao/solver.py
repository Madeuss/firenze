"""Solver de dedutibilidade.

Recebe `Caso`, nunca `CasoCompleto`: se ele enxergasse a solução, provaria
apenas que sabe ler. A assinatura é a garantia. (RN-002, RN-011)

O modelo de dedução: parte dos fatos públicos e acrescenta tudo que algum
suspeito revelaria se perguntado — um suspeito diz a verdade sobre qualquer
fato que não o incrimine nem exponha seu segredo (RN-020). Sobre esse conjunto
alcançável, o caso é dedutível quando sobra exatamente um suspeito sem álibi
confirmado e existe prova física apontando para ele.
"""

from pydantic import BaseModel, ConfigDict

from mansao.dominio import Caso, Fato, TipoFato


class Resultado(BaseModel):
    model_config = ConfigDict(frozen=True)

    deduzivel: bool
    culpado_deduzido: str | None
    candidatos: tuple[str, ...]
    cadeia: tuple[str, ...]
    motivo_da_falha: str | None = None


def dira_a_verdade(caso: Caso, suspeito: str, fato: Fato) -> bool:
    """Um suspeito mente só sobre o que o incrimina ou expõe seu segredo. (RN-020)"""
    if fato.expoe_segredo_de == suspeito:
        return False
    if fato.incrimina == suspeito:
        return False
    incrimina_por_presenca = (
        fato.tipo is TipoFato.presenca
        and fato.personagem == suspeito
        and fato.comodo == caso.comodo_crime
        and fato.intervalo == caso.intervalo_crime
    )
    return not incrimina_por_presenca


def fatos_alcancaveis(caso: Caso) -> tuple[Fato, ...]:
    """Fatos públicos mais tudo que alguém revelaria ao ser perguntado.

    Uma passada basta: hoje a disposição de revelar não depende do que o
    jogador já sabe. Quando o confronto destravar fatos (fase 4), isto vira
    ponto fixo.
    """
    alcancaveis: dict[str, Fato] = {f.id: f for f in caso.fatos if f.escopo.publico}
    for suspeito in caso.suspeitos:
        for fato in caso.dossie(suspeito.id):
            if fato.id not in alcancaveis and dira_a_verdade(caso, suspeito.id, fato):
                alcancaveis[fato.id] = fato
    return tuple(alcancaveis.values())


def _tem_alibi(fato: Fato, caso: Caso) -> bool:
    return (
        fato.tipo is TipoFato.presenca
        and fato.intervalo == caso.intervalo_crime
        and fato.comodo != caso.comodo_crime
        and fato.testemunha is not None
        and fato.testemunha != fato.personagem
    )


def resolver(caso: Caso) -> Resultado:
    alcancaveis = fatos_alcancaveis(caso)

    alibis: dict[str, str] = {
        f.personagem: f.id for f in alcancaveis if f.personagem is not None and _tem_alibi(f, caso)
    }
    candidatos = tuple(s.id for s in caso.suspeitos if s.id not in alibis)

    if len(candidatos) != 1:
        return Resultado(
            deduzivel=False,
            culpado_deduzido=None,
            candidatos=candidatos,
            cadeia=(),
            motivo_da_falha=(
                "nenhum suspeito sem álibi"
                if not candidatos
                else f"{len(candidatos)} suspeitos sem álibi confirmado"
            ),
        )

    candidato = candidatos[0]
    provas = tuple(
        f.id for f in alcancaveis if f.tipo is TipoFato.objeto and f.incrimina == candidato
    )
    if not provas:
        return Resultado(
            deduzivel=False,
            culpado_deduzido=None,
            candidatos=candidatos,
            cadeia=(),
            motivo_da_falha="sem prova física alcançável apontando para o único candidato",
        )

    corpo = tuple(f.id for f in alcancaveis if f.tipo is TipoFato.corpo)
    return Resultado(
        deduzivel=True,
        culpado_deduzido=candidato,
        candidatos=candidatos,
        cadeia=corpo + tuple(sorted(alibis.values())) + provas,
    )
