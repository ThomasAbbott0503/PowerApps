# Faturas Endolog / LOGMED — Pacote de melhorias (padrão Abbott)

> **Uso interno Abbott.** Este pacote contém só lógica (consultas, medidas, tema e layout), nenhum dado.
> O arquivo `.pbix` guarda dados importados e **não deve ficar em repositório público**.

## Arquivo pronto: `FaturasEndolog_Executivo.pbix` (na raiz do repositório)

É o mesmo relatório, com o **layout novo já aplicado**: tema Abbott, faixa azul-marinho com o logo, grade alinhada, títulos corrigidos, páginas com problema ocultas e 7 visuais personalizados não usados removidos.
**O modelo de dados não foi alterado**: mesmas consultas, medidas e relações. Por isso os números são os mesmos de hoje.
As correções de cálculo (dólar, preço médio, calendário) entram quando você aplicar os arquivos `01` e `02` seguindo o guia abaixo.
O original `FaturasEndolog.pbix` continua no repositório, sem mudanças.

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `tema-abbott.json` | Tema do Power BI nas cores Abbott (azul-marinho do logo #000075, azul-claro #009CDE de apoio) |
| `01-consultas-power-query.pq` | Consultas M corrigidas (mesmos nomes de tabela) |
| `02-medidas-dax.dax` | Medidas corrigidas e novas medidas executivas |
| `README.md` | Este guia: erros corrigidos, ordem de aplicação e layout |

A lógica atual foi mantida: as mesmas tabelas, as mesmas fontes no SharePoint, as mesmas páginas e os mesmos filtros (filial, BU, mês, ano, moeda).

---

## Erros corrigidos

| # | Erro | Correção |
|---|---|---|
| 1 | Dólar fixo em **5,5** (consulta e DAX) | PTAX médio mensal do Banco Central; se a API falhar, usa o parâmetro `pTaxaDolarPadrao` |
| 2 | `tpmoeda`/`tpmoedalog` com `FORMAT()` devolviam **texto** | Devolvem número, com **formato dinâmico** R$/US$ |
| 3 | Gráfico "Tipo de serviço" **somava PREÇO unitário** | Usa a nova medida `Preço Médio` (Cobrado ÷ Qtde) |
| 4 | Relação por **nome do mês** sem ano (meses de anos diferentes se misturavam) | Coluna `DataRef` (1º dia do mês) ligada a `dDATAS[Data]` |
| 5 | `ANO` texto × tabela `Ano` número; LOGMED sem relação de ano | Ano vem de `dDATAS[Ano]` para as duas tabelas |
| 6 | `VALORDOLAR` formatada como R$ | Formato US$ |
| 7 | `Quantidade` como **texto** no LOGMED_atendimento | Número |
| 7b | **Valores digitados como texto** na Faturas_LOGMED (" R$ 5.130,00", "0,10%") viravam erro e sumiam. É o motivo de **setembro/2026** não aparecer no LOGMED (8 linhas afetadas; mai/26 tem 24, jan/26 9, jun/26 9, abr/26 8, ago/26 6) | Função `fxNumero` converte o texto em número |
| 7c | Mês digitado errado: "SETEMBRO", "JULHO", "Jeneiro" | Função `fxMes` padroniza |
| 8 | Filiais digitadas à mão (RJ, MG, SP, DF) | Lista automática a partir dos dados |
| 9 | `SharePoint.Files` listava o site inteiro 5× | Uma consulta-base `PastaFaturas` + função `fxLerAba` |
| 10 | Tabelas intermediárias carregadas (dados duplicados) | FRETES, Serviços, LOGMED_* com "Habilitar carga" desligado |
| 11 | Sobras não usadas (Armazenagem_Endolog, "Medida", consultas NF_Saida_2024, 7 visuais personalizados) | Removidas |
| 12 | Páginas **Saídas Logmed** e **validações** apontam para tabelas que não existem no modelo (LOGMED-ENVIOS, NF DE SAIDA, SC5 FATURAS BU) | Ocultar ou restaurar as consultas. **Atenção LGPD:** a página Saídas Logmed mostra *Paciente* e *Médico* |
| 13 | Donut chamado "por BU" mostrava FILIAL | Título "Participação por filial" |
| 14 | Páginas com tamanhos diferentes (1280×720 e 1920×1080) | Todas em 1280×720 |

---

## Ordem para aplicar (≈ 30 min no Power BI Desktop)

1. **Faça uma cópia** do `FaturasEndolog.pbix` antes de mexer.
2. **Tema:** Exibir → Temas → Procurar temas → `tema-abbott.json`.
3. **Power Query** (Transformar dados):
   1. Crie o parâmetro `pTaxaDolarPadrao` (Decimal, 5.5).
   2. Crie as consultas novas `PastaFaturas`, `fxLerAba`, `fxDataReferencia`, `fxNumero`, `fxMes`, `Cambio` (Nova fonte → Consulta nula → Editor Avançado → colar).
   3. Substitua o código de `FRETES`, `Serviços`, `Fatura_Endolog`, `LOGMED_armazenagem`, `LOGMED_atendimento`, `LOGMED-Serviços`, `dDATAS`, `FILIAISENDOLOG`.
   4. Desligue "Habilitar carga" em: `PastaFaturas`, `fxLerAba`, `fxDataReferencia`, `fxNumero`, `fxMes`, `FRETES`, `Serviços`, `LOGMED_armazenagem`, `LOGMED_atendimento`, `Cambio`.
   5. Apague `Ano`, `Armazenagem_Endolog`, `Parâmetro1`, `Arquivo de Amostra`, `Transformar Arquivo`, `Transformar o Arquivo de Exemplo`.
   6. Fechar e Aplicar.
   > Se `PastaFaturas` der erro em `"Shared Documents"`, troque por `"Documentos Compartilhados"`.
   > Se a API do Banco Central for bloqueada pela rede da Abbott, o relatório continua funcionando com a taxa do parâmetro.
4. **Relacionamentos** (Exibição de modelo), todos *muitos-para-um*, filtro único:
   - `Fatura_Endolog[DataRef]` → `dDATAS[Data]`
   - `LOGMED-Serviços[DataRef]` → `dDATAS[Data]`
   - `Fatura_Endolog[FILIAL]` → `FILIAISENDOLOG[FILIAL]`
   - `LOGMED-Serviços[FILIAL]` → `FILIAISENDOLOG[FILIAL]`
   - Apague as relações antigas por `MÊS`/`NomeMês` e `ANO`/`Ano`.
   - Em `dDATAS[NomeMês]`: Classificar por coluna → `Mês`.
5. **Medidas:** edite as 6 existentes e crie as novas de `02-medidas-dax.dax`.
6. **Visuais:** siga o layout abaixo. Troque os filtros de ano (`Ano[Ano]` e `LOGMED-Serviços[ANO]`) por `dDATAS[Ano]`, e os de filial por `FILIAISENDOLOG[FILIAL]`.
7. **Visuais personalizados:** Exibir → painel Visualizações → `…` → remova os que não estão em uso (sobra só o Text Filter, se mantiver a página Saídas Logmed).
8. Salve como **Projeto do Power BI (.pbip)** para versionar no Git.

---

## Layout executivo (todas as páginas 1280×720)

Grade com margem de 16 px e espaço de 12 px entre cartões. Fundo #F4F7F9, cartões brancos com borda de 8 px.

```
┌──────────────────────────────────────────────────────────────────────┐
│ ▌ABBOTT  Faturas ENDOLOG      Período: jan/26 a out/26   Atualizado… │  faixa 56 px #000075 + linha #009CDE
├──────────────────────────────────────────────────────────────────────┤
│ [Ano] [Mês] [Filial] [BU] [Moeda R$|US$]                            │  filtros 40 px
├──────────────┬──────────────┬──────────────┬─────────────────────────┤
│ Valor cobrado│ Qtde serviços│ Preço médio  │ Var. vs mês anterior    │  KPIs 96 px
├──────────────┴──────────────┴──────────┬───┴─────────────────────────┤
│ Evolução mensal do valor cobrado       │ Participação por filial     │
│ (linha: tpmoeda por MêsAno)            │ (donut)                     │  230 px
├────────────────────────┬───────────────┴─────────────────────────────┤
│ Valor por título       │ Valor por filial (colunas)                  │  230 px
│ (barras)               │                                             │
├────────────────────────┴─────────────────────────────────────────────┤
│ Detalhe: Filial | BU | Tipo de serviço | Título | Mês | Qtde | Preço médio | Cobrado │
└──────────────────────────────────────────────────────────────────────┘
```

### Página 1 — Faturas ENDOLOG
| Visual | Antes | Depois |
|---|---|---|
| Cartão | "Valor cobrado" (Soma COBRADO) | `tpmoeda`, título "Valor cobrado" |
| Cartão | "total de serviços" | `Qtde Serviços Endolog`, "Qtde de serviços" |
| Cartão (novo) | — | `Preço Médio Endolog` |
| Cartão (novo) | — | `Var % Mês Endolog` com ícone ▲/▼ verde/vermelho |
| Linha | "Variação da cobrança por mês" | eixo `dDATAS[MêsAno]`, valor `tpmoeda`, "Evolução mensal do valor cobrado" |
| Donut | "Porcentagem de cobrança por BU" (era filial) | `FILIAISENDOLOG[FILIAL]` × `tpmoeda`, "Participação por filial" |
| Barras | "TIPO DE SERVIÇOS COBRADOS" | `TÍTULO` × `tpmoeda`, "Valor por título" (ordem decrescente) |
| Barras | "Tipo de serviço" (Soma PREÇO) | `TIPO DE SERVIÇO` × `Preço Médio Endolog`, "Preço médio por tipo de serviço" |
| Combo | "Valor cobrado por lastmiles" | colunas simples `FILIAL` × `tpmoeda`, "Valor por filial (last mile)" |
| Tabela | detalhe | mesmas colunas + `Preço Médio`; cabeçalho azul-marinho, zebra |

### Página 2 — Faturas LOGMED
Mesma grade e mesmos visuais da página 1, usando as medidas `…LOGMED` / `tpmoedalog`. Os filtros são sincronizados com a página 1 (Exibir → Sincronizar segmentações).

### Página 3 — Cost Drive
- Cabeçalho e filtros iguais; **um** filtro de Filial, BU e Título (antes eram 6 duplicados).
- KPIs: `Total Faturado Moeda`, `Peso Endolog %`, `Acumulado Ano Endolog`, `Acumulado Ano LOGMED`.
- As duas matrizes atuais (Tipo de serviço × Mês com `tpmoeda`/`tpmoedalog`) ficam lado a lado, com formatação condicional (escala azul) nos valores.
- Novo gráfico de colunas empilhadas "Total faturado por mês" (`dDATAS[MêsAno]` × `tpmoeda` e `tpmoedalog`).

### Páginas 4 e 5 — Saídas Logmed / validações
Ficam **ocultas** até as consultas dessas tabelas serem restauradas. Antes de publicar, remova ou mascare *Paciente* e *Médico* (LGPD).
