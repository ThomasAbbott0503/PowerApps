// =====================================================================
//  FATURAS ENDOLOG / LOGMED — CONSULTAS POWER QUERY CORRIGIDAS
//  Como usar: Power Query > Página Inicial > Editor Avançado.
//  Cole cada bloco na consulta de MESMO NOME (os nomes das tabelas
//  foram mantidos para não quebrar nenhum visual).
//  Consultas marcadas [NÃO CARREGAR]: clique direito > desmarque
//  "Habilitar carga".
// =====================================================================


// ---------------------------------------------------------------------
// 1) pTaxaDolarPadrao  [PARÂMETRO NOVO]
//    Taxa usada só quando o PTAX do mês não estiver disponível.
//    Página Inicial > Gerenciar Parâmetros > Novo: Decimal, valor 5.5
// ---------------------------------------------------------------------
5.5 meta [IsParameterQuery = true, Type = "Number", IsParameterQueryRequired = true]


// ---------------------------------------------------------------------
// 2) PastaFaturas  [NOVA — NÃO CARREGAR]
//    Lê SÓ a pasta das faturas (antes o SharePoint.Files listava o
//    site inteiro, 5 vezes). Atualização bem mais rápida.
// ---------------------------------------------------------------------
let
    Site    = "https://abbott.sharepoint.com/sites/BR-MD-SUPPLYCHAINFAT/",
    Fonte   = SharePoint.Contents(Site, [ApiVersion = 15]),
    Docs    = Fonte{[Name = "Shared Documents"]}[Content],
    Pasta   = Docs{[Name = "BI-FATURAS BU LASTMILES"]}[Content],
    Arquivos = Table.SelectColumns(Pasta, {"Name", "Content", "Date modified"})
in
    Arquivos


// ---------------------------------------------------------------------
// 3) fxLerAba  [NOVA FUNÇÃO — NÃO CARREGAR]
//    Abre um arquivo da pasta e devolve a aba com cabeçalho.
// ---------------------------------------------------------------------
(NomeArquivo as text, Aba as text) as table =>
let
    Arquivo = PastaFaturas{[Name = NomeArquivo]}[Content],
    Livro   = Excel.Workbook(Arquivo, null, true),
    Planilha = Livro{[Item = Aba, Kind = "Sheet"]}[Data],
    ComCabecalho = Table.PromoteHeaders(Planilha, [PromoteAllScalars = true]),
    // remove linhas totalmente vazias do Excel
    SemVazias = Table.SelectRows(ComCabecalho, each not List.IsEmpty(List.RemoveMatchingItems(Record.FieldValues(_), {"", null})))
in
    SemVazias


// ---------------------------------------------------------------------
// 4) fxDataReferencia  [NOVA FUNÇÃO — NÃO CARREGAR]
//    Cria a coluna DataRef (1º dia do mês) a partir de ANO + MÊS.
//    Resolve o problema de meses de anos diferentes se misturarem.
// ---------------------------------------------------------------------
(Tabela as table, ColMes as text, ColAno as text) as table =>
let
    Meses = {"Janeiro","Fevereiro","Março","Abril","Maio","Junho",
             "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"},
    MesPadrao = Table.TransformColumns(Tabela, {{ColMes, each Text.Proper(Text.Trim(Text.From(_))), type text}}),
    AnoNumero = Table.TransformColumns(MesPadrao, {{ColAno, each try Int64.From(_) otherwise null, Int64.Type}}),
    ComData = Table.AddColumn(AnoNumero, "DataRef", each
        let
            m = List.PositionOf(Meses, Record.Field(_, ColMes)) + 1,
            a = Record.Field(_, ColAno)
        in
            if m > 0 and a <> null then #date(a, m, 1) else null,
        type date)
in
    ComData


// ---------------------------------------------------------------------
// 5) FRETES  [NÃO CARREGAR — vira parte de Fatura_Endolog]
// ---------------------------------------------------------------------
let
    Fonte = fxLerAba("Base Unificada Fretes Endolog.xlsx", "Resumo unificado"),
    Tipos = Table.TransformColumnTypes(Fonte, {
        {"FILIAL", type text}, {"BU", type text}, {"TIPO DE SERVIÇO", type text},
        {"QTDE", Int64.Type}, {"PREÇO", Currency.Type}, {"COBRADO", Currency.Type},
        {"MÊS", type text}, {"TÍTULO", type text}, {"ANO", type text}})
