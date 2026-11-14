"""Gera a pasta FaturasEndolog_Executivo.SemanticModel (formato TMDL)."""
import os, sys, json, uuid
OUT = sys.argv[1]
D = os.path.join(OUT, "definition")
os.makedirs(os.path.join(D, "tables"), exist_ok=True)

SITE = "https://abbott.sharepoint.com/sites/BR-MD-SUPPLYCHAINFAT/"
BRL = '"R$"\\ #,0;-"R$"\\ #,0;"R$"\\ #,0'
BRL2 = '"R$"\\ #,0.00;-"R$"\\ #,0.00;"R$"\\ #,0.00'
USD = '"US$"\\ #,0;-"US$"\\ #,0;"US$"\\ #,0'
DYN = 'IF ( SELECTEDVALUE ( TipoMoeda[Moeda], "Real" ) = "Real", """R$"" #,0", """US$"" #,0" )'

def w(path, txt):
    with open(os.path.join(D, path), "w", encoding="utf-8") as f:
        f.write(txt.strip("\n") + "\n")

def ind(txt, n):
    return "\n".join(("\t" * n + l) if l.strip() else "" for l in txt.strip("\n").splitlines())

# ----------------------------------------------------------------- M
M_PASTA = f'''
let
    Fonte = SharePoint.Files("{SITE}", [ApiVersion = 15]),
    Pasta = Table.SelectRows(Fonte, each Text.Contains([Folder Path], "BI-FATURAS BU LASTMILES")),
    Colunas = Table.SelectColumns(Pasta, {{"Name", "Content", "Date modified"}})
in
    Colunas
'''
M_LERABA = '''
(NomeArquivo as text, Aba as text) as table =>
let
    Arquivo = PastaFaturas{[Name = NomeArquivo]}[Content],
    Livro = Excel.Workbook(Arquivo, null, true),
    Planilha = Livro{[Item = Aba, Kind = "Sheet"]}[Data],
    ComCabecalho = Table.PromoteHeaders(Planilha, [PromoteAllScalars = true]),
    SemVazias = Table.SelectRows(ComCabecalho, each not List.IsEmpty(List.RemoveMatchingItems(Record.FieldValues(_), {"", null})))
in
    SemVazias
'''
M_NUMERO = '''
(v as any) as nullable number =>
let
    r = if v = null then null
        else if Value.Is(v, type number) then v
        else
            let
                t0 = Text.Trim(Text.Replace(Text.Replace(Text.Replace(Text.From(v), "R$", ""), "US$", ""), " ", "")),
                pct = Text.EndsWith(t0, "%"),
                t = Text.TrimEnd(t0, "%"),
                // "1.234,56" -> 1234.56 | "999.99" (um ponto, 2 casas) -> 999.99 | "1.234" -> 1234
                limpo = if Text.Contains(t, ",") then Text.Replace(Text.Replace(t, ".", ""), ",", ".")
                        else if Text.Contains(t, ".") and List.Count(Text.Split(t, ".")) = 2 and Text.Length(Text.AfterDelimiter(t, ".")) = 2 then t
                        else Text.Replace(t, ".", ""),
                n = if limpo = "" or limpo = "-" then null else try Number.FromText(limpo, "en-US") otherwise null
            in
                if n = null then null else if pct then n / 100 else n
in
    r
'''
M_MES = '''
(v as any) as nullable text =>
let
    t = if v = null then null else Text.Proper(Text.Trim(Text.From(v))),
    mapa = [Jan = "Janeiro", Jeneiro = "Janeiro", Fev = "Fevereiro", Mar = "Março", Marco = "Março", Abr = "Abril", Mai = "Maio", Jun = "Junho", Jul = "Julho", Ago = "Agosto", Set = "Setembro", Out = "Outubro", Nov = "Novembro", Dez = "Dezembro"]
in
    if t = null then null else Record.FieldOrDefault(mapa, t, t)
'''
M_DATAREF = '''
(Tabela as table, ColMes as text, ColAno as text) as table =>
let
    Meses = {"Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"},
    MesPadrao = Table.TransformColumns(Tabela, {{ColMes, fxMes, type text}}),
    AnoTexto = Table.TransformColumns(MesPadrao, {{ColAno, each try Text.From(Int64.From(_)) otherwise null, type text}}),
    ComData = Table.AddColumn(AnoTexto, "DataRef", each
        let m = List.PositionOf(Meses, Record.Field(_, ColMes)) + 1,
            a = try Int64.From(Record.Field(_, ColAno)) otherwise null
        in if m > 0 and a <> null then #date(a, m, 1) else null, type date)
in
    ComData
'''
def m_endolog(arq):
    return f'''
let
    Fonte = fxLerAba("{arq}", "Resumo unificado"),
    Numeros = Table.TransformColumns(Fonte, {{{{"QTDE", fxNumero, type number}}, {{"PREÇO", fxNumero, Currency.Type}}, {{"COBRADO", fxNumero, Currency.Type}}}}),
    Tipos = Table.TransformColumnTypes(Numeros, {{{{"FILIAL", type text}}, {{"BU", type text}}, {{"TIPO DE SERVIÇO", type text}}, {{"MÊS", type text}}, {{"TÍTULO", type text}}, {{"ANO", type text}}}})
in
    Tipos
'''
def m_logmed(aba):
    return f'''
let
    Fonte = fxLerAba("Faturas_LOGMED.xlsx", "{aba}"),
    Numeros = Table.TransformColumns(Fonte, {{{{"Quantidade", fxNumero, type number}}, {{"Valor", fxNumero, Currency.Type}}, {{"Total", fxNumero, Currency.Type}}}}),
    Tipos = Table.TransformColumnTypes(Numeros, {{{{"SERVIÇO", type text}}, {{"MÊS", type text}}, {{"FILIAL", type text}}, {{"BU", type text}}, {{"TÍTULO", type text}}, {{"ANO", type text}}}})
in
    Tipos
'''
M_CAMBIO = '''
let
    Inicio = "01-01-2020",
    Fim = Date.ToText(Date.From(DateTime.LocalNow()), "MM-dd-yyyy"),
    Url = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='" & Inicio & "'&@dataFinalCotacao='" & Fim & "'&$format=json&$select=cotacaoVenda,dataHoraCotacao",
    Tentativa = try
        let
            Json = Json.Document(Web.Contents(Url)),
            Tab = Table.FromRecords(Json[value]),
            ComMes = Table.AddColumn(Tab, "Data", each Date.StartOfMonth(Date.From(DateTime.FromText(Text.Start([dataHoraCotacao], 19)))), type date),
            Media = Table.Group(ComMes, {"Data"}, {{"PTAX", each List.Average([cotacaoVenda]), type number}})
        in
            Media
    otherwise #table(type table [Data = date, PTAX = number], {})
in
    Tentativa
'''
M_FATURA = '''
let
    Fonte = Table.Combine({FRETES, Serviços}),
    ComData = fxDataReferencia(Fonte, "MÊS", "ANO"),
    Limpo = Table.TransformColumns(ComData, {{"FILIAL", each Text.Upper(Text.Trim(Text.From(_))), type text}, {"BU", each Text.Trim(Text.From(_)), type text}}),
    SemNulos = Table.ReplaceValue(Limpo, null, 0, Replacer.ReplaceValue, {"QTDE", "COBRADO"}),
    Tipos = Table.TransformColumnTypes(SemNulos, {{"QTDE", Int64.Type}})
in
    Tipos
'''
M_LOGSERV = '''
let
    Fonte = Table.Combine({LOGMED_armazenagem, LOGMED_atendimento}),
    ComData = fxDataReferencia(Fonte, "MÊS", "ANO"),
    Limpo = Table.TransformColumns(ComData, {{"FILIAL", each Text.Upper(Text.Trim(Text.From(_))), type text}}),
    SemNulos = Table.ReplaceValue(Limpo, null, 0, Replacer.ReplaceValue, {"Quantidade", "Total"})
in
    SemNulos
'''
M_DDATAS = '''
let
    Inicio = #date(2020, 1, 1),
    Fim = Date.EndOfYear(Date.From(DateTime.LocalNow())),
    QtdMeses = (Date.Year(Fim) - Date.Year(Inicio)) * 12 + Date.Month(Fim),
    Lista = List.Transform({0 .. QtdMeses - 1}, each Date.AddMonths(Inicio, _)),
    Base = Table.FromList(Lista, Splitter.SplitByNothing(), type table [Data = date]),
    Meses = {"Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"},
    Ano = Table.AddColumn(Base, "Ano", each Date.Year([Data]), Int64.Type),
    Mes = Table.AddColumn(Ano, "Mês", each Date.Month([Data]), Int64.Type),
    Nome = Table.AddColumn(Mes, "NomeMês", each Meses{[Mês] - 1}, type text),
    AnoMes = Table.AddColumn(Nome, "AnoMês", each Text.From([Ano]) & "-" & Text.PadStart(Text.From([Mês]), 2, "0"), type text),
    Rotulo = Table.AddColumn(AnoMes, "MêsAno", each Text.Lower(Text.Start([NomeMês], 3)) & "/" & Text.End(Text.From([Ano]), 2), type text),
    Tri = Table.AddColumn(Rotulo, "Trimestre", each "T" & Text.From(Date.QuarterOfYear([Data])), type text),
    ComPtax = Table.NestedJoin(Tri, {"Data"}, Cambio, {"Data"}, "c", JoinKind.LeftOuter),
    Ptax = Table.AddColumn(ComPtax, "PTAX", each let v = try [c]{0}[PTAX] otherwise null in if v = null then pTaxaDolarPadrao else v, type number),
    Final = Table.RemoveColumns(Ptax, {"c"})
in
    Final
'''
M_FILIAIS = '''
let
    Lista = List.Distinct(List.Combine({Fatura_Endolog[FILIAL], #"LOGMED-Serviços"[FILIAL]})),
    SemNulo = List.Sort(List.RemoveNulls(List.Select(Lista, each _ <> ""))),
    Tabela = Table.FromList(SemNulo, Splitter.SplitByNothing(), type table [FILIAL = text])
in
    Tabela
'''
M_MOEDA = '''
let
    Fonte = #table(type table [Moeda = text], {{"Real"}, {"Dolar"}})
in
    Fonte
'''
M_ATU = '''
let
    Fonte = #table(type table [Data = datetime], {{DateTime.LocalNow()}})
in
    Fonte
'''

