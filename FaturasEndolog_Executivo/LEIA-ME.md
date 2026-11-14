# FaturasEndolog_Executivo (Projeto do Power BI – .pbip)

Relatório **completo**: modelo de dados corrigido + visual executivo Abbott já montado.
O projeto não carrega dados (eles ficam no SharePoint da Abbott), por isso é leve e seguro.

## Como abrir (máquina da empresa)
1. Baixe esta pasta inteira (`Code → Download ZIP` no GitHub) e descompacte.
2. Abra **`FaturasEndolog_Executivo.pbip`** no Power BI Desktop (versão 2024 ou mais nova).
3. Clique em **Atualizar**. Na primeira vez:
   - SharePoint: use a **conta organizacional** (já salva no seu Desktop);
   - `olinda.bcb.gov.br` (cotação do dólar): escolha **Anônimo**. Se a rede bloquear, o relatório usa o parâmetro `pTaxaDolarPadrao` (5,5) e segue funcionando.
4. **Arquivo → Salvar como → .pbix** para publicar no Power BI Service como antes.

## O que está incluído
- Tema Abbott, cabeçalho com logo, período e data de atualização.
- Filtros Ano / Mês / Filial / BU / Título e botão **R$ | US$** em todas as páginas.
- Cartões: Valor cobrado, Qtde de serviços, Preço médio, Variação vs mês anterior.
- Evolução mensal por **mês/ano** (jan/26, fev/26…), participação por filial, valor por título, preço médio por tipo, valor por filial e tabela de detalhe.
- Cost Drive: total consolidado, peso Endolog, acumulado no ano, matrizes e gráfico Endolog + LOGMED por mês.
- Correções: dólar pelo PTAX mensal, valores digitados como texto (ex.: "R$ 5.130,00") e meses escritos errado ("SETEMBRO", "Jeneiro").
- As páginas "Saídas Logmed" e "validações" não entraram (usavam tabelas que não existem no modelo e dados de pacientes). Elas continuam no `FaturasEndolog.pbix` original.

## Conferência depois da primeira atualização
- Sem filtro de BU, Ano = 2026, LOGMED: **Setembro = R$ 365.835,96** e **Outubro = R$ 367.487,68**.
- Total geral em R$ da página ENDOLOG (sem filtros) deve bater com o relatório antigo.
