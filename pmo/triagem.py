"""Etapa 3 — triagem dos comentários com o Claude Haiku 5.5.

Lê só os comentários dos itens abertos e devolve:
- a classificação de cada item (bloqueio, desalinhamento, risco, ruído);
- conflitos entre itens que descrevem a mesma regra de jeitos diferentes (AL-01).
Sem chave de API, a triagem é pulada e os candidatos do código seguem como estão.
"""

import json

from .ia import MODELO_TRIAGEM, perguntar

SISTEMA = """Você faz a triagem de comentários do Jira para a PMO de uma empresa de tecnologia.
Para cada item, classifique o que os comentários indicam:
- "bloqueio": o trabalho está parado esperando algo ou alguém;
- "desalinhamento": o item descreve uma regra, valor ou entrega de forma diferente de outro item;
- "risco": há sinal de atraso ou problema, mas o trabalho segue;
- "ruido": nada relevante para a PMO.
Depois, compare os itens entre si e liste os conflitos: dois ou mais itens que descrevem a mesma
regra ou entrega com valores ou entendimentos diferentes. Cite os valores de cada lado.
Use só o que está nos comentários; não invente fatos.
Responda apenas com JSON neste formato:
{"itens": [{"chave": "...", "classificacao": "bloqueio|desalinhamento|risco|ruido", "resumo": "uma frase"}],
 "conflitos": [{"itens": ["...", "..."], "descricao": "uma frase com os valores de cada lado"}]}"""


def triar(comentarios: list, medidor) -> dict:
    if not comentarios:
        return {"itens": [], "conflitos": []}
    conteudo = "Itens com comentários:\n" + json.dumps(comentarios, ensure_ascii=False, indent=1)
    return perguntar("triagem", MODELO_TRIAGEM, SISTEMA, conteudo, medidor,
                     esforco="low", max_tokens=4000)


def aplicar_triagem(achados: list, triagem: dict, snapshot: dict, regras: dict) -> list:
    """Confirma ou descarta candidatos de bloqueio e acrescenta os conflitos (AL-01)."""
    por_chave = {t["chave"]: t for t in triagem.get("itens", [])}
    itens = {i["chave"]: i for i in snapshot["itens"]}
    resultado = []
    for achado in achados:
        if achado["origem"] == "candidato":
            leitura = por_chave.get(achado["itens"][0])
            if leitura and leitura["classificacao"] == "ruido":
                continue
            if leitura:
                achado = {**achado, "origem": "triagem", "leitura_ia": leitura["resumo"]}
        resultado.append(achado)

    cfg = {"titulo": "Mesma regra descrita de forma diferente", "severidade": "media"}
    for conflito in triagem.get("conflitos", []):
        chaves = [c for c in conflito.get("itens", []) if c in itens]
        if len(chaves) < 2:
            continue
        boards = sorted({itens[c]["board"] for c in chaves})
        resultado.append({
            "id": f"AL-01:{'+'.join(chaves)}",
            "codigo": "AL-01",
            "titulo": cfg["titulo"],
            "severidade": cfg["severidade"],
            "board": " + ".join(boards),
            "itens": chaves,
            "evidencia": conflito["descricao"],
            "origem": "triagem",
        })
    return resultado
