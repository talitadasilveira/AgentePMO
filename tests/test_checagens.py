"""Cada problema plantado no Jira fictício precisa ser encontrado, e nada além deles."""

import copy

import pytest

from pmo.checagens import carregar_regras, rodar_checagens
from pmo.coleta import coletar


@pytest.fixture
def snapshot():
    return coletar("exemplo")


@pytest.fixture
def regras():
    return carregar_regras()


ESPERADOS = {
    "DT-01:TIG-150",
    "DT-02:TIG-152+TIG-150",
    "DP-01:PAG-412+TIG-188",
    "DP-01:TIG-201+PAG-398",
    "DP-02:TIG-190+PAG-399",
    "DP-03:PAG-430+TIG-195",
    "DY-01:PAG-412+TIG-188",
    "RG-01:PAG-420",
    "AL-02:PAG-377",
}


def test_encontra_todos_os_problemas_plantados(snapshot, regras):
    ids = {a["id"] for a in rodar_checagens(snapshot, regras)}
    assert ids == ESPERADOS


def test_achados_ordenados_por_severidade(snapshot, regras):
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    sev = [ordem[a["severidade"]] for a in rodar_checagens(snapshot, regras)]
    assert sev == sorted(sev)


def test_evidencia_traz_datas_e_folga(snapshot, regras):
    achados = {a["id"]: a for a in rodar_checagens(snapshot, regras)}
    evid = achados["DP-01:PAG-412+TIG-188"]["evidencia"]
    assert "12/11/2026" in evid and "18/11/2026" in evid and "6 dias" in evid


def test_dependencia_cancelada_explica_o_motivo(snapshot, regras):
    achados = {a["id"]: a for a in rodar_checagens(snapshot, regras)}
    assert "cancelada" in achados["DP-02:TIG-190+PAG-399"]["evidencia"]


def test_bloqueio_em_comentario_e_so_candidato(snapshot, regras):
    achados = {a["id"]: a for a in rodar_checagens(snapshot, regras)}
    assert achados["AL-02:PAG-377"]["origem"] == "candidato"


def test_descarte_suprime_o_achado(snapshot, regras):
    decisoes = [{"id": "RG-01:PAG-420", "decisao": "descartar"}]
    ids = {a["id"] for a in rodar_checagens(snapshot, regras, decisoes)}
    assert "RG-01:PAG-420" not in ids


def test_risco_aceito_volta_depois_da_data(snapshot, regras):
    ainda_valido = [{"id": "DT-01:TIG-150", "decisao": "aceitar", "revisar_em": "2026-11-30"}]
    vencido = [{"id": "DT-01:TIG-150", "decisao": "aceitar", "revisar_em": "2026-11-01"}]
    assert "DT-01:TIG-150" not in {a["id"] for a in rodar_checagens(snapshot, regras, ainda_valido)}
    assert "DT-01:TIG-150" in {a["id"] for a in rodar_checagens(snapshot, regras, vencido)}


def test_checagem_desativada_nao_roda(snapshot, regras):
    regras = copy.deepcopy(regras)
    regras["checagens"]["RG-01"]["ativa"] = False
    assert not any(a["codigo"] == "RG-01" for a in rodar_checagens(snapshot, regras))


def test_item_concluido_nao_gera_atraso(snapshot, regras):
    snapshot = copy.deepcopy(snapshot)
    for item in snapshot["itens"]:
        if item["chave"] == "TIG-150":
            item["status"] = "Concluído"
    ids = {a["id"] for a in rodar_checagens(snapshot, regras)}
    assert "DT-01:TIG-150" not in ids
