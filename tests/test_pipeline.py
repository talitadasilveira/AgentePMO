"""O pipeline sem IA roda de ponta a ponta e a triagem é aplicada como esperado."""

import json

from pmo import analise, dashboard, triagem
from pmo.__main__ import executar
from pmo.checagens import carregar_regras, rodar_checagens
from pmo.coleta import coletar
from pmo.ia import extrair_json


def test_pipeline_sem_ia_gera_os_arquivos(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    execucao = executar("exemplo", com_ia=False, pasta=tmp_path)
    for nome in ("snapshot.json", "achados.json", "dashboard.html", "relatorio.md"):
        assert (tmp_path / nome).exists()
    html = (tmp_path / "dashboard.html").read_text(encoding="utf-8")
    assert "DY-01:PAG-412+TIG-188" in html
    assert all(a["recomendacao"] for a in execucao["achados"])
    assert execucao["custo"]["total_usd"] == 0


def test_triagem_descarta_ruido_e_acrescenta_conflito():
    snapshot, regras = coletar("exemplo"), carregar_regras()
    achados = rodar_checagens(snapshot, regras)
    leitura = {
        "itens": [{"chave": "PAG-377", "classificacao": "ruido", "resumo": "nada"}],
        "conflitos": [{"itens": ["PAG-405", "TIG-190"], "descricao": "R$ 1.000 x R$ 500 por dia"}],
    }
    ids = {a["id"] for a in triagem.aplicar_triagem(achados, leitura, snapshot, regras)}
    assert "AL-02:PAG-377" not in ids
    assert "AL-01:PAG-405+TIG-190" in ids


def test_combinar_aceita_severidade_do_modelo_e_ignora_valor_invalido():
    achados = [
        {"id": "RG-01:X", "codigo": "RG-01", "severidade": "baixa"},
        {"id": "DT-01:Y", "codigo": "DT-01", "severidade": "alta"},
    ]
    resultado = {"achados": [
        {"id": "RG-01:X", "severidade": "alta", "recomendacao": "Completar já"},
        {"id": "DT-01:Y", "severidade": "urgente"},
    ]}
    por_id = {a["id"]: a for a in analise.combinar(achados, resultado)}
    assert por_id["RG-01:X"]["severidade"] == "alta"
    assert por_id["DT-01:Y"]["severidade"] == "alta"
    assert por_id["DT-01:Y"]["recomendacao"] == analise.PADRAO["DT-01"]


def test_extrair_json_aceita_bloco_de_codigo():
    assert extrair_json('Segue:\n```json\n{"a": 1}\n```') == {"a": 1}
    assert extrair_json('texto antes {"b": [1, 2]} texto depois') == {"b": [1, 2]}


def test_html_nao_quebra_com_fechamento_de_script():
    execucao = {"gerado_em": "x", "fonte": "exemplo", "com_ia": False, "resumo": ["</script>"],
                "achados": [], "custo": {"total_usd": 0, "etapas": []}}
    html = dashboard.gerar_html(execucao)
    assert html.count("</script>") == 1
    json.loads(html.split("const EXEC = ")[1].split(";\nconst CHAVE")[0].replace("<\\/", "</"))
