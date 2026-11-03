"""Como o agente aprende o processo da área, sem treinar o modelo.

- config/processo.md: contexto fixo que vai no prompt (fica em cache);
- dados/decisoes/*.json: decisões da revisão humana, um arquivo por revisão. As mais
  recentes com comentário viram exemplos para a análise;
- taxa de descarte por checagem: mostra qual regra está apontando o que a área não quer ver.
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROCESSO = RAIZ / "config" / "processo.md"
PASTA_DECISOES = RAIZ / "dados" / "decisoes"


def carregar_processo(caminho: Path = PROCESSO) -> str:
    return caminho.read_text(encoding="utf-8").strip() if caminho.exists() else ""


def codigo_de(decisao: dict) -> str:
    return decisao.get("codigo") or decisao["id"].split(":")[0]


def carregar_decisoes(pasta: Path = PASTA_DECISOES) -> list:
    """Lê todos os arquivos da pasta; para o mesmo achado vale a decisão mais recente."""
    por_id = {}
    for arquivo in sorted(pasta.glob("*.json")) if pasta.exists() else []:
        with open(arquivo, encoding="utf-8") as f:
            for d in json.load(f):
                atual = por_id.get(d["id"])
                if atual is None or d.get("em", "") >= atual.get("em", ""):
                    por_id[d["id"]] = d
    return sorted(por_id.values(), key=lambda d: d.get("em", ""))


def exemplos(decisoes: list, achados: list, por_codigo: int = 3) -> list:
    """Decisões mais recentes com comentário, só dos tipos de checagem desta execução."""
    codigos = {a["codigo"] for a in achados}
    escolhidos = {}
    for d in reversed(decisoes):
        codigo = codigo_de(d)
        if codigo not in codigos or not d.get("comentario"):
            continue
        lista = escolhidos.setdefault(codigo, [])
        if len(lista) < por_codigo:
            exemplo = {"codigo": codigo, "decisao": d["decisao"], "comentario": d["comentario"]}
            if d.get("evidencia"):
                exemplo["evidencia"] = d["evidencia"]
            lista.append(exemplo)
    return [e for codigo in sorted(escolhidos) for e in escolhidos[codigo]]


def taxa_descarte(decisoes: list, regras: dict) -> list:
    """Por checagem: quantos achados a área decidiu e quantos descartou."""
    cfg = regras.get("calibragem") or {}
    alerta, minimo = cfg.get("taxa_alerta", 0.5), cfg.get("minimo_decisoes", 3)
    contagem = {}
    for d in decisoes:
        c = contagem.setdefault(codigo_de(d), {"decididos": 0, "descartados": 0})
        c["decididos"] += 1
        c["descartados"] += d.get("decisao") == "descartar"
    linhas = []
    for codigo in sorted(contagem):
        c = contagem[codigo]
        taxa = c["descartados"] / c["decididos"]
        linhas.append({
            "codigo": codigo,
            "titulo": regras["checagens"].get(codigo, {}).get("titulo", codigo),
            **c,
            "taxa": round(taxa, 2),
            "calibrar": c["decididos"] >= minimo and taxa >= alerta,
        })
    return linhas
