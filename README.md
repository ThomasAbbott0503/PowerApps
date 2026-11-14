# Faturas Last Mile – Endolog / LOGMED (Abbott)

Relatório executivo em Power BI, com modelo de dados corrigido e layout pronto.
Este repositório guarda **só a estrutura** do relatório (consultas, medidas, visuais). Os dados ficam no SharePoint da Abbott e entram quando você atualiza.

## Como usar

**Jeito rápido – `FaturasEndolog_Executivo.pbit`**
1. Baixe o arquivo e dê dois cliques (abre no Power BI Desktop).
2. Ele pergunta o parâmetro `pTaxaDolarPadrao` (deixe **5,5**) → **Carregar**.
3. Na primeira atualização ele pede credenciais:
   - SharePoint `abbott.sharepoint.com` → **Conta organizacional**;
   - `olinda.bcb.gov.br` (cotação PTAX) → **Anônimo**. Se a rede bloquear, o relatório usa 5,5 e continua funcionando.
4. **Arquivo → Salvar como → .pbix** e publique no Power BI Service como sempre.

**Para versionar – projeto `FaturasEndolog_Executivo.pbip`**
Mesmo conteúdo, em arquivos de texto (`.Report` + `.SemanticModel`). Baixe o repositório inteiro (Code → Download ZIP), abra o `.pbip` no Desktop e clique em **Atualizar**. Alterações feitas no Desktop e salvas aqui ficam com histórico.

## O que está montado (3 páginas, 1280 × 720)

| Página | Conteúdo |
|---|---|
| Faturas ENDOLOG / Faturas LOGMED | Cabeçalho Abbott (logo, período selecionado, data da última atualização) · filtros Ano, Mês, Filial, BU, Título · botão **R$ \| US$** · cartões Valor cobrado, Qtde de serviços, Preço médio, **Variação vs mês anterior** (▲ vermelho / ▼ verde) · evolução mensal (jan/26, fev/26…) · participação por filial · valor por título · preço médio por tipo · valor por filial · tabela de detalhe |
| Cost Drive | Total faturado consolidado, peso Endolog, acumulado no ano Endolog e LOGMED · matrizes tipo de serviço × mês · gráfico mensal Endolog + LOGMED |

As páginas antigas *Saídas Logmed* e *validações* não entraram: usavam tabelas que não existem no modelo e expunham nome de paciente e médico (LGPD).

## Correções no modelo de dados

| Antes | Agora |
|---|---|
| Dólar fixo em 5,5 | PTAX médio mensal do Banco Central (`Cambio`), com 5,5 só como reserva |
| Mês ligado só pelo nome (anos se misturavam) | Coluna `DataRef` (1º dia do mês) ligada a um calendário `dDATAS` com mês **e** ano |
| Meses com erro de digitação ("Jeneiro", "MAIO ", "SETEMBRO") sumiam dos filtros | Função `fxMes` padroniza (maiúsculas, espaços, abreviações) |
| Valores em texto ("R$ 1.234,56", "R$ 150.00", "0,10%", "R$ -") dependiam do locale | Função `fxNumero` converte todos os formatos; vazio/traço vira 0 |
| Gráfico somava o **preço unitário** | Medida **Preço Médio** (Cobrado ÷ Qtde) |
| Medidas `tpmoeda` devolviam texto (quebravam totais) | Devolvem número com **formato dinâmico** R$/US$ |
| Filiais digitadas à mão | Lista automática a partir dos dados |
| 5 leituras do site inteiro do SharePoint | 1 consulta-base `PastaFaturas` + função `fxLerAba` |

Fontes continuam as mesmas: `Base Unificada Fretes Endolog.xlsx`, `Base Unificada Serviços Endolog.xlsx` (aba *Resumo unificado*) e `Faturas_LOGMED.xlsx` (abas *Armazenagem* e *atendimentos*), na pasta `BI-FATURAS BU LASTMILES`.

## Conferência após a primeira atualização (Ano = 2026, sem outros filtros)

| Mês | ENDOLOG | LOGMED |
|---|---|---|
| Janeiro | – | R$ 362.245,11 |
| Fevereiro | – | R$ 326.012,69 |
| Março | – | R$ 404.149,77 |
| Abril | – | R$ 383.210,44 |
| Maio | R$ 312.802,40 | R$ 398.041,82 |
| Junho | R$ 121.617,77 | R$ 385.227,98 |
| Julho | R$ 335.271,40 | – |
| Agosto | R$ 127.912,80 | R$ 368.314,76 |
| Setembro | R$ 353.261,80 | R$ 365.835,96 |
| Outubro | – | R$ 367.487,68 |
| **Total 2026** | **R$ 1.250.866,17** | **R$ 3.360.526,21** |

Calculados a partir das planilhas de 14/11/2026. "–" = o mês não existe na planilha.
Se um mês aparecer no relatório com valor diferente, ou não aparecer, o problema está na planilha do SharePoint (linhas faltando ou ano errado), não no relatório.

## Estrutura do repositório

```
FaturasEndolog_Executivo.pbit            ← abra este (modelo pronto)
FaturasEndolog_Executivo.pbip            ← projeto (texto)
FaturasEndolog_Executivo.Report/         ← layout (report.json) e tema
FaturasEndolog_Executivo.SemanticModel/  ← consultas M, medidas DAX, relações (TMDL)
ferramentas/                             ← scripts que geraram o projeto e o tema Abbott
```

`.gitignore` bloqueia `.pbix`, `.xlsx`, `.xlsm` e `.csv`: arquivos com dados não devem subir para o GitHub.
