import pytest

from firenze.cli import main

Capture = pytest.CaptureFixture[str]


def _field(output: str, label: str) -> str:
    line = next(x for x in output.splitlines() if x.strip().startswith(label))
    return line.split(":", 1)[1].strip()


def test_generate_prints_the_briefing_without_the_solution(capsys: Capture) -> None:
    code = main(["generate", "--seed", "42"])
    out = capsys.readouterr().out

    assert code == 0
    assert "ELENCO" in out
    assert "Solução omitida" in out
    assert "culpado:" not in out


def test_reveal_shows_the_solution_and_the_solver_chain(capsys: Capture) -> None:
    main(["generate", "--seed", "42", "--reveal"])
    out = capsys.readouterr().out

    assert "SOLUÇÃO" in out
    assert "dedutível: True" in out


def test_locale_switches_the_prose_not_the_case(capsys: Capture) -> None:
    main(["generate", "--seed", "42", "--locale", "en", "--reveal"])
    english = capsys.readouterr().out
    main(["generate", "--seed", "42", "--reveal"])
    portuguese = capsys.readouterr().out

    assert "CAST" in english and "SOLUTION" in english
    assert "ELENCO" in portuguese
    # Same seed, same mystery: the culprit's name is a person, not a translation.
    culprit_en = _field(english, "culprit:")
    culprit_pt = _field(portuguese, "culpado:")
    assert culprit_en == culprit_pt


def test_json_does_not_carry_the_solution(capsys: Capture) -> None:
    main(["generate", "--seed", "42", "--json"])
    out = capsys.readouterr().out

    assert '"seed": 42' in out
    assert "culprit" not in out


def test_unknown_locale_is_an_error(capsys: Capture) -> None:
    code = main(["generate", "--seed", "1", "--locale", "tlh"])

    assert code == 1
    assert "available" in capsys.readouterr().err


def test_invalid_cast_returns_an_error_code(capsys: Capture) -> None:
    code = main(["generate", "--seed", "1", "--suspects", "2"])

    assert code == 1
    assert "3 suspects" in capsys.readouterr().err
