"""Chamadas ao Claude, com medição de tokens e custo de cada execução."""

import json
import os
import re

MODELO_TRIAGEM = "claude-haiku-5-5"
MODELO_ANALISE = "claude-opus-5-5"

# US$ por milhão de tokens (entrada, saída), preços de tabela da API.
PRECOS = {
    MODELO_TRIAGEM: (0.10, 0.50),
    MODELO_ANALISE: (4.00, 20.00),
}


def ia_disponivel() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


class Medidor:
    """Soma tokens e custo por etapa, para o relatório da execução."""

    def __init__(self):
        self.etapas = []

    def registrar(self, etapa: str, modelo: str, usage) -> None:
        entrada = usage.input_tokens + (getattr(usage, "cache_read_input_tokens", 0) or 0) \
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
        saida = usage.output_tokens
        preco_in, preco_out = PRECOS[modelo]
        custo = entrada / 1e6 * preco_in + saida / 1e6 * preco_out
        self.etapas.append({
            "etapa": etapa, "modelo": modelo,
            "tokens_entrada": entrada, "tokens_saida": saida,
            "custo_usd": round(custo, 4),
        })

    @property
    def total_usd(self) -> float:
        return round(sum(e["custo_usd"] for e in self.etapas), 4)


def _cliente():
    import anthropic
    return anthropic.Anthropic()


def _texto(resposta) -> str:
    return "".join(b.text for b in resposta.content if b.type == "text")


def extrair_json(texto: str):
    """Lê o primeiro objeto JSON da resposta (aceita bloco ```json)."""
    bloco = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texto, re.S)
    bruto = bloco.group(1) if bloco else texto[texto.find("{"): texto.rfind("}") + 1]
    return json.loads(bruto)


def perguntar(etapa: str, modelo: str, sistema: str, conteudo: str,
              medidor: Medidor, esforco: str, max_tokens: int) -> dict:
    """Uma chamada ao Claude que deve devolver JSON. Instruções fixas ficam em cache."""
    cliente = _cliente()
    parametros = dict(
        model=modelo,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": esforco},
        messages=[{"role": "user", "content": conteudo}],
    )
    if modelo == MODELO_ANALISE:
        # Se o modelo recusar por política, a API refaz no modelo de fallback.
        resposta = cliente.beta.messages.create(
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
            **parametros,
        )
    else:
        resposta = cliente.messages.create(**parametros)
    medidor.registrar(etapa, modelo, resposta.usage)
    if resposta.stop_reason == "refusal":
        raise RuntimeError(f"{etapa}: o modelo recusou a solicitação")
    if resposta.stop_reason == "max_tokens":
        raise RuntimeError(f"{etapa}: resposta cortada no limite de tokens")
    return extrair_json(_texto(resposta))
