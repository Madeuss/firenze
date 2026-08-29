"""Gerador determinístico de casos.

A estrutura do caso — culpado, linha do tempo, fatos e escopos — é montada por
código a partir de uma semente (ADR-0004). O LLM entra depois, só no verniz:
nomes, personalidade e descrição. Mesma semente e mesma versão do gerador
produzem exatamente o mesmo caso, que é o que torna eval reproduzível.

Nada aqui pergunta ao solver como resolver; o solver é chamado no fim e tem
poder de veto (RN-002).
"""

import hashlib
import random
from itertools import count

from mansao.dominio import (
    Caso,
    CasoCompleto,
    Escopo,
    Fato,
    Papel,
    Personagem,
    Solucao,
    TipoFato,
)
from mansao.geracao.solver import resolver
from mansao.geracao.validacao import validar

VERSAO_GERADOR = "1"

COMODOS = (
    "biblioteca",
    "salão",
    "sala de jantar",
    "cozinha",
    "adega",
    "escritório",
    "jardim de inverno",
    "porão",
)
COMODOS_DISCRETOS = ("adega", "escritório", "porão")
# Preposição contraída por cômodo. O verniz do LLM reescreve estas frases,
# mas caso reprovado no solver também é lido por humano — vale sair certo.
PREPOSICAO = {
    "biblioteca": "na",
    "salão": "no",
    "sala de jantar": "na",
    "cozinha": "na",
    "adega": "na",
    "escritório": "no",
    "jardim de inverno": "no",
    "porão": "no",
}
INTERVALOS = ("21h00", "21h30", "22h00", "22h30", "23h00", "23h30")

NOMES = (
    "Aurélio Bastos",
    "Ondina Vilar",
    "Teodoro Mainz",
    "Clarice Antunes",
    "Bartolomeu Sá",
    "Ilma Prado",
    "Nazareno Cruz",
    "Vitória Belmiro",
    "Godofredo Alves",
    "Marlene Tostes",
)
NOME_VITIMA = "Rodolfo Andrade"

MEIOS = ("castiçal de bronze", "veneno no decanter", "abridor de cartas", "corda de cortina")
MOTIVOS = (
    "herança que seria redirecionada na manhã seguinte",
    "chantagem prestes a virar escândalo",
    "sociedade desfeita sem acerto de contas",
    "carta que provava uma falsificação antiga",
)
SEGREDOS = (
    "desviava vinho da adega para revender",
    "lia a correspondência do anfitrião",
    "escondia dívidas de jogo",
    "encontrava-se às escondidas com alguém da casa",
    "falsificou uma assinatura no livro-caixa",
    "guardava objetos que não lhe pertenciam",
)


class CasoInsoluvel(RuntimeError):
    """O gerador não achou caso dedutível dentro do orçamento de tentativas."""


def _canary(semente: int, fato_id: str) -> str:
    digest = hashlib.blake2s(f"{semente}:{fato_id}".encode(), digest_size=4).hexdigest()
    return f"CN-{digest}"


def _em(comodo: str) -> str:
    return f"{PREPOSICAO.get(comodo, 'em')} {comodo}"


def _escopo(*personagens: str) -> Escopo:
    return Escopo(publico=False, personagens=frozenset(personagens))


def gerar(semente: int, suspeitos: int = 6, tentativas: int = 20) -> CasoCompleto:
    """Gera um caso válido e dedutível, ou levanta `CasoInsoluvel`.

    Cada tentativa usa uma semente derivada. Caso reprovado é descartado —
    afrouxar a validação para aproveitá-lo é o erro que RN-002 existe para
    impedir.
    """
    if suspeitos < 3:
        raise ValueError("um caso precisa de ao menos 3 suspeitos para ter álibis cruzados")

    for tentativa in range(tentativas):
        derivada = semente if tentativa == 0 else semente * 1000 + tentativa
        candidato = _montar(semente=semente, semente_efetiva=derivada, suspeitos=suspeitos)
        validar(candidato)
        if resolver(candidato.caso).culpado_deduzido == candidato.solucao.culpado:
            return candidato

    raise CasoInsoluvel(f"nenhum caso dedutível em {tentativas} tentativas a partir de {semente}")