in
    Tipos


// ---------------------------------------------------------------------
// 6) Serviços  [NÃO CARREGAR — vira parte de Fatura_Endolog]
// ---------------------------------------------------------------------
let
    Fonte = fxLerAba("Base Unificada Serviços Endolog.xlsx", "Resumo unificado"),
    Tipos = Table.TransformColumnTypes(Fonte, {
        {"FILIAL", type text}, {"BU", type text}, {"TIPO DE SERVIÇO", type text},
        {"QTDE", Int64.Type}, {"PREÇO", Currency.Type}, {"COBRADO", Currency.Type},
        {"MÊS", type text}, {"TÍTULO", type text}, {"ANO", type text}})
in
    Tipos


// ---------------------------------------------------------------------
// 7) Fatura_Endolog  [CARREGAR]
//    Mesma lógica de antes (Fretes + Serviços), agora com DataRef.
//    A coluna "dolar" fixa em 5,5 saiu: o dólar agora é calculado na
//    medida VALORDOLAR com o PTAX de cada mês.
// ---------------------------------------------------------------------
let
    Fonte    = Table.Combine({FRETES, Serviços}),
    ComData  = fxDataReferencia(Fonte, "MÊS", "ANO"),
    Limpo    = Table.TransformColumns(ComData, {
                  {"FILIAL", each Text.Upper(Text.Trim(_)), type text},
                  {"BU", each Text.Trim(_), type text}}),
    SemNulos = Table.ReplaceValue(Limpo, null, 0, Replacer.ReplaceValue, {"QTDE", "COBRADO"})
in
    SemNulos


// ---------------------------------------------------------------------
// 8) LOGMED_armazenagem  [NÃO CARREGAR]
// ---------------------------------------------------------------------
let
    Fonte = fxLerAba("Faturas_LOGMED.xlsx", "Armazenagem"),
    Tipos = Table.TransformColumnTypes(Fonte, {
        {"SERVIÇO", type text}, {"Quantidade", type number}, {"Valor", Currency.Type},
        {"Total", Currency.Type}, {"MÊS", type text}, {"FILIAL", type text},
        {"BU", type text}, {"TÍTULO", type text}, {"ANO", type text}})
in
    Tipos


// ---------------------------------------------------------------------
// 9) LOGMED_atendimento  [NÃO CARREGAR]
//    Antes "Quantidade" vinha como TEXTO aqui. Corrigido.
// ---------------------------------------------------------------------
let
    Fonte = fxLerAba("Faturas_LOGMED.xlsx", "atendimentos"),
    Tipos = Table.TransformColumnTypes(Fonte, {
        {"SERVIÇO", type text}, {"Quantidade", type number}, {"Valor", Currency.Type},
        {"Total", Currency.Type}, {"MÊS", type text}, {"FILIAL", type text},
        {"BU", type text}, {"TÍTULO", type text}, {"ANO", type text}})
in
    Tipos


// ---------------------------------------------------------------------
// 10) LOGMED-Serviços  [CARREGAR]
// ---------------------------------------------------------------------
let
    Fonte    = Table.Combine({LOGMED_armazenagem, LOGMED_atendimento}),
    ComData  = fxDataReferencia(Fonte, "MÊS", "ANO"),
    Limpo    = Table.TransformColumns(ComData, {{"FILIAL", each Text.Upper(Text.Trim(_)), type text}}),
    SemNulos = Table.ReplaceValue(Limpo, null, 0, Replacer.ReplaceValue, {"Quantidade", "Total"}),
    Tipos    = Table.TransformColumnTypes(SemNulos, {{"Quantidade", Int64.Type}})
in
    Tipos


