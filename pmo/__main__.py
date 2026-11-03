"""Roda o pipeline inteiro: python -m pmo [--fonte exemplo] [--sem-ia] [--saida saida]"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from . import analise, aprendizado, checagens, coleta, dashboard, triagem
from .ia import Medidor, ia_disponivel

RAIZ = Path(__file__).resolve().parent.parent


def executar(fonte: str, com_ia: bool, pasta: Path) -> dict:
    medidor = Medidor()
    snapshot = coleta.coletar(fonte)
    regras = checagens.carregar_regras()
    decisoes = aprendizado.carregar_decisoes()
    processo = aprendizado.carregar_processo()
    achados = checagens.rodar_checagens(snapshot, regras, decisoes)
    print(f"[checagens] {len(achados)} achados em código; {len(decisoes)} decisões anteriores")

    erro_ia = None
    if com_ia:
        try:
            leitura = triagem.triar(checagens.comentarios_para_triagem(snapshot, regras), medidor, processo)
            achados = triagem.aplicar_triagem(achados, leitura, snapshot, regras)
            print(f"[triagem] {len(leitura.get('conflitos', []))} conflitos; {len(achados)} achados após a triagem")
            exemplos = aprendizado.exemplos(decisoes, achados)
            print(f"[analise] {len(exemplos)} decisões anteriores enviadas como exemplo")
            resultado = analise.analisar(achados, medidor, processo, exemplos)
        except Exception as e:  # falha da API não pode impedir o dashboard
            erro_ia = re.sub(r"sk-ant-[\w-]+", "sk-ant-***", f"{type(e).__name__}: {e}")[:600]
            print(f"[ia] falhou, seguindo sem IA: {erro_ia}")
            com_ia = False
            resultado = analise.analise_padrao(achados)
    else:
        print("[ia] sem ANTHROPIC_API_KEY: pulando triagem e análise")
        resultado = analise.analise_padrao(achados)
    achados = analise.combinar(achados, resultado)

    execucao = {
        "gerado_em": dashboard.agora(),
        "fonte": fonte,
        "data_referencia": snapshot["data_referencia"],
        "com_ia": com_ia,
        "resumo": resultado.get("resumo", []),
        "achados": achados,
        "calibragem": aprendizado.taxa_descarte(decisoes, regras),
        "custo": {"total_usd": medidor.total_usd, "etapas": medidor.etapas},
    }

    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    (pasta / "achados.json").write_text(json.dumps(execucao, ensure_ascii=False, indent=1), encoding="utf-8")
    (pasta / "dashboard.html").write_text(dashboard.gerar_html(execucao), encoding="utf-8")
    relatorio = dashboard.gerar_markdown(execucao)
    (pasta / "relatorio.md").write_text(relatorio, encoding="utf-8")

    resumo_job = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo_job:
        with open(resumo_job, "a", encoding="utf-8") as f:
            f.write(relatorio)

    print(f"[ok] {len(achados)} achados · custo US$ {medidor.total_usd:.4f} · arquivos em {pasta}")
    if os.environ.get("GITHUB_ACTIONS"):
        # Aviso visível na página da execução (os logs exigem login); nunca mostra a chave.
        if erro_ia:
            print(f"::error title=Agente PMO - falha na IA::{erro_ia.replace(chr(10), ' ')}")
        else:
            modo = "com IA" if com_ia else "sem IA (secret ANTHROPIC_API_KEY não encontrado ou --sem-ia)"
            print(f"::notice title=Agente PMO::{len(achados)} achados, {modo}, custo US$ {medidor.total_usd:.4f}")
    execucao["erro_ia"] = erro_ia
    return execucao


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pmo", description="Agente PMO")
    parser.add_argument("--fonte", default="exemplo", choices=["exemplo", "jira"])
    parser.add_argument("--sem-ia", action="store_true", help="não chama o Claude")
    parser.add_argument("--saida", default=str(RAIZ / "saida"))
    args = parser.parse_args(argv)
    execucao = executar(args.fonte, ia_disponivel() and not args.sem_ia, Path(args.saida))
    return 1 if execucao["erro_ia"] else 0


if __name__ == "__main__":
    sys.exit(main())
