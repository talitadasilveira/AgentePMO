# Processo da PMO (exemplo fictício)

> Este texto vai no prompt do agente, em cache. É um exemplo: troque pelo processo real da área,
> sempre curto (1 a 2 páginas). O que for regra objetiva vai em `config/regras.yaml`, não aqui.

## Times e boards
- **PAG (Pagamentos):** backend de pagamentos, conciliação e integração com parceiros bancários.
- **TIG (App):** aplicativo e telas; depende do PAG para tudo que envolve valores e limites.
- Dependência entre os dois times precisa estar no Jira com responsável e data dos dois lados.

## Cadência
- Sprints de 2 semanas, começando na segunda-feira.
- Releases do PAG a cada 2 semanas, na quinta-feira; releases do App na sexta-feira da mesma semana.
- Nenhum deploy em produção na semana de virada de mês sem aprovação do PMO.

## Definições
- **DoR:** história só entra na sprint com critério de aceite, estimativa e dependências mapeadas.
- **DoD:** código revisado, testado em homologação e com o PO de acordo.
- **Spike:** épico de investigação, de até 1 sprint. Não precisa de estimativa em pontos nem de DoD.
- **Parceiro bancário:** liberações de ambiente e credenciais do parceiro levam de 3 a 5 dias úteis;
  comentário "aguardando parceiro" é bloqueio real e deve ter flag.

## O que é aceitável
- Atraso de até 2 dias úteis em história, sem impacto em release, é risco baixo.
- Dependência entre times que termina depois do item dependente é sempre risco alto, mesmo de 1 dia.
- Subir funcionalidade desligada (feature flag) antes da dependência é aceito, se registrado no épico.

## Quem decide
- Datas e escopo de épico: PO do time.
- Conflito de regra de negócio entre times: Produto, com o PMO mediando.
- Mudança de data de release: PMO, avisando os dois times.
