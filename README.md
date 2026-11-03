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
| 6 | Revisão humana | Área de projetos | `dados/decisoes/` |

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
   Escreva o motivo no comentário: é ele que ensina o agente.
2. Clique em **Baixar decisões** (gera `decisoes-AAAA-MM-DD.json`) e suba o arquivo na pasta `dados/decisoes/`
   pelo GitHub (**Add file → Upload files**). Um arquivo por revisão; o histórico vai se acumulando.
3. Na próxima execução, descartes somem e riscos aceitos só voltam depois da data de revisão.

## Como o agente aprende o processo

Sem treinar o modelo, em quatro camadas:

1. **Regras objetivas** em `config/regras.yaml`: checagens em código, custo zero.
2. **Processo da área** em `config/processo.md`: glossário, cadência, o que é aceitável e quem decide.
   Vai no prompt de sistema da triagem e da análise, em cache. Mantenha em 1 a 2 páginas.
3. **Decisões anteriores como exemplos:** para cada tipo de achado da execução, as 3 decisões mais recentes
   com comentário vão para a análise, que passa a recomendar com o mesmo critério da área.
4. **Calibragem:** o relatório e o dashboard mostram a taxa de descarte por checagem. Com pelo menos
   3 decisões e 50% ou mais de descartes (ajustável em `calibragem`), a checagem é marcada para revisar a regra.

Os arquivos de `config/processo.md` e `dados/decisoes/` deste repositório são **fictícios**.

## Custo

Cada execução registra tokens e custo por etapa no relatório. Estimativa com ~200 épicos: perto de US$ 0,40.
