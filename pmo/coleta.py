"""Etapa 1 — coleta.

Na POC a fonte é o Jira fictício em dados/exemplo/jira.json. A leitura do Jira
real (incremental, via REST API, só leitura) entra na fase 4, depois da
aprovação de Segurança.
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLO = RAIZ / "dados" / "exemplo" / "jira.json"


def coletar(fonte: str = "exemplo") -> dict:
    """Devolve o snapshot: {"data_referencia", "releases", "itens"}."""
    if fonte == "exemplo":
        with open(EXEMPLO, encoding="utf-8") as f:
            snapshot = json.load(f)
        validar(snapshot)
        return snapshot
    if fonte == "jira":
        raise NotImplementedError(
            "A leitura do Jira real entra na fase 4 da POC, depois da aprovação "
            "de Segurança. Use --fonte exemplo."
        )
    raise ValueError(f"Fonte desconhecida: {fonte}")


def validar(snapshot: dict) -> None:
    """Falha cedo se o snapshot não tiver o formato que as checagens esperam."""
    for chave in ("data_referencia", "releases", "itens"):
        if chave not in snapshot:
            raise ValueError(f"Snapshot sem o campo obrigatório '{chave}'")
    chaves = [item["chave"] for item in snapshot["itens"]]
    repetidas = {c for c in chaves if chaves.count(c) > 1}
    if repetidas:
        raise ValueError(f"Itens repetidos no snapshot: {sorted(repetidas)}")
