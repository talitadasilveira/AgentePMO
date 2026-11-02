"""Etapa 2 — checagens objetivas, feitas em código (nenhum token gasto).

Cada checagem devolve achados no formato:
    {"id", "codigo", "titulo", "severidade", "board", "itens", "evidencia", "origem"}
"""

from datetime import date
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
REGRAS = RAIZ / "config" / "regras.yaml"

TIPOS_PLANEJAVEIS = ("Iniciativa", "Epico")


def carregar_regras(caminho: Path = REGRAS) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _data(valor):
    return date.fromisoformat(valor) if valor else None


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


class Contexto:
    """Snapshot indexado por chave, com os atalhos que as checagens usam."""

    def __init__(self, snapshot: dict, regras: dict):
        self.regras = regras
        self.hoje = _data(snapshot["data_referencia"])
        self.itens = {i["chave"]: i for i in snapshot["itens"]}
        self.releases = snapshot["releases"]
        self.concluido = set(regras["status_concluido"])
        self.cancelado = set(regras["status_cancelado"])

    def aberto(self, item: dict) -> bool:
        return item["status"] not in self.concluido | self.cancelado

    def cancelado_(self, item: dict) -> bool:
        return item["status"] in self.cancelado


def _achado(ctx, codigo, itens, evidencia, board=None, origem="codigo"):
    cfg = ctx.regras["checagens"][codigo]
    if board is None:
        boards = sorted({ctx.itens[c]["board"] for c in itens if c in ctx.itens})
        board = " + ".join(boards)
    return {
        "id": f"{codigo}:{'+'.join(itens)}",
        "codigo": codigo,
        "titulo": cfg["titulo"],
        "severidade": cfg["severidade"],
        "board": board,
        "itens": list(itens),
        "evidencia": evidencia,
        "origem": origem,
    }


def dt01_vencidos(ctx):
    """Iniciativa ou épico com data de fim no passado e ainda aberto."""
    for item in ctx.itens.values():
        fim = _data(item["fim"])
        if item["tipo"] in TIPOS_PLANEJAVEIS and ctx.aberto(item) and fim and fim < ctx.hoje:
            abertos = [
                f["chave"] for f in ctx.itens.values()
                if f["pai"] == item["chave"] and ctx.aberto(f)
            ]
            dias = (ctx.hoje - fim).days
            evid = f"{item['chave']} {item['titulo']}: fim em {_br(fim)}, vencido há {dias} dias"
            if abertos:
                evid += f"; {len(abertos)} filho(s) aberto(s): {', '.join(abertos)}"
            yield _achado(ctx, "DT-01", [item["chave"]], evid)


def dt02_filho_depois_do_pai(ctx):
    """História cuja data de fim passa da data de fim do épico."""
    for item in ctx.itens.values():
        pai = ctx.itens.get(item["pai"]) if item["pai"] else None
        if item["tipo"] != "Historia" or not pai or not ctx.aberto(item):
            continue
        fim, fim_pai = _data(item["fim"]), _data(pai["fim"])
        if fim and fim_pai and fim > fim_pai:
            evid = (
                f"{item['chave']} termina em {_br(fim)}, "
                f"{(fim - fim_pai).days} dias depois do épico {pai['chave']} ({_br(fim_pai)})"
            )
            yield _achado(ctx, "DT-02", [item["chave"], pai["chave"]], evid)


def dp01_dependencia_atrasada(ctx):
    """Dependência termina depois do item que depende dela."""
    for item in ctx.itens.values():
        if not ctx.aberto(item):
            continue
        for chave_dep in item["depende_de"]:
            dep = ctx.itens.get(chave_dep)
            if not dep or ctx.cancelado_(dep) or not ctx.aberto(dep):
                continue
            fim, fim_dep = _data(item["fim"]), _data(dep["fim"])
            if fim and fim_dep and fim_dep > fim:
                evid = (
                    f"{item['chave']} {item['titulo']} (fim {_br(fim)}) depende de "
                    f"{dep['chave']} {dep['titulo']} (fim {_br(fim_dep)}): "
                    f"folga negativa de {(fim_dep - fim).days} dias"
                )
                yield _achado(ctx, "DP-01", [item["chave"], dep["chave"]], evid)


def dp02_dependencia_solta(ctx):
    """Dependência que não existe, foi cancelada, ou está sem dono ou sem data."""
    for item in ctx.itens.values():
        if not ctx.aberto(item):
            continue
        for chave_dep in item["depende_de"]:
            dep = ctx.itens.get(chave_dep)
            motivos = []
            if dep is None:
                motivos.append("não existe no snapshot")
            else:
                if ctx.cancelado_(dep):
                    motivos.append("está cancelada")
                if not dep["responsavel"]:
                    motivos.append("está sem responsável")
                if not dep["fim"] and ctx.aberto(dep):
                    motivos.append("está sem data de fim")
            if motivos:
                evid = f"{item['chave']} depende de {chave_dep}, que " + " e ".join(motivos)
                yield _achado(ctx, "DP-02", [item["chave"], chave_dep], evid,
                              board=item["board"])