def _montar(semente: int, semente_efetiva: int, suspeitos: int) -> CasoCompleto:
    rng = random.Random(semente_efetiva)

    nomes = list(NOMES)
    rng.shuffle(nomes)
    elenco = (
        Personagem(id="vitima", nome=NOME_VITIMA, papel=Papel.vitima),
        *(
            Personagem(id=f"sus-{i + 1}", nome=nomes[i], papel=Papel.suspeito)
            for i in range(suspeitos)
        ),
    )
    ids = [p.id for p in elenco if p.papel is Papel.suspeito]

    comodo_crime = rng.choice(COMODOS)
    intervalo_crime = rng.randrange(1, len(INTERVALOS) - 1)
    culpado = rng.choice(ids)
    inocentes = [i for i in ids if i != culpado]

    movimentos = _mover(rng, ids, culpado, inocentes, comodo_crime, intervalo_crime)
    segredos = _segredos(rng, inocentes, intervalo_crime, movimentos)

    fatos = _fatos(
        semente=semente,
        rng=rng,
        ids=ids,
        culpado=culpado,
        inocentes=inocentes,
        movimentos=movimentos,
        segredos=segredos,
        comodo_crime=comodo_crime,
        intervalo_crime=intervalo_crime,
    )

    caso = Caso(
        semente=semente,
        versao_gerador=VERSAO_GERADOR,
        comodos=COMODOS,
        intervalos=INTERVALOS,
        elenco=elenco,
        fatos=fatos,
        comodo_crime=comodo_crime,
        intervalo_crime=intervalo_crime,
    )
    solucao = Solucao(
        culpado=culpado,
        meio=rng.choice(MEIOS),
        motivo=rng.choice(MOTIVOS),
        cadeia=tuple(f.id for f in fatos if f.tipo is TipoFato.objeto and f.incrimina == culpado),
    )
    return CasoCompleto(caso=caso, solucao=solucao)


def _mover(
    rng: random.Random,
    ids: list[str],
    culpado: str,
    inocentes: list[str],
    comodo_crime: str,
    intervalo_crime: int,
) -> dict[tuple[str, int], str]:
    """Onde cada suspeito estava em cada intervalo.

    Um dicionário de (personagem, intervalo) para cômodo torna RN-004
    impossível por construção — não há como estar em dois lugares. O validador
    ainda checa, porque o caso pode ser tocado depois daqui.
    """
    movimentos: dict[tuple[str, int], str] = {}

    # No intervalo do crime o culpado está sozinho com a vítima e cada inocente
    # está acompanhado: é isso que deixa exatamente um suspeito sem álibi.
    movimentos[(culpado, intervalo_crime)] = comodo_crime
    disponiveis = [c for c in COMODOS if c != comodo_crime]
    rng.shuffle(disponiveis)

    embaralhados = list(inocentes)
    rng.shuffle(embaralhados)
    grupos = [embaralhados[i : i + 2] for i in range(0, len(embaralhados), 2)]
    if len(grupos) > 1 and len(grupos[-1]) == 1:
        grupos[-2].extend(grupos.pop())

    for grupo, comodo in zip(grupos, disponiveis, strict=False):
        for pid in grupo:
            movimentos[(pid, intervalo_crime)] = comodo

    for t in range(len(INTERVALOS)):
        if t == intervalo_crime:
            continue
        for pid in ids:
            movimentos[(pid, t)] = rng.choice(COMODOS)

    return movimentos


def _segredos(
    rng: random.Random,
    inocentes: list[str],
    intervalo_crime: int,
    movimentos: dict[tuple[str, int], str],
) -> dict[str, tuple[str, int, str]]:
    """Um segredo por inocente: cômodo, intervalo e o que ele esconde. (RN-003)

    O segredo acontece longe do crime e sempre a sós — segredo com testemunha
    não faz ninguém mentir.
    """
    segredos: dict[str, tuple[str, int, str]] = {}
    textos = list(SEGREDOS)
    rng.shuffle(textos)

    # Pares (cômodo, intervalo) distintos por inocente. Se dois segredos
    # caíssem no mesmo par, esvaziar o cômodo para um deles moveria o outro
    # para longe do próprio segredo — e o fato passaria a contradizer a linha
    # do tempo (RN-004).
    pares = [
        (comodo, t)
        for comodo in COMODOS_DISCRETOS
        for t in range(len(INTERVALOS))
        if t != intervalo_crime
    ]
    rng.shuffle(pares)
    if len(pares) < len(inocentes):
        raise ValueError("cômodos discretos insuficientes para dar um segredo a cada inocente")

    for pid, texto, (comodo, intervalo) in zip(inocentes, textos, pares, strict=False):
        segredos[pid] = (comodo, intervalo, texto)
        movimentos[(pid, intervalo)] = comodo

        # Segredo com testemunha não faz ninguém mentir: o cômodo fica só dele.
        alternativo = rng.choice([c for c in COMODOS if c != comodo])
        for chave, onde in list(movimentos.items()):
            if chave[1] == intervalo and chave[0] != pid and onde == comodo:
                movimentos[chave] = alternativo

    return segredos


