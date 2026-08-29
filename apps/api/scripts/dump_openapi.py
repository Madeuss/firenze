"""Escreve o contrato em apps/api/openapi.json.

O arquivo é commitado (ADR-0003): é dele que `packages/contracts` gera os tipos
TypeScript. O CI regenera e falha se o resultado divergir do que está no repo —
contrato desatualizado é contrato quebrado esperando a hora.
"""

import json
from pathlib import Path

from mansao.main import app

DESTINO = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> None:
    esquema = json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True)
    DESTINO.write_text(esquema + "\n", encoding="utf-8")
    print(f"escrito: {DESTINO}")


if __name__ == "__main__":
    main()
