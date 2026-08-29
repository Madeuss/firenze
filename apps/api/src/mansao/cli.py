"""Case generator CLI.

`mansao generate --seed 42` prints the case as a player would receive it. The
solution only shows with `--reveal`, and that is not decoration: if printing the
culprit were the default, running the command while developing would spoil every
case you meant to play.

`--locale` switches the catalog. The case itself does not change — same seed,
same structure, same culprit — only the prose does. That is the whole point of
ADR-0005, and running the two side by side is the cheapest way to see it.
"""

import argparse
import sys
from collections.abc import Sequence

from mansao.domain import CaseWithSolution, FactKind, Role
from mansao.generation import UnsolvableCase, generate, solve
from mansao.i18n import DEFAULT_LOCALE, Catalog, UnknownLocale, available_locales, load


def _briefing(full: CaseWithSolution, catalog: Catalog, reveal: bool) -> str:
    case = full.case
    label = catalog.label
    lines = [
        f"{label('case')} {case.seed} ({label('generator')} v{case.generator_version}, "
        f"{catalog.locale})",
        "",
        label("cast"),
    ]
    for character in case.cast:
        mark = f" ({label('victim')})" if character.role is Role.victim else ""
        lines.append(f"  {character.id:8} {character.name}{mark}")

    lines += ["", label("known")]
    lines += [f"  {f.id}  {catalog.fact(case, f)}" for f in case.facts if f.scope.public]

    lines += ["", label("dossiers")]
    for suspect in case.suspects:
        lines.append(
            f"  {suspect.id} — {suspect.name}: "
            f"{len(case.dossier(suspect.id))} {label('facts_count')}"
        )

    if not reveal:
        return "\n".join([*lines, "", label("hidden")])

    result = solve(case)
    lines += [
        "",
        label("solution"),
        f"  {label('culprit')}: {case.name_of(full.solution.culprit)}",
        f"  {label('means')}: {catalog.means(full.solution.means_key)}",
        f"  {label('motive')}: {catalog.motive(full.solution.motive_key)}",
        "",
        label("solver"),
        f"  {label('deducible')}: {result.deducible}",
        f"  {label('deduced')}: {result.deduced_culprit}",
        f"  {label('chain')}: {', '.join(result.chain)}",
        "",
        label("secrets"),
    ]
    lines += [
        f"  {f.character}: {catalog.fact(case, f)}" for f in case.facts if f.kind is FactKind.secret
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mansao", description="Mansão case generator.")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate a case from a seed")
    gen.add_argument("--seed", type=int, required=True)
    gen.add_argument("--suspects", type=int, default=6)
    gen.add_argument("--locale", default=DEFAULT_LOCALE, help=f"one of {available_locales()}")
    gen.add_argument("--reveal", action="store_true", help="show solution and solver chain")
    gen.add_argument("--json", action="store_true", help="print the case as JSON, no solution")

    args = parser.parse_args(argv)

    # The Windows console opens in cp1252 and eats the accents in the briefing.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        catalog = load(args.locale)
        full = generate(seed=args.seed, suspects=args.suspects)
    except (UnsolvableCase, UnknownLocale, ValueError) as failure:
        print(f"error: {failure}", file=sys.stderr)
        return 1

    if args.json:
        print(full.case.model_dump_json(indent=2))
    else:
        print(_briefing(full, catalog, reveal=args.reveal))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