def dp03_ciclos(ctx):
    """Ciclo de dependências (A depende de B, que depende de A)."""
    vistos = set()
    for inicio in ctx.itens:
        pilha = [(inicio, [inicio])]
        while pilha:
            atual, caminho = pilha.pop()
            for prox in ctx.itens.get(atual, {}).get("depende_de", []):
                if prox == inicio:
                    ciclo = tuple(sorted(caminho))
                    if ciclo not in vistos:
                        vistos.add(ciclo)
                        evid = "Ciclo: " + " → ".join(caminho + [inicio])
                        yield _achado(ctx, "DP-03", list(ciclo), evid)
                elif prox in ctx.itens and prox not in caminho:
                    pilha.append((prox, caminho + [prox]))


def dy01_deploy_antes_da_dependencia(ctx):
    """Release com item cuja dependência ainda aberta termina depois do deploy."""
    for release in ctx.releases:
        data_deploy = _data(release["data"])
        for chave in release["itens"]:
            item = ctx.itens.get(chave)
            if not item:
                continue
            for chave_dep in item["depende_de"]:
                dep = ctx.itens.get(chave_dep)
                if not dep or ctx.cancelado_(dep) or not ctx.aberto(dep):
                    continue
                fim_dep = _data(dep["fim"])
                if fim_dep is None or fim_dep > data_deploy:
                    quando = _br(fim_dep) if fim_dep else "sem data"
                    evid = (
                        f"Release {release['nome']} sobe em {_br(data_deploy)} com {chave}, "
                        f"que depende de {chave_dep} (fim {quando})"
                    )
                    yield _achado(ctx, "DY-01", [chave, chave_dep], evid,
                                  board=release["board"])


def rg01_campos_obrigatorios(ctx):
    """Épico aberto sem os campos que a PMO exige."""
    campos = ctx.regras["campos_obrigatorios_epico"]
    for item in ctx.itens.values():
        if item["tipo"] != "Epico" or ctx.cancelado_(item):
            continue
        faltando = [c for c in campos if item.get(c) in (None, "", [])]
        if faltando:
            evid = f"{item['chave']} {item['titulo']} sem: {', '.join(faltando)}"
            yield _achado(ctx, "RG-01", [item["chave"]], evid)


def al02_candidatos_bloqueio(ctx):
    """Comentário com palavra de bloqueio em item aberto e sem flag.

    É só um candidato: a triagem do Claude confirma ou descarta.
    """
    palavras = [p.lower() for p in ctx.regras["palavras_bloqueio"]]
    for item in ctx.itens.values():
        if item["flag"] or not ctx.aberto(item):
            continue
        for comentario in item["comentarios"]:
            texto = comentario["texto"].lower()
            if any(p in texto for p in palavras):
                evid = (
                    f"Comentário de {comentario['autor']} em "
                    f"{_br(_data(comentario['data']))}: \"{comentario['texto']}\"; "
                    f"item sem flag no Jira"
                )
                yield _achado(ctx, "AL-02", [item["chave"]], evid, origem="candidato")
                break


CHECAGENS = {
    "DT-01": dt01_vencidos,
    "DT-02": dt02_filho_depois_do_pai,
    "DP-01": dp01_dependencia_atrasada,
    "DP-02": dp02_dependencia_solta,
    "DP-03": dp03_ciclos,
    "DY-01": dy01_deploy_antes_da_dependencia,
    "RG-01": rg01_campos_obrigatorios,
    "AL-02": al02_candidatos_bloqueio,
}

ORDEM_SEVERIDADE = {"alta": 0, "media": 1, "baixa": 2}


def suprimidos(regras: dict, decisoes: list, hoje: date) -> set:
    """Ids que não devem voltar: exceções fixas, descartes e riscos aceitos ainda válidos."""
    ids = set(regras.get("excecoes") or [])
    for d in decisoes:
        if d.get("decisao") == "descartar":
            ids.add(d["id"])
        elif d.get("decisao") == "aceitar" and d.get("revisar_em"):
            if _data(d["revisar_em"]) > hoje:
                ids.add(d["id"])
    return ids


def rodar_checagens(snapshot: dict, regras: dict, decisoes: list | None = None) -> list:
    ctx = Contexto(snapshot, regras)
    ignorar = suprimidos(regras, decisoes or [], ctx.hoje)
    achados = []
    for codigo, funcao in CHECAGENS.items():
        if not regras["checagens"].get(codigo, {}).get("ativa", False):
            continue
        for achado in funcao(ctx):
            if achado["id"] not in ignorar:
                achados.append(achado)
    achados.sort(key=lambda a: (ORDEM_SEVERIDADE[a["severidade"]], a["codigo"], a["id"]))
    return achados


def comentarios_para_triagem(snapshot: dict, regras: dict) -> list:
    """Só os comentários de itens abertos: é o que a triagem lê."""
    ctx = Contexto(snapshot, regras)
    return [
        {
            "chave": i["chave"],
            "board": i["board"],
            "titulo": i["titulo"],
            "status": i["status"],
            "flag": i["flag"],
            "comentarios": i["comentarios"],
        }
        for i in ctx.itens.values()
        if i["comentarios"] and ctx.aberto(i)
    ]
