# Agente PMO — POC

Pipeline que lê iniciativas e épicos do Jira, cruza datas, dependências e deploys **em código**, usa o
**Claude** só para interpretar comentários e redigir a análise, e entrega um **dashboard** para a área de
projetos revisar cada achado antes de qualquer ação (human in the loop).

> Este repositório é público: roda **só com dados fictícios** (`dados/exemplo/jira.json`). Dado real do
> Jira entra apenas na fase 4, depois da aprovação de Segurança, em repositório da empresa.

## Como funciona

| # | Etapa | Quem faz | Arquivo |
| --- | --- | --- | --- |
| 1 | Coleta | Python | `pmo/coleta.py` |
| 2 | Checagens (datas, dependências, deploys, regras) | Python | `pmo/checagens.py` |
| 3 | Triagem dos comentários | Claude Haiku 5.5 | `pmo/triagem.py` |
| 4 | Análise: severidade, recomendação, resumo | Claude Opus 5.5 | `pmo/analise.py` |
| 5 | Dashboard de revisão + relatório | Python | `pmo/dashboard.py` |
| 6 | Revisão humana | Área de projetos | `dados/decisoes.json` |

Checagens: `DT-01` vencido e aberto · `DT-02` história além do épico · `DP-01` dependência termina depois ·
`DP-02` dependência solta · `DP-03` ciclo · `DY-01` deploy antes da dependência · `RG-01` campos obrigatórios ·
`AL-02` bloqueio em comentário sem flag · `AL-01` mesma regra descrita de forma diferente (vem da triagem).

As regras ficam em `config/regras.yaml` e podem ser editadas sem mexer no código.

## Rodar (sem instalar nada no PC)

Tudo roda no **GitHub Actions**:

1. Aba **Actions** → **Agente PMO** → **Run workflow**. Também roda a cada push na `main` e toda segunda às 07h.
2. Ao terminar, o resumo aparece na própria execução e o dashboard fica em **Artifacts → dashboard-pmo**
   (baixe, descompacte e abra `dashboard.html` no navegador).

Sem chave da API o pipeline roda **sem IA** (checagens + recomendações padrão, custo zero).
Para ligar o Claude: **Settings → Secrets and variables → Actions → New repository secret**,
nome `ANTHROPIC_API_KEY`, valor = sua chave da API (console.anthropic.com).

## Revisão humana

1. No dashboard, escolha uma decisão por achado: **Aprovar**, **Ajustar**, **Descartar** ou **Aceitar risco**
   (com data de revisão).
2. Clique em **Baixar decisões** e salve o conteúdo em `dados/decisoes.json` (dá para editar pelo próprio GitHub).
3. Na próxima execução, descartes somem e riscos aceitos só voltam depois da data de revisão.

## Custo

Cada execução registra tokens e custo por etapa no relatório. Estimativa com ~200 épicos: perto de US$ 0,40.