# ----------------------------------------------------------------- TMDL helpers
def col(name, dt, fmt=None, sort=None, hidden=False, extra=""):
    q = f"'{name}'" if any(c in name for c in " -") else name
    s = f"\tcolumn {q}\n\t\tdataType: {dt}\n"
    if hidden: s += "\t\tisHidden\n"
    if fmt: s += f"\t\tformatString: {fmt}\n"
    s += "\t\tsummarizeBy: none\n\t\tsourceColumn: " + name + "\n"
    if sort: s += f"\t\tsortByColumn: {sort}\n"
    return s + extra + "\n"

def meas(name, dax, fmt=None, dyn=None):
    q = f"'{name}'" if " " in name or "%" in name else name
    if "\n" in dax.strip():
        s = f"\tmeasure {q} = ```\n" + ind(dax, 3) + "\n\t\t\t```\n"
    else:
        s = f"\tmeasure {q} = {dax.strip()}\n"
    if fmt: s += f"\t\tformatString: {fmt}\n"
    if dyn: s += f"\t\tformatStringDefinition = {dyn}\n"
    return s + "\n"

def part(name, m):
    q = f"'{name}'" if any(c in name for c in " -") else name
    return f"\tpartition {q} = m\n\t\tmode: import\n\t\tsource =\n" + ind(m, 4) + "\n\n"

