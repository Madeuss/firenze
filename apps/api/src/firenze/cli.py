"""Case generator CLI.

`firenze generate --seed 42` prints the case as a player would receive it. The
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

from firenze.config import settings
from firenze.domain import CaseWithSolution, FactKind, Role
from firenze.generation import UnsolvableCase, generate, solve
from firenze.i18n import DEFAULT_LOCALE, Catalog, UnknownLocale, available_locales, load
from firenze.model import ModelUnavailable, resolve
from firenze.veneer import CaseVeneer, VeneerRejected, VeneerUnavailable, write


def _briefing(
    full: CaseWithSolution,
    catalog: Catalog,
    reveal: bool,
    veneer: CaseVeneer | None = None,
) -> str:
    case = full.case
    label = catalog.label
    lines = [
        f"{label('case')} {case.seed} ({label('generator')} v{case.generator_version}, "
        f"{catalog.locale})",
        "",
        label("cast"),
    ]
    if veneer is not None:
        lines = [lines[0], "", veneer.scene, "", label("cast")]
    for character in case.cast:
        mark = f" ({label('victim')})" if character.role is Role.victim else ""
        lines.append(f"  {character.id:8} {character.name}{mark}")
        if veneer is not None and character.role is not Role.victim:
            surface = veneer.for_character(character.id)
            lines.append(f"           {surface.role_title}. {surface.appearance}")
            lines.append(f"           {surface.manner}")

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
    parser = argparse.ArgumentParser(prog="firenze", description="Firenze case generator.")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate a case from a seed")
    gen.add_argument("--seed", type=int, required=True)
    gen.add_argument("--suspects", type=int, default=6)
    gen.add_argument("--locale", default=DEFAULT_LOCALE, help=f"one of {available_locales()}")
    gen.add_argument("--reveal", action="store_true", help="show solution and solver chain")
    gen.add_argument(
        "--veneer",
        action="store_true",
        help="have a model write the cast and the scene; needs ANTHROPIC_API_KEY",
    )
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

    veneer = None
    if args.veneer:
        try:
            model = resolve(
                settings.model_provider,
                model=settings.model_name,
                base_url=settings.model_base_url,
                api_key=settings.model_api_key.get_secret_value(),
            )
            veneer = write(full.case, catalog, model=model)
        except (VeneerUnavailable, VeneerRejected, ModelUnavailable) as failure:
            # The case is playable without prose. Degrading beats failing.
            print(f"veneer skipped: {failure}", file=sys.stderr)

    if args.json:
        print(full.case.model_dump_json(indent=2))
    else:
        print(_briefing(full, catalog, reveal=args.reveal, veneer=veneer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
