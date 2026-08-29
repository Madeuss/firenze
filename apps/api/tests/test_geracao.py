"""Testes do gerador, do solver e das invariantes.

Rodam sobre muitas sementes de propósito: uma semente que passa não prova nada
sobre o gerador, só sobre aquela semente.
"""

import pytest

from mansao.dominio import CasoCompleto, Papel, TipoFato
from mansao.geracao import CasoInvalido, gerar, resolver, validar
from mansao.geracao.solver import fatos_alcancaveis
from mansao.geracao.validacao import rn_004_sem_sobreposicao

SEMENTES = range(1, 41)


@pytest.fixture(scope="module")
def casos() -> list[CasoCompleto]:
    return [gerar(semente=s) for s in SEMENTES]


def test_gerador_e_deterministico() -> None:
    primeiro = gerar(semente=7)
    segundo = gerar(semente=7)

    assert primeiro.model_dump_json() == segundo.model_dump_json()


def test_sementes_diferentes_produzem_casos_diferentes() -> None:
    assert gerar(semente=7).caso.model_dump_json() != gerar(semente=8).caso.model_dump_json()


def test_todo_caso_gerado_passa_nas_invariantes(casos: list[CasoCompleto]) -> None:
    for completo in casos:
        validar(completo)


def test_solver_deduz_o_culpado_sem_ver_a_solucao(casos: list[CasoCompleto]) -> None:
    """RN-002: a dedução parte dos fatos alcançáveis, não da resposta."""
    for completo in casos:
        resultado = resolver(completo.caso)

        assert resultado.deduzivel, f"caso {completo.caso.semente}: {resultado.motivo_da_falha}"
        assert resultado.culpado_deduzido == completo.solucao.culpado
        assert resultado.candidatos == (completo.solucao.culpado,)


def test_rn_001_exatamente_um_culpado(casos: list[CasoCompleto]) -> None:
    for completo in casos:
        suspeitos = [p.id for p in completo.caso.elenco if p.papel is Papel.suspeito]

        assert completo.solucao.culpado in suspeitos
        assert len([p for p in completo.caso.elenco if p.papel is Papel.vitima]) == 1


def test_rn_003_todo_inocente_tem_segredo(casos: list[CasoCompleto]) -> None:
    for completo in casos:
        inocentes = {
            p.id
            for p in completo.caso.elenco
            if p.papel is Papel.suspeito and p.id != completo.solucao.culpado
        }
        com_segredo = {
            f.expoe_segredo_de for f in completo.caso.fatos if f.tipo is TipoFato.segredo
        }

        assert inocentes <= com_segredo


def test_rn_004_detecta_sobreposicao_plantada() -> None:
    """O validador precisa pegar o caso quebrado, não só aprovar o bom."""
    completo = gerar(semente=3)
    presenca = next(f for f in completo.caso.fatos if f.tipo is TipoFato.presenca)
    assert presenca.comodo is not None
    outro_comodo = next(c for c in completo.caso.comodos if c != presenca.comodo)
    adulterado = completo.model_copy(
        update={
            "caso": completo.caso.model_copy(
                update={
                    "fatos": (
                        *completo.caso.fatos,
                        presenca.model_copy(update={"id": "F-999", "comodo": outro_comodo}),
                    )
                }
            )
        }
    )

    with pytest.raises(CasoInvalido) as erro:
        rn_004_sem_sobreposicao(adulterado)

    assert erro.value.regra == "RN-004"


def test_rn_010_dossie_respeita_escopo(casos: list[CasoCompleto]) -> None:
    for completo in casos:
        for suspeito in completo.caso.suspeitos:
            for fato in completo.caso.dossie(suspeito.id):
                assert fato.escopo.inclui(suspeito.id)


def test_rn_011_solucao_nao_esta_no_caso(casos: list[CasoCompleto]) -> None:
    """O culpado não pode ser dedutível de um único campo do `Caso`."""
    for completo in casos:
        serializado = completo.caso.model_dump_json()

        assert "culpado" not in serializado
        assert completo.solucao.motivo not in serializado


def test_rn_012_fato_restrito_tem_canary(casos: list[CasoCompleto]) -> None:
    for completo in casos:
        for fato in completo.caso.fatos:
            if not fato.escopo.publico:
                assert fato.canary and fato.canary.startswith("CN-")


def test_culpado_nao_tem_alibi_alcancavel(casos: list[CasoCompleto]) -> None:
    """O núcleo do quebra-cabeça: todo inocente é excluído, o culpado não."""
    for completo in casos:
        caso = completo.caso
        alcancaveis = fatos_alcancaveis(caso)
        com_alibi = {
            f.personagem
            for f in alcancaveis
            if f.tipo is TipoFato.presenca
            and f.intervalo == caso.intervalo_crime
            and f.comodo != caso.comodo_crime
        }

        assert completo.solucao.culpado not in com_alibi
        assert com_alibi == {s.id for s in caso.suspeitos} - {completo.solucao.culpado}


def test_segredo_de_um_inocente_nao_vaza_para_outro(casos: list[CasoCompleto]) -> None:
    """RN-010 no ponto onde ela mais importa: o dossiê do vizinho."""
    for completo in casos:
        for fato in completo.caso.fatos:
            if fato.tipo is not TipoFato.segredo:
                continue
            dono = fato.expoe_segredo_de
            for suspeito in completo.caso.suspeitos:
                if suspeito.id != dono:
                    assert fato not in completo.caso.dossie(suspeito.id)


def test_menos_de_tres_suspeitos_e_recusado() -> None:
    with pytest.raises(ValueError, match="3 suspeitos"):
        gerar(semente=1, suspeitos=2)


@pytest.mark.parametrize("suspeitos", [3, 4, 5, 7])
def test_elenco_de_tamanhos_diferentes(suspeitos: int) -> None:
    completo = gerar(semente=11, suspeitos=suspeitos)

    validar(completo)
    assert len(completo.caso.suspeitos) == suspeitos
    assert resolver(completo.caso).culpado_deduzido == completo.solucao.culpado