def table(name, body, hidden=False):
    q = f"'{name}'" if any(c in name for c in " -") else name
    s = f"table {q}\n" + ("\tisHidden\n" if hidden else "") + "\n" + body + "\tannotation PBI_ResultType = Table\n"
    w(f"tables/{name}.tmdl", s)

def expr(name, m, group=None, result="Table"):
    q = f"'{name}'" if any(c in name for c in " -") else name
    body = m.strip("\n")
    if "\n" in body:
        s = f"expression {q} =\n" + ind(body, 2) + "\n"
    else:
        s = f"expression {q} = {body}\n"
    if group: s += f"\tqueryGroup: '{group}'\n"
    s += f"\tannotation PBI_ResultType = {result}\n\n"
    return s

# ----------------------------------------------------------------- tables
F = "Fatura_Endolog"; L = "'LOGMED-Serviços'"
mes_endolog = (
    meas("VALORREAL", f"SUM ( {F}[COBRADO] )", BRL)
  + meas("VALORDOLAR", f"SUMX ( VALUES ( dDATAS[Data] ), DIVIDE ( [VALORREAL], CALCULATE ( MAX ( dDATAS[PTAX] ) ) ) )", USD)
  + meas("tpmoeda", 'IF ( SELECTEDVALUE ( TipoMoeda[Moeda], "Real" ) = "Real", [VALORREAL], [VALORDOLAR] )', BRL, DYN)
  + meas("Qtde Serviços Endolog", f"SUM ( {F}[QTDE] )", "#,0")
  + meas("Preço Médio Endolog", "DIVIDE ( [VALORREAL], [Qtde Serviços Endolog] )", BRL2)
  + meas("Valor Mês Anterior Endolog", "VAR _d = MAX ( dDATAS[Data] ) RETURN CALCULATE ( [VALORREAL], REMOVEFILTERS ( dDATAS ), dDATAS[Data] = EDATE ( _d, -1 ) )", BRL)
  + meas("Var % Mês Endolog", "VAR _a = [Valor Mês Anterior Endolog] RETURN IF ( NOT ISBLANK ( _a ), DIVIDE ( [VALORREAL] - _a, _a ) )", "▲ 0.0%;▼ 0.0%;0.0%")
  + meas("Cor Var Endolog", 'IF ( [Var % Mês Endolog] > 0, "#D64545", "#2E9E6B" )')
  + meas("Acumulado Ano Endolog", "VAR _d = MAX ( dDATAS[Data] ) RETURN CALCULATE ( [VALORREAL], REMOVEFILTERS ( dDATAS ), dDATAS[Ano] = YEAR ( _d ), dDATAS[Data] <= _d )", BRL)
  + meas("Total Faturado", "[VALORREAL] + [valorreallog]", BRL)
  + meas("Total Faturado Moeda", "[tpmoeda] + [tpmoedalog]", BRL, DYN)
  + meas("Peso Endolog %", "DIVIDE ( [VALORREAL], [Total Faturado] )", "0.0%")
  + meas("Período Selecionado", 'VAR _i = MIN ( dDATAS[Data] ) VAR _f = MAX ( dDATAS[Data] ) RETURN "Período: " & FORMAT ( _i, "mmm/yy" ) & " a " & FORMAT ( _f, "mmm/yy" )')
  + meas("Última Atualização", '"Atualizado em " & FORMAT ( MAX ( Atualizacao[Data] ), "dd/mm/yyyy hh:mm" )')
  + meas("Cabeçalho Info", '[Período Selecionado] & "   |   " & [Última Atualização]')
)
cols_endolog = (col("FILIAL","string") + col("BU","string") + col("TIPO DE SERVIÇO","string")
  + col("QTDE","int64","#,0") + col("PREÇO","decimal",BRL2) + col("COBRADO","decimal",BRL)
  + col("MÊS","string") + col("TÍTULO","string") + col("ANO","string") + col("DataRef","dateTime","Short Date"))
