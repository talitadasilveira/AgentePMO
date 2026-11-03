"""Processo, decisões anteriores como exemplos e taxa de descarte por checagem."""

import json

from pmo import aprendizado
from pmo.analise import com_processo
from pmo.checagens import carregar_regras


def _salvar(pasta, nome, decisoes):
    pasta.mkdir(exist_ok=True)
    (pasta / nome).write_text(json.dumps(decisoes), encoding="utf-8")


def test_historico_ficticio_marca_rg01_para_calibrar():
    decisoes = aprendizado.carregar_decisoes()
    linhas = {c["codigo"]: c for c in aprendizado.taxa_descarte(decisoes, carregar_regras())}
    assert linhas["RG-01"] == {**linhas["RG-01"], "decididos": 4, "descartados": 3, "taxa": 0.75, "calibrar": True}
    assert not linhas["DP-01"]["calibrar"]
    assert linhas["AL-02"]["taxa"] == 0.5 and not linhas["AL-02"]["calibrar"]  # poucas decisões ainda


def test_decisao_mais_recente_vale_para_o_mesmo_achado(tmp_path):
    _salvar(tmp_path, "a.json", [{"id": "DT-01:X-1", "decisao": "aprovar", "em": "2026-10-01"}])
    _salvar(tmp_path, "b.json", [{"id": "DT-01:X-1", "decisao": "descartar", "em": "2026-10-08"}])
    decisoes = aprendizado.carregar_decisoes(tmp_path)
    assert [d["decisao"] for d in decisoes] == ["descartar"]


def test_pasta_vazia_ou_ausente(tmp_path):
    assert aprendizado.carregar_decisoes(tmp_path / "nao-existe") == []
    assert aprendizado.taxa_descarte([], carregar_regras()) == []


def test_exemplos_so_dos_codigos_da_execucao_e_com_comentario():
    decisoes = [
        {"id": "RG-01:A", "decisao": "descartar", "comentario": "spike", "em": "1"},
        {"id": "RG-01:B", "decisao": "aprovar", "em": "2"},
        {"id": "DP-01:C", "decisao": "aprovar", "comentario": "ok", "em": "3"},
        {"id": "RG-01:D", "decisao": "descartar", "comentario": "spike de novo", "em": "4"},
    ]
    achados = [{"codigo": "RG-01"}]
    exemplos = aprendizado.exemplos(decisoes, achados, por_codigo=1)
    assert exemplos == [{"codigo": "RG-01", "decisao": "descartar", "comentario": "spike de novo"}]


def test_processo_entra_no_prompt_de_sistema():
    processo = aprendizado.carregar_processo()
    assert "Spike" in processo
    assert com_processo("BASE", processo).startswith("BASE\n\nProcesso da área")
    assert com_processo("BASE", "") == "BASE"