// ---------------------------------------------------------------------
// 11) Cambio  [NÃO CARREGAR]
//     PTAX médio mensal (venda) do Banco Central. Se a API não
//     responder, usa o parâmetro pTaxaDolarPadrao.
// ---------------------------------------------------------------------
let
    Inicio = "01-01-2020",
    Fim    = Date.ToText(Date.From(DateTime.LocalNow()), "MM-dd-yyyy"),
    Url    = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/" &
             "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)" &
             "?@dataInicial='" & Inicio & "'&@dataFinalCotacao='" & Fim & "'&$format=json&$select=cotacaoVenda,dataHoraCotacao",
    Tentativa = try
        let
            Json   = Json.Document(Web.Contents(Url)),
            Tab    = Table.FromRecords(Json[value]),
            ComMes = Table.AddColumn(Tab, "Data", each Date.StartOfMonth(Date.From(DateTime.FromText(Text.Start([dataHoraCotacao], 19)))), type date),
            Media  = Table.Group(ComMes, {"Data"}, {{"PTAX", each List.Average([cotacaoVenda]), type number}})
        in
            Media
    otherwise #table(type table [Data = date, PTAX = number], {})
in
    Tentativa


// ---------------------------------------------------------------------
// 12) dDATAS  [CARREGAR — substitui a anterior]
//     Agora 1 linha por MÊS/ANO (antes eram só 12 linhas, sem ano).
//     Mantém as colunas Mês e NomeMês para não quebrar visuais.
//     Depois: marcar NomeMês "Classificar por coluna" = Mês.
// ---------------------------------------------------------------------
let
    Inicio  = #date(2020, 1, 1),
    Fim     = Date.EndOfYear(Date.From(DateTime.LocalNow())),
    QtdMeses = (Date.Year(Fim) - Date.Year(Inicio)) * 12 + Date.Month(Fim),
    Lista   = List.Transform({0 .. QtdMeses - 1}, each Date.AddMonths(Inicio, _)),
    Base    = Table.FromList(Lista, Splitter.SplitByNothing(), type table [Data = date]),
    Meses   = {"Janeiro","Fevereiro","Março","Abril","Maio","Junho",
               "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"},
    Ano     = Table.AddColumn(Base, "Ano", each Date.Year([Data]), Int64.Type),
    Mes     = Table.AddColumn(Ano, "Mês", each Date.Month([Data]), Int64.Type),
    Nome    = Table.AddColumn(Mes, "NomeMês", each Meses{[Mês] - 1}, type text),
    Abrev   = Table.AddColumn(Nome, "MêsAbrev", each Text.Start([NomeMês], 3), type text),
    AnoMes  = Table.AddColumn(Abrev, "AnoMês", each Text.From([Ano]) & "-" & Text.PadStart(Text.From([Mês]), 2, "0"), type text),
    Rotulo  = Table.AddColumn(AnoMes, "MêsAno", each [MêsAbrev] & "/" & Text.End(Text.From([Ano]), 2), type text),
    Tri     = Table.AddColumn(Rotulo, "Trimestre", each "T" & Text.From(Date.QuarterOfYear([Data])), type text),
    ComPtax = Table.NestedJoin(Tri, {"Data"}, Cambio, {"Data"}, "c", JoinKind.LeftOuter),
    Ptax    = Table.AddColumn(ComPtax, "PTAX", each
                 let v = try [c]{0}[PTAX] otherwise null in if v = null then pTaxaDolarPadrao else v, type number),
    Final   = Table.RemoveColumns(Ptax, {"c"})
in
    Final


// ---------------------------------------------------------------------
// 13) FILIAISENDOLOG  [CARREGAR — agora automática]
//     Antes era digitada à mão (RJ, MG, SP, DF). Filial nova aparece
//     sozinha.
// ---------------------------------------------------------------------
let
    Lista  = List.Distinct(List.Combine({Fatura_Endolog[FILIAL], #"LOGMED-Serviços"[FILIAL]})),
    SemNulo = List.Sort(List.RemoveNulls(List.Select(Lista, each _ <> ""))),
    Tabela = Table.FromList(SemNulo, Splitter.SplitByNothing(), type table [FILIAL = text])
in
    Tabela


// ---------------------------------------------------------------------
// 14) TipoMoeda  [MANTIDA, sem alteração]  -> Dolar / Real
//
// 15) APAGAR: Ano (substituída por dDATAS[Ano]), Armazenagem_Endolog
//     (não usada em nenhum visual), Parâmetro1, Arquivo de Amostra,
//     Transformar Arquivo, Transformar o Arquivo de Exemplo
//     (sobras da NF_Saida_2024 que não alimentam nada).
// =====================================================================