table("Fatura_Endolog", mes_endolog + cols_endolog + part("Fatura_Endolog", M_FATURA))

mes_log = (
    meas("valorreallog", f"SUM ( {L}[Total] )", BRL)
  + meas("ValorEmUSDlogmed", "SUMX ( VALUES ( dDATAS[Data] ), DIVIDE ( [valorreallog], CALCULATE ( MAX ( dDATAS[PTAX] ) ) ) )", USD)
  + meas("tpmoedalog", 'IF ( SELECTEDVALUE ( TipoMoeda[Moeda], "Real" ) = "Real", [valorreallog], [ValorEmUSDlogmed] )', BRL, DYN)
  + meas("Qtde Serviços LOGMED", f"SUM ( {L}[Quantidade] )", "#,0")
  + meas("Preço Médio LOGMED", "DIVIDE ( [valorreallog], [Qtde Serviços LOGMED] )", BRL2)
  + meas("Valor Mês Anterior LOGMED", "VAR _d = MAX ( dDATAS[Data] ) RETURN CALCULATE ( [valorreallog], REMOVEFILTERS ( dDATAS ), dDATAS[Data] = EDATE ( _d, -1 ) )", BRL)
  + meas("Var % Mês LOGMED", "VAR _a = [Valor Mês Anterior LOGMED] RETURN IF ( NOT ISBLANK ( _a ), DIVIDE ( [valorreallog] - _a, _a ) )", "▲ 0.0%;▼ 0.0%;0.0%")
  + meas("Cor Var LOGMED", 'IF ( [Var % Mês LOGMED] > 0, "#D64545", "#2E9E6B" )')
  + meas("Acumulado Ano LOGMED", "VAR _d = MAX ( dDATAS[Data] ) RETURN CALCULATE ( [valorreallog], REMOVEFILTERS ( dDATAS ), dDATAS[Ano] = YEAR ( _d ), dDATAS[Data] <= _d )", BRL)
)
cols_log = (col("SERVIÇO","string") + col("Quantidade","double","#,0.##") + col("Valor","decimal",BRL2) + col("Total","decimal",BRL)
  + col("MÊS","string") + col("FILIAL","string") + col("BU","string") + col("TÍTULO","string") + col("ANO","string") + col("DataRef","dateTime","Short Date"))
