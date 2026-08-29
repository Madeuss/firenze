"""Invariantes estruturais do caso.

Cada função corresponde a uma regra numerada. Elas rodam sobre o caso pronto,
não sobre a intenção de quem gerou — é o que faz o teste valer alguma coisa
quando o gerador mudar, ou quando um caso vier de fora.
"""

from mansao.dominio import CasoCompleto, Papel, TipoFato


class CasoInvalido(ValueError):
    """Caso que viola uma regra de integridade. Nunca é publicável."""

    def __init__(self, regra: str, detalhe: str) -> None:
        super().__init__(f"{regra}: {detalhe}")
        self.regra = regra
        self.detalhe = detalhe


def validar(completo: CasoCompleto) -> None:
    """Roda todas as checagens. Levanta `CasoInvalido` na primeira violação."""
    rn_001_um_culpado(completo)
    rn_003_segredo_por_inocente(completo)
    rn_004_sem_sobreposicao(completo)
    rn_012_canary_em_fato_restrito(completo)


def rn_001_um_culpado(completo: CasoCompleto) -> None:
    suspeitos = {p.id for p in completo.caso.elenco if p.papel is Papel.suspeito}
    if completo.solucao.culpado not in suspeitos:
        raise CasoInvalido("RN-001", f"culpado {completo.solucao.culpado!r} não é suspeito do caso")


def rn_003_segredo_por_inocente(completo: CasoCompleto) -> None:
    inocentes = {
        p.id
        for p in completo.caso.elenco
        if p.papel is Papel.suspeito and p.id != completo.solucao.culpado
    }
    com_segredo = {f.expoe_segredo_de for f in completo.caso.fatos if f.tipo is TipoFato.segredo}
    faltando = inocentes - com_segredo
    if faltando:
        raise CasoInvalido("RN-003", f"inocentes sem segredo próprio: {sorted(faltando)}")


def rn_004_sem_sobreposicao(completo: CasoCompleto) -> None:
    """Ninguém em dois cômodos no mesmo intervalo."""
    onde: dict[tuple[str, int], str] = {}
    for fato in completo.caso.fatos:
        if fato.personagem is None or fato.comodo is None or fato.intervalo is None:
            continue
        chave = (fato.personagem, fato.intervalo)
        anterior = onde.setdefault(chave, fato.comodo)
        if anterior != fato.comodo:
            raise CasoInvalido(
                "RN-004",
                f"{fato.personagem} aparece na {anterior} e na {fato.comodo} "
                f"no intervalo {fato.intervalo}",
            )


def rn_012_canary_em_fato_restrito(completo: CasoCompleto) -> None:
    """Todo fato não-público carrega canary."""
    sem_canary = [f.id for f in completo.caso.fatos if not f.escopo.publico and not f.canary]
    if sem_canary:
        raise CasoInvalido("RN-012", f"fatos restritos sem canary: {sem_canary}")
