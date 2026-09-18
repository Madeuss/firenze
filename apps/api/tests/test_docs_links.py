"""Relative links in the repository's Markdown have to resolve.

This lives in the API test suite because that is the only runner the CI has,
and a separate workflow would mean another required check to keep green. A
broken link in a public repository is a small thing that reads as carelessness
in the documents this project is partly judged on.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
MARKDOWN = sorted(
    path
    for path in REPO.rglob("*.md")
    if not any(part in {".venv", "node_modules", ".git"} for part in path.parts)
)
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# Um documento citado em crase é um link para quem lê, e não era para o teste:
# `docs/07-runbook.md` esteve no CLAUDE.md desde o começo apontando para um
# arquivo que não existia, e passou por aqui todas as vezes.
CITACAO = re.compile(r"`([^`\s]+\.md)`")


def test_the_suite_actually_found_the_documents() -> None:
    """A glob that silently matches nothing would make every assertion below pass."""
    assert len(MARKDOWN) >= 10


@pytest.mark.parametrize("document", MARKDOWN, ids=lambda p: str(p.relative_to(REPO)))
def test_relative_links_resolve(document: Path) -> None:
    broken = []
    for target in LINK.findall(document.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if not (document.parent / target.split("#")[0]).exists():
            broken.append(target)

    assert not broken, f"{document.relative_to(REPO)} points at: {broken}"


# O plano nomeia documentos que ainda não existem, e isso é o trabalho dele:
# uma árvore de diretórios pretendida e seções que dizem onde cada coisa vai
# morar. Cobrar existência ali seria cobrar que o futuro já tivesse acontecido.
PLANEJAMENTO = {"docs/00-plano-de-projeto.md"}


def _e_caminho(citado: str) -> bool:
    """`docs/agents/<id>.md` e `docs/agents/*.md` são formas, não arquivos."""
    return not any(marca in citado for marca in ("*", "<", ">", "?"))


@pytest.mark.parametrize("document", MARKDOWN, ids=lambda p: str(p.relative_to(REPO)))
def test_documents_named_in_backticks_exist(document: Path) -> None:
    """A path in code style is a promise too, and nothing was checking it.

    `docs/07-runbook.md` sat in CLAUDE.md from the first week, pointing at a file
    nobody had written, and passed this suite every single time — the link test
    only ever looked at `[text](target)`.
    """
    if str(document.relative_to(REPO)).replace("\\", "/") in PLANEJAMENTO:
        pytest.skip("um plano cita o que ainda vai existir")

    missing = [
        named
        for named in CITACAO.findall(document.read_text(encoding="utf-8"))
        if _e_caminho(named)
        and not (document.parent / named).exists()
        and not (REPO / named).exists()
    ]

    assert not missing, f"{document.relative_to(REPO)} names documents that do not exist: {missing}"
