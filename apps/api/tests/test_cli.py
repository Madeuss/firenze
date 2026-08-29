from mansao.cli import main


def test_gerar_imprime_briefing_sem_revelar_a_solucao(capsys) -> None:  # type: ignore[no-untyped-def]
    codigo = main(["gerar", "--semente", "42"])
    saida = capsys.readouterr().out

    assert codigo == 0
    assert "ELENCO" in saida
    assert "Solução omitida" in saida
    assert "culpado:" not in saida


def test_revelar_mostra_solucao_e_cadeia_do_solver(capsys) -> None:  # type: ignore[no-untyped-def]
    main(["gerar", "--semente", "42", "--revelar"])
    saida = capsys.readouterr().out

    assert "SOLUÇÃO" in saida
    assert "dedutível: True" in saida


def test_json_nao_carrega_a_solucao(capsys) -> None:  # type: ignore[no-untyped-def]
    main(["gerar", "--semente", "42", "--json"])
    saida = capsys.readouterr().out

    assert '"semente": 42' in saida
    assert "culpado" not in saida


def test_elenco_invalido_retorna_codigo_de_erro(capsys) -> None:  # type: ignore[no-untyped-def]
    codigo = main(["gerar", "--semente", "1", "--suspeitos", "2"])

    assert codigo == 1
    assert "3 suspeitos" in capsys.readouterr().err
