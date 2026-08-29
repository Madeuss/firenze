"""CLI do gerador de casos.

`mansao gerar --semente 42` imprime o caso como o jogador o receberia. A solução
só aparece com `--revelar`, e isso não é firula: se o padrão fosse imprimir o
culpado, o hábito de rodar o comando durante o desenvolvimento estragaria todo
caso que você fosse jogar.
"""

import argparse
import sys
from collections.abc import Sequence

from mansao.dominio import CasoCompleto, Papel, TipoFato
from mansao.geracao import CasoInsoluvel, gerar, resolver


def _briefing(completo: CasoCompleto, revelar: bool) -> str:
    caso = completo.caso
    linhas = [
        f"Caso {caso.semente} (gerador v{caso.versao_gerador})",
        "",
        "ELENCO",
    ]
    for p in caso.elenco:
        marca = " (vítima)" if p.papel is Papel.vitima else ""
        linhas.append(f"  {p.id:8} {p.nome}{marca}")

    linhas += ["", "O QUE SE SABE"]
    linhas += [f"  {f.id}  {f.descricao}" for f in caso.fatos if f.escopo.publico]

    linhas += ["", "DOSSIÊS (o que cada suspeito sabe)"]
    for s in caso.suspeitos:
        dossie = caso.dossie(s.id)
        linhas.append(f"  {s.id} — {s.nome}: {len(dossie)} fatos")

    if not revelar:
        linhas += ["", "Solução omitida. Use --revelar para vê-la."]
        return "\n".join(linhas)

    resultado = resolver(caso)
    linhas += [
        "",
        "SOLUÇÃO",
        f"  culpado: {completo.solucao.culpado}",
        f"  meio:    {completo.solucao.meio}",
        f"  motivo:  {completo.solucao.motivo}",
        "",
        "SOLVER",
        f"  dedutível: {resultado.deduzivel}",
        f"  deduziu:   {resultado.culpado_deduzido}",
        f"  cadeia:    {', '.join(resultado.cadeia)}",
        "",
        "SEGREDOS (por que os inocentes mentem)",
    ]
    linhas += [
        f"  {f.expoe_segredo_de}: {f.descricao}" for f in caso.fatos if f.tipo is TipoFato.segredo
    ]
    return "\n".join(linhas)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mansao", description="Gerador de casos do Mansão.")
    sub = parser.add_subparsers(dest="comando", required=True)

    g = sub.add_parser("gerar", help="gera um caso a partir de uma semente")
    g.add_argument("--semente", type=int, required=True)
    g.add_argument("--suspeitos", type=int, default=6)
    g.add_argument("--revelar", action="store_true", help="mostra solução e cadeia do solver")
    g.add_argument("--json", action="store_true", help="imprime o caso como JSON, sem a solução")

    args = parser.parse_args(argv)

    # O console do Windows abre em cp1252 e come os acentos do briefing.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        completo = gerar(semente=args.semente, suspeitos=args.suspeitos)
    except (CasoInsoluvel, ValueError) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    if args.json:
        print(completo.caso.model_dump_json(indent=2))
    else:
        print(_briefing(completo, revelar=args.revelar))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
