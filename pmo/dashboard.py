"""Etapa 5 — dashboard de revisão (HTML estático, um arquivo só) e relatório em Markdown.

O revisor registra uma decisão por achado; as decisões ficam no navegador e saem
pelo botão "Baixar decisões" como decisoes-AAAA-MM-DD.json, que vai para dados/decisoes/
e alimenta a próxima execução (supressões, exemplos para a análise e calibragem).
"""

import json
from datetime import datetime, timezone

ROTULO_SEV = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}


def gerar_html(execucao: dict) -> str:
    dados = json.dumps(execucao, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DADOS__", dados)


def gerar_markdown(execucao: dict) -> str:
    linhas = [
        f"# Agente PMO — execução de {execucao['gerado_em']}",
        "",
        f"Fonte: **{execucao['fonte']}** · IA: **{'sim' if execucao['com_ia'] else 'não'}** · "
        f"Custo: **US$ {execucao['custo']['total_usd']:.4f}**",
        "",
        "## Resumo",
        "",
    ]
    linhas += [f"- {frase}" for frase in execucao["resumo"]]
    linhas += ["", "## Achados", "", "| Severidade | Código | Itens | Evidência |", "| --- | --- | --- | --- |"]
    for a in execucao["achados"]:
        evid = a["evidencia"].replace("|", "/")
        linhas.append(f"| {ROTULO_SEV[a['severidade']]} | {a['codigo']} | {', '.join(a['itens'])} | {evid} |")
    if execucao.get("calibragem"):
        linhas += ["", "## Calibragem das checagens", "",
                   "Decisões anteriores da área de projetos, por tipo de checagem.", "",
                   "| Código | Checagem | Decididos | Descartados | Taxa de descarte | |", "| --- | --- | --- | --- | --- | --- |"]
        for c in execucao["calibragem"]:
            alerta = "Revisar a regra" if c["calibrar"] else ""
            linhas.append(f"| {c['codigo']} | {c['titulo']} | {c['decididos']} | {c['descartados']} | {c['taxa']:.0%} | {alerta} |")
    if execucao["custo"]["etapas"]:
        linhas += ["", "## Tokens", "", "| Etapa | Modelo | Entrada | Saída | US$ |", "| --- | --- | --- | --- | --- |"]
        for e in execucao["custo"]["etapas"]:
            linhas.append(
                f"| {e['etapa']} | {e['modelo']} | {e['tokens_entrada']} | {e['tokens_saida']} | {e['custo_usd']:.4f} |"
            )
    return "\n".join(linhas) + "\n"


def agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agente PMO — revisão dos achados</title>
<style>
:root{--roxo:#540ccb;--roxo-escuro:#372061;--roxo-suave:#f2ebfc;--cta:#f23ce6;--texto:#1f0d3d;--cinza:#5f5f89;
--borda:#e4e3ff;--borda-forte:#aea4ff;--fundo:#fafaff;--branco:#fff;--erro:#c0172d;--erro-bg:#ffe5e8;
--aviso:#625200;--aviso-bg:#fdeb8e;--ok:#00635d;--ok-bg:#cbf4ef;--sutil:#f4f4fa}
*{box-sizing:border-box}
body{margin:0;background:var(--fundo);color:var(--texto);font-family:"Sofia Pro",system-ui,-apple-system,"Segoe UI",sans-serif}
header{background:var(--roxo-escuro);color:#fff}
.wrap{max-width:1200px;margin:0 auto;padding:20px 24px}
.topo{display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#e1c4ff}
.titulo{font-size:24px;font-weight:800;margin:4px 0 0}
.meta{font-size:14px;color:#e1c4ff}
.pill{display:inline-block;padding:4px 12px;border-radius:9999px;font-size:12px;font-weight:700}
.alta{background:var(--erro-bg);color:var(--erro)}.media{background:var(--aviso-bg);color:var(--aviso)}.baixa{background:var(--sutil);color:#484869}
main.wrap{display:flex;flex-direction:column;gap:24px;padding-top:32px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}
.card{background:var(--branco);border-radius:16px;box-shadow:0 4px 6px -2px rgba(16,24,40,.03),0 12px 16px -4px rgba(16,24,40,.08);padding:24px}
.kpi span{display:block;font-size:14px;color:var(--cinza)}.kpi strong{font-size:36px;font-weight:900}
h2{margin:0 0 12px;font-size:20px}
.filtros{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}
button{font:inherit;font-size:14px;font-weight:700;border-radius:9999px;padding:8px 18px;min-height:44px;cursor:pointer;border:2px solid var(--borda-forte);background:var(--branco);color:var(--texto)}
button[aria-pressed=true]{background:var(--roxo);border-color:var(--roxo);color:#fff;box-shadow:inset 0 -4px 0 0 rgba(0,0,0,.2)}
button.cta{background:var(--cta);border-color:var(--cta);color:#fff;box-shadow:inset 0 -4px 0 0 rgba(0,0,0,.2)}
.achado{display:flex;flex-direction:column;gap:14px}
.linha{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.codigo{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:var(--cinza)}
.board{border:1px solid var(--borda);color:var(--roxo)}
.achado h3{margin:0;font-size:20px}
.rotulo{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--cinza)}
.reco{background:var(--roxo-suave);border-radius:12px;padding:16px}.reco .rotulo{color:var(--roxo)}
.decisao{border-top:1px solid var(--borda);padding-top:14px;display:flex;flex-direction:column;gap:12px}
.campos{display:flex;flex-wrap:wrap;gap:12px}
label{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:700;color:var(--cinza);flex:1 1 180px}
input{font:inherit;font-size:14px;padding:10px 16px;border-radius:9999px;border:2px solid var(--borda);color:var(--texto)}
.registrada{font-size:14px;font-weight:700;color:var(--ok)}
p{margin:0;line-height:1.5}
ul{margin:0;padding-left:20px;line-height:1.5}
.aviso{background:var(--roxo-suave);border-radius:12px;padding:12px 16px;font-size:14px}
.rolagem{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--borda);white-space:nowrap}
th{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--cinza)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.barra{display:inline-block;width:80px;height:8px;border-radius:9999px;background:var(--sutil);vertical-align:middle;margin-right:8px;overflow:hidden}
.barra i{display:block;height:100%;background:var(--roxo)}
.barra i.alerta{background:var(--erro)}
</style>
</head>
<body>
<header><div class="wrap topo">
<div><div class="eyebrow">Agente PMO</div><p class="titulo">Saúde do portfólio · PAG e TIG</p></div>
<div class="linha"><span class="meta" id="meta"></span><span class="pill" style="background:#fdeb8e;color:#625200">Aguardando revisão</span></div>
</div></header>
<main class="wrap">
<p class="aviso" id="aviso"></p>
<section class="kpis" aria-label="Resumo em números">
<div class="card kpi"><span>Achados</span><strong id="k-total"></strong></div>
<div class="card kpi"><span>Severidade alta</span><strong id="k-altas" style="color:var(--erro)"></strong></div>
<div class="card kpi"><span>Revisados</span><strong id="k-rev" style="color:var(--roxo)"></strong></div>
<div class="card kpi"><span>Custo da execução</span><strong id="k-custo"></strong></div>
</section>
<section class="card" aria-labelledby="t-resumo"><h2 id="t-resumo">Resumo do agente</h2><ul id="resumo"></ul></section>
<section class="card" aria-labelledby="t-calib" id="calib" hidden><h2 id="t-calib">Calibragem das checagens</h2>
<p style="color:var(--cinza);font-size:14px;margin-bottom:12px">Quanto das revisões anteriores a área descartou, por checagem. Taxa alta indica regra a revisar em config/regras.yaml.</p>
<div class="rolagem"><table><thead><tr><th>Checagem</th><th class="num">Decididos</th><th class="num">Descartados</th><th>Taxa de descarte</th><th></th></tr></thead><tbody id="calib-linhas"></tbody></table></div></section>
<section aria-labelledby="t-achados" style="display:flex;flex-direction:column;gap:16px">
<div class="filtros"><h2 id="t-achados" style="margin:0">Achados para revisar</h2>
<div class="linha" role="group" aria-label="Filtrar por severidade" id="filtros"></div></div>
<div id="lista" style="display:flex;flex-direction:column;gap:16px"></div>
</section>
<div class="linha"><button type="button" class="cta" id="baixar">Baixar decisões</button>
<span class="meta" style="color:var(--cinza)">Suba o arquivo na pasta dados/decisoes/ do repositório para a próxima execução levar as decisões em conta.</span></div>
</main>
<script>
const EXEC = __DADOS__;
const CHAVE = "agente-pmo-decisoes:" + EXEC.gerado_em;
const OPCOES = [["aprovar","Aprovar"],["ajustar","Ajustar"],["descartar","Descartar"],["aceitar","Aceitar risco"]];
const SEV = {alta:"Alta", media:"Média", baixa:"Baixa"};
let decisoes = {};
try { decisoes = JSON.parse(localStorage.getItem(CHAVE) || "{}"); } catch (e) { decisoes = {}; }
let filtro = "todas";

function salvar(){ try { localStorage.setItem(CHAVE, JSON.stringify(decisoes)); } catch (e) {} }
function el(tag, props, filhos){
  const n = document.createElement(tag);
  Object.entries(props || {}).forEach(([k, v]) => { if (k === "text") n.textContent = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v); });
  (filhos || []).forEach(f => n.appendChild(f));
  return n;
}
function bloco(rotulo, texto){ return el("div", {}, [el("div", {class:"rotulo", text:rotulo}), el("p", {text:texto})]); }
function campo(a, nome, rotulo, tipo){
  const d = decisoes[a.id] || {};
  const input = el("input", {type:tipo, value:d[nome] || "", oninput:e => { decisoes[a.id] = {...(decisoes[a.id] || {}), [nome]: e.target.value}; salvar(); }});
  return el("label", {}, [document.createTextNode(rotulo), input]);
}

function render(){
  document.getElementById("meta").textContent = "Execução de " + EXEC.gerado_em + " · fonte " + EXEC.fonte;
  document.getElementById("aviso").textContent = EXEC.fonte === "exemplo" ? "Dados fictícios do Jira de exemplo." + (EXEC.com_ia ? "" : " Rodou sem IA: recomendações padrão.") : "";
  const total = EXEC.achados.length;
  const rev = EXEC.achados.filter(a => decisoes[a.id] && decisoes[a.id].decisao).length;
  document.getElementById("k-total").textContent = total;
  document.getElementById("k-altas").textContent = EXEC.achados.filter(a => a.severidade === "alta").length;
  document.getElementById("k-rev").textContent = rev + " de " + total;
  document.getElementById("k-custo").textContent = "US$ " + EXEC.custo.total_usd.toFixed(2);
  const ul = document.getElementById("resumo"); ul.replaceChildren(...EXEC.resumo.map(f => el("li", {text:f})));
  const calib = EXEC.calibragem || [];
  document.getElementById("calib").hidden = !calib.length;
  document.getElementById("calib-linhas").replaceChildren(...calib.map(c => {
    const barra = el("span", {class:"barra"}, [el("i", {class:c.calibrar ? "alerta" : "", style:"width:" + Math.round(c.taxa * 100) + "%"})]);
    return el("tr", {}, [
      el("td", {}, [el("span", {class:"codigo", text:c.codigo + " "}), document.createTextNode(c.titulo)]),
      el("td", {class:"num", text:String(c.decididos)}),
      el("td", {class:"num", text:String(c.descartados)}),
      el("td", {}, [barra, document.createTextNode(Math.round(c.taxa * 100) + "%")]),
      el("td", {}, c.calibrar ? [el("span", {class:"pill alta", text:"Revisar a regra"})] : []),
    ]);
  }));

  const filtros = document.getElementById("filtros");
  filtros.replaceChildren(...[["todas","Todas"],["alta","Alta"],["media","Média"],["baixa","Baixa"]].map(([k, r]) =>
    el("button", {type:"button", "aria-pressed": String(filtro === k), text:r, onclick:() => { filtro = k; render(); }})));

  const lista = document.getElementById("lista");
  const visiveis = EXEC.achados.filter(a => filtro === "todas" || a.severidade === filtro);
  lista.replaceChildren(...visiveis.map(a => {
    const d = decisoes[a.id] || {};
    const botoes = OPCOES.map(([k, r]) => el("button", {type:"button", "aria-pressed": String(d.decisao === k), text:r,
      onclick:() => { decisoes[a.id] = {...(decisoes[a.id] || {}), decisao:k, em:new Date().toISOString()}; salvar(); render(); }}));
    const filhos = [
      el("div", {class:"linha"}, [el("span", {class:"pill " + a.severidade, text:SEV[a.severidade]}), el("span", {class:"codigo", text:a.codigo}), el("span", {class:"pill board", text:a.board})]),
      el("h3", {text:a.titulo}),
      bloco("Itens envolvidos", a.itens.join(", ")),
      bloco("Evidência", a.evidencia),
    ];
    if (a.leitura_ia) filhos.push(bloco("Leitura dos comentários", a.leitura_ia));
    const reco = el("div", {class:"reco"}, [el("div", {class:"rotulo", text:"Recomendação do agente"}), el("p", {text:a.recomendacao})]);
    if (a.impacto) reco.appendChild(el("p", {text:"Se nada for feito: " + a.impacto}));
    filhos.push(reco);
    const dec = [el("div", {class:"linha"}, [el("strong", {text:"Decisão"}), ...botoes])];
    if (d.decisao) dec.push(el("span", {class:"registrada", text:"Decisão registrada: " + OPCOES.find(o => o[0] === d.decisao)[1]}));
    dec.push(el("div", {class:"campos"}, [campo(a, "comentario", "Comentário para o time", "text"), campo(a, "responsavel", "Responsável", "text"), campo(a, "revisar_em", "Prazo ou data de revisão", "date")]));
    filhos.push(el("div", {class:"decisao"}, dec));
    return el("article", {class:"card achado"}, filhos);
  }));
}

document.getElementById("baixar").addEventListener("click", () => {
  // Leva junto o contexto do achado: o histórico precisa se explicar sozinho para virar exemplo.
  const porId = Object.fromEntries(EXEC.achados.map(a => [a.id, a]));
  const saida = Object.entries(decisoes).filter(([, d]) => d.decisao).map(([id, d]) => {
    const x = porId[id] || {};
    return {id, codigo:x.codigo, titulo:x.titulo, evidencia:x.evidencia, recomendacao:x.recomendacao, execucao:EXEC.gerado_em, ...d};
  });
  const blob = new Blob([JSON.stringify(saida, null, 2)], {type:"application/json"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "decisoes-" + EXEC.gerado_em.slice(0, 10) + ".json"; a.click();
});
render();
</script>
</body>
</html>
"""