def _fatos(
    *,
    semente: int,
    rng: random.Random,
    ids: list[str],
    culpado: str,
    inocentes: list[str],
    movimentos: dict[tuple[str, int], str],
    segredos: dict[str, tuple[str, int, str]],
    comodo_crime: str,
    intervalo_crime: int,
) -> tuple[Fato, ...]:
    numero = count(1)

    def novo_id() -> str:
        return f"F-{next(numero):03d}"

    fatos: list[Fato] = [
        Fato(
            id=novo_id(),
            tipo=TipoFato.corpo,
            descricao=(
                f"O corpo de {NOME_VITIMA} foi encontrado {_em(comodo_crime)}, "
                f"por volta das {INTERVALOS[intervalo_crime]}."
            ),
            escopo=Escopo(publico=True),
            comodo=comodo_crime,
            intervalo=intervalo_crime,
        )
    ]

    # Presença só vira fato quando alguém pode atestar. Quem estava sozinho não
    # ganha álibi — e é essa ausência que o solver procura.
    for t in range(len(INTERVALOS)):
        por_comodo: dict[str, list[str]] = {}
        for pid in ids:
            por_comodo.setdefault(movimentos[(pid, t)], []).append(pid)

        for comodo, presentes in sorted(por_comodo.items()):
            if len(presentes) < 2:
                continue
            for i, pid in enumerate(presentes):
                testemunha = presentes[(i + 1) % len(presentes)]
                fato_id = novo_id()
                fatos.append(
                    Fato(
                        id=fato_id,
                        tipo=TipoFato.presenca,
                        descricao=(
                            f"{pid} estava {_em(comodo)} às {INTERVALOS[t]}, "
                            f"na presença de {testemunha}."
                        ),
                        escopo=_escopo(pid, testemunha),
                        personagem=pid,
                        comodo=comodo,
                        intervalo=t,
                        testemunha=testemunha,
                        canary=_canary(semente, fato_id),
                    )
                )

    for pid, (comodo, intervalo, texto) in segredos.items():
        fato_id = novo_id()
        fatos.append(
            Fato(
                id=fato_id,
                tipo=TipoFato.segredo,
                descricao=f"{pid} {texto} — estava {_em(comodo)} às {INTERVALOS[intervalo]}.",
                escopo=_escopo(pid),
                personagem=pid,
                comodo=comodo,
                intervalo=intervalo,
                expoe_segredo_de=pid,
                canary=_canary(semente, fato_id),
            )
        )

    # A prova. Quem a encontrou não tem motivo para escondê-la, então ela é
    # alcançável por interrogatório — é o passo que fecha a dedução.
    achou = rng.choice(inocentes)
    fato_id = novo_id()
    fatos.append(
        Fato(
            id=fato_id,
            tipo=TipoFato.objeto,
            descricao=(
                f"{achou} viu, {_em(comodo_crime)}, um objeto pessoal de {culpado} "
                f"que não deveria estar ali às {INTERVALOS[intervalo_crime]}."
            ),
            escopo=_escopo(achou),
            # O fato fala de onde o *dono do objeto* esteve; quem achou entra
            # como testemunha. Marcar o descobridor como `personagem` o
            # colocaria na cena do crime e quebraria a linha do tempo (RN-004).
            personagem=culpado,
            testemunha=achou,
            comodo=comodo_crime,
            intervalo=intervalo_crime,
            incrimina=culpado,
            canary=_canary(semente, fato_id),
        )
    )

    return tuple(fatos)
