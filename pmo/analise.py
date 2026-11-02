"""Etapa 4 — análise com o Claude Opus 5.5.

Recebe só os achados já resumidos (nunca o Jira cru) e devolve o resumo executivo,
a severidade final e a recomendação de cada achado. Sem chave de API, usa
recomendações padrão por tipo de checagem.
"""

import json

from .ia import MODELO_ANALISE, perguntar

SISTEMA = """Você é o analista da PMO. Recebe achados de saúde do portfólio (atrasos, dependências,
deploys, regras) que o código já verificou, com as evidências.
Para cada achado:
- ajuste a severidade (alta, media, baixa) pelo impacto cruzado: um atraso que trava um deploy
  ou outro time sobe de nível; um campo vazio sem impacto pode descer;
- escreva uma recomendação concreta e curta (quem precisa fazer o quê);
- diga em uma frase qual é o impacto se nada for feito.
Escreva também um resumo de no máximo 3 frases para a área de projetos, começando pelo maior risco.
Use só os fatos dos achados; não invente datas, nomes ou números. Escreva em português do Brasil.
Responda apenas com JSON neste formato:
{"resumo": ["frase", "frase"],
 "achados": [{"id": "...", "severidade": "alta|media|baixa", "recomendacao": "...", "impacto": "..."}]}"""

PADRAO = {
    "DT-01": "Atualizar a data com o time ou quebrar o que falta em um novo épico.",
    "DT-02": "Rever a data da história ou ajustar a data do épico.",
    "DP-01": "Alinhar com o time da dependência se dá para antecipar, ou replanejar o item dependente.",
    "DP-02": "Substituir a dependência por um item válido, com responsável e data.",
    "DP-03": "Quebrar o ciclo definindo qual dos itens entrega primeiro.",
    "DY-01": "Mover o deploy para depois da dependência ou subir com a funcionalidade desligada.",
    "RG-01": "Pedir ao PO para completar os campos antes do refinamento.",
    "AL-01": "Confirmar a regra com Produto e atualizar os itens envolvidos.",
    "AL-02": "Sinalizar o impedimento no Jira e escalar com quem destrava.",
}


def analisar(achados: list, medidor) -> dict:
    if not achados:
        return {"resumo": ["Nenhum achado nesta execução."], "achados": []}
    enxuto = [
        {k: a[k] for k in ("id", "codigo", "titulo", "severidade", "board", "itens", "evidencia")}
        for a in achados
    ]
    conteudo = "Achados desta execução:\n" + json.dumps(enxuto, ensure_ascii=False, indent=1)
    return perguntar("analise", MODELO_ANALISE, SISTEMA, conteudo, medidor,
                     esforco="medium", max_tokens=16000)


def analise_padrao(achados: list) -> dict:
    altas = [a for a in achados if a["severidade"] == "alta"]
    resumo = [f"{len(achados)} achados, {len(altas)} de severidade alta."]
    if altas:
        resumo.append(f"Maior risco: {altas[0]['evidencia']}.")
    resumo.append("Análise sem IA: recomendações padrão por tipo de checagem.")
    return {
        "resumo": resumo,
        "achados": [
            {"id": a["id"], "severidade": a["severidade"],
             "recomendacao": PADRAO.get(a["codigo"], ""), "impacto": ""}
            for a in achados
        ],
    }


def combinar(achados: list, analise: dict) -> list:
    """Junta a análise aos achados; o que o modelo não devolveu fica com o padrão."""
    por_id = {a["id"]: a for a in analise.get("achados", [])}
    resultado = []
    for achado in achados:
        extra = por_id.get(achado["id"], {})
        severidade = extra.get("severidade")
        resultado.append({
            **achado,
            "severidade_codigo": achado["severidade"],
            "severidade": severidade if severidade in ("alta", "media", "baixa") else achado["severidade"],
            "recomendacao": extra.get("recomendacao") or PADRAO.get(achado["codigo"], ""),
            "impacto": extra.get("impacto", ""),
        })
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    resultado.sort(key=lambda a: (ordem[a["severidade"]], a["codigo"], a["id"]))
    return resultado
