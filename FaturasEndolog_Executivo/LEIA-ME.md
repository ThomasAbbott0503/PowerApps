# FaturasEndolog_Executivo

Relatório **completo**: modelo de dados corrigido + layout executivo Abbott já montado (3 páginas, 1280×720).
Nenhum dado fica no GitHub: os dados vêm do SharePoint da Abbott quando você atualiza.

## Jeito mais simples: o arquivo .pbit (modelo do Power BI)
1. Baixe **`FaturasEndolog_Executivo.pbit`** e dê dois cliques (abre no Power BI Desktop).
2. Ele pede o parâmetro **pTaxaDolarPadrao** (deixe 5,5) e clica em **Carregar**.
3. Na primeira atualização:
   - SharePoint: **conta organizacional** (a mesma de sempre);
   - `olinda.bcb.gov.br` (dólar PTAX): **Anônimo**. Se a rede bloquear, o relatório usa 5,5 e funciona do mesmo jeito.
4. **Arquivo → Salvar como → .pbix** e publique como antes.

## Alternativa: o projeto .pbip (mesmo conteúdo, em arquivos de texto)
`Code → Download ZIP`, descompacte e abra `FaturasEndolog_Executivo.pbip`. Depois, **Atualizar**.

## O que está montado
- Cabeçalho Abbott com logo, **período selecionado** e **data da última atualização**.
- Filtros Ano / Mês / Filial / BU / Título e botão **R$ | US$** em todas as páginas.
- 4 cartões: Valor cobrado, Qtde de serviços, Preço médio por serviço, Variação vs mês anterior (▲ vermelho / ▼ verde).
- Evolução mensal por mês/ano (jan/26, fev/26…), participação por filial, valor por título, preço médio por tipo, valor por filial e tabela de detalhe.
- Cost Drive: total consolidado, peso Endolog, acumulado no ano, matrizes Endolog e LOGMED e gráfico mensal dos dois.

## Correções nos dados (já aplicadas no modelo)
- Dólar pelo **PTAX médio mensal** do Banco Central (antes era 5,5 fixo).
- Valores digitados como texto na Faturas_LOGMED ("R$ 5.130,00", "0,10%") viram número (antes viravam erro e sumiam: setembro).
- Meses escritos errado ("SETEMBRO", "JULHO", "Jeneiro") padronizados.
- Calendário com mês **e** ano; filiais automáticas; preço médio em vez de soma de preço.
- As páginas "Saídas Logmed" e "validações" ficaram de fora (tabelas inexistentes no modelo e dados de pacientes). Continuam no `FaturasEndolog.pbix` original.

## Conferência depois da primeira atualização
- LOGMED, Ano 2026, sem filtro de BU: **Setembro = R$ 365.835,96**, **Outubro = R$ 367.487,68**.
- Se setembro ainda não aparecer, o arquivo **Faturas_LOGMED.xlsx do SharePoint** não tem as linhas de set/out de 2026 (a "Cópia…xlsm" tem).