table("LOGMED-Serviços", mes_log + cols_log + part("LOGMED-Serviços", M_LOGSERV))

cols_d = (col("Data","dateTime","Short Date") + col("Ano","int64","0") + col("Mês","int64","0")
  + col("NomeMês","string",sort="Mês") + col("AnoMês","string") + col("MêsAno","string",sort="Data")
  + col("Trimestre","string") + col("PTAX","double","0.0000"))
table("dDATAS", "\tdataCategory: Time\n\n" + cols_d + part("dDATAS", M_DDATAS))
table("FILIAISENDOLOG", col("FILIAL","string") + part("FILIAISENDOLOG", M_FILIAIS))
table("TipoMoeda", col("Moeda","string") + part("TipoMoeda", M_MOEDA))
table("Atualizacao", col("Data","dateTime","General Date") + part("Atualizacao", M_ATU), hidden=True)

# ----------------------------------------------------------------- expressions
G = "Funções e consultas auxiliares"
E = (expr("pTaxaDolarPadrao", '5.5 meta [IsParameterQuery=true, Type="Number", IsParameterQueryRequired=true]', G, "Number")
   + expr("PastaFaturas", M_PASTA, G)
   + expr("fxLerAba", M_LERABA, G, "Function")
   + expr("fxNumero", M_NUMERO, G, "Function")
   + expr("fxMes", M_MES, G, "Function")
   + expr("fxDataReferencia", M_DATAREF, G, "Function")
   + expr("Cambio", M_CAMBIO, G)
   + expr("FRETES", m_endolog("Base Unificada Fretes Endolog.xlsx"), G)
   + expr("Serviços", m_endolog("Base Unificada Serviços Endolog.xlsx"), G)
   + expr("LOGMED_armazenagem", m_logmed("Armazenagem"), G)
   + expr("LOGMED_atendimento", m_logmed("atendimentos"), G))
w("expressions.tmdl", E)

# ----------------------------------------------------------------- relationships
R = ""
for i,(a,b) in enumerate([("Fatura_Endolog.DataRef","dDATAS.Data"),("'LOGMED-Serviços'.DataRef","dDATAS.Data"),
                          ("Fatura_Endolog.FILIAL","FILIAISENDOLOG.FILIAL"),("'LOGMED-Serviços'.FILIAL","FILIAISENDOLOG.FILIAL")]):
    R += f"relationship {uuid.uuid4()}\n\tfromColumn: {a}\n\ttoColumn: {b}\n\n"
w("relationships.tmdl", R)

w("database.tmdl", "database\n\tcompatibilityLevel: 1567\n")
tabs = ["Fatura_Endolog","LOGMED-Serviços","dDATAS","FILIAISENDOLOG","TipoMoeda","Atualizacao"]
order = ["pTaxaDolarPadrao","PastaFaturas","fxLerAba","fxNumero","fxMes","fxDataReferencia","Cambio","FRETES","Serviços","Fatura_Endolog",
         "LOGMED_armazenagem","LOGMED_atendimento","LOGMED-Serviços","dDATAS","FILIAISENDOLOG","TipoMoeda","Atualizacao"]
mdl = ("model Model\n\tculture: pt-BR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: pt-BR\n"
       "\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
       f"queryGroup '{G}'\n\n"
       f"annotation PBI_QueryOrder = {json.dumps(order, ensure_ascii=False)}\n\nannotation __PBI_TimeIntelligenceEnabled = 0\n\n"
       + "".join(f"ref table {('\'' + t + '\'') if '-' in t else t}\n" for t in tabs) + "")
w("model.tmdl", mdl)

with open(os.path.join(OUT, "definition.pbism"), "w") as f:
    json.dump({"version": "4.0", "settings": {}}, f)
with open(os.path.join(OUT, ".platform"), "w") as f:
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
               "metadata": {"type": "SemanticModel", "displayName": "FaturasEndolog_Executivo"},
               "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}}, f, indent=2)
print("modelo ok")
