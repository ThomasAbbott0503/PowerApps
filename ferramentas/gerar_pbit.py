"""Gera FaturasEndolog_Executivo.pbit (modelo de template do Power BI): modelo TMSL + layout pronto.
Reaproveita as definições (M, medidas) de gerar_modelo.py e o layout de gerar_relatorio.py."""
import json, zipfile, sys, os, re, importlib.util, runpy

SRC, OUT, THEME, REPORT_JSON = sys.argv[1:5]

# ---------- carrega definições M e medidas do gerador TMDL (sem executar a gravação) ----------
src = open(os.path.join(os.path.dirname(__file__), "gerar_modelo.py"), encoding="utf-8").read()
src = src.split("# ----------------------------------------------------------------- TMDL helpers")[0] + "\n" + src[src.index("CG_DOLAR = "):src.index("tm = (")]
src = src.replace('OUT = sys.argv[1]', 'OUT = "/tmp/_x"').replace('os.makedirs(os.path.join(D, "tables"), exist_ok=True)', '').replace('os.makedirs(os.path.join(D, "cultures"), exist_ok=True)', '')
ns = {}; exec(src, ns)

BRL, BRL2, USD, DYN = ns["BRL"], ns["BRL2"], ns["USD"], ns["DYN"]
F, L = "Fatura_Endolog", "LOGMED-Serviços"

def col(name, dt, fmt=None, sort=None, hidden=False):
    c = {"name": name, "dataType": dt, "sourceColumn": name, "summarizeBy": "none"}
    if fmt: c["formatString"] = fmt
    if sort: c["sortByColumn"] = sort
    if hidden: c["isHidden"] = True
    return c

def meas(name, dax, fmt=None, dyn=None):
    m = {"name": name, "expression": dax}
    if fmt: m["formatString"] = fmt
    if dyn: m["formatStringDefinition"] = {"expression": dyn}
    return m

def part(name, m):
    return [{"name": name, "mode": "import", "source": {"type": "m", "expression": m.strip("\n").splitlines()}}]

VAR_FMT = "▲ 0.0%;▼ 0.0%;0.0%"
mes_endolog = [
    meas("VALORREAL", f"SUM ( {F}[COBRADO] )", BRL),
    meas("VALORDOLAR", "SUMX ( VALUES ( dDATAS[Data] ), DIVIDE ( [VALORREAL], CALCULATE ( MAX ( dDATAS[PTAX] ) ) ) )", USD),
    meas("Qtde Serviços Endolog", f"SUM ( {F}[QTDE] )", "#,0"),
    meas("Preço Médio Endolog", "DIVIDE ( [VALORREAL], [Qtde Serviços Endolog] )", BRL2),
    meas("Valor Mês Anterior Endolog", "VAR _d = MAX ( dDATAS[Data] ) RETURN CALCULATE ( [VALORREAL], REMOVEFILTERS ( dDATAS ), dDATAS[Data] = EDATE ( _d, -1 ) )", BRL),
    meas("Var % Mês Endolog", "VAR _a = [Valor Mês Anterior Endolog] RETURN IF ( NOT ISBLANK ( _a ), DIVIDE ( [VALORREAL] - _a, _a ) )", VAR_FMT),
    meas("Cor Var Endolog", 'IF ( [Var % Mês Endolog] > 0, "#D64545", "#2E9E6B" )'),
    meas("Acumulado Ano Endolog", "VAR _d = MAX ( dDATAS[Data] ) RETURN CALCULATE ( [VALORREAL], REMOVEFILTERS ( dDATAS ), dDATAS[Ano] = YEAR ( _d ), dDATAS[Data] <= _d )", BRL),
    meas("Total Faturado", "[VALORREAL] + [valorreallog]", BRL),
    meas("Peso Endolog %", "DIVIDE ( [VALORREAL], [Total Faturado] )", "0.0%"),
    meas("Período Selecionado", 'VAR _i = MIN ( dDATAS[Data] ) VAR _f = MAX ( dDATAS[Data] ) RETURN "Período: " & FORMAT ( _i, "mmm/yy" ) & " a " & FORMAT ( _f, "mmm/yy" )'),
    meas("Última Atualização", '"Atualizado em " & FORMAT ( MAX ( Atualizacao[Data] ), "dd/mm/yyyy hh:mm" )'),
    meas("Cabeçalho Info", '[Período Selecionado] & "   |   " & [Última Atualização]'),
]
cols_endolog = [col("FILIAL","string"), col("BU","string"), col("TIPO DE SERVIÇO","string"), col("QTDE","int64","#,0"),
    col("PREÇO","decimal",BRL2), col("COBRADO","decimal",BRL), col("MÊS","string"), col("TÍTULO","string"), col("ANO","string"),
    col("DataRef","dateTime","Short Date")]
mes_log = [
    meas("valorreallog", f"SUM ( '{L}'[Total] )", BRL),
    meas("ValorEmUSDlogmed", "SUMX ( VALUES ( dDATAS[Data] ), DIVIDE ( [valorreallog], CALCULATE ( MAX ( dDATAS[PTAX] ) ) ) )", USD),
    meas("Qtde Serviços LOGMED", f"SUM ( '{L}'[Quantidade] )", "#,0"),
    meas("Preço Médio LOGMED", "DIVIDE ( [valorreallog], [Qtde Serviços LOGMED] )", BRL2),
    meas("Valor Mês Anterior LOGMED", "VAR _d = MAX ( dDATAS[Data] ) RETURN CALCULATE ( [valorreallog], REMOVEFILTERS ( dDATAS ), dDATAS[Data] = EDATE ( _d, -1 ) )", BRL),
    meas("Var % Mês LOGMED", "VAR _a = [Valor Mês Anterior LOGMED] RETURN IF ( NOT ISBLANK ( _a ), DIVIDE ( [valorreallog] - _a, _a ) )", VAR_FMT),
    meas("Cor Var LOGMED", 'IF ( [Var % Mês LOGMED] > 0, "#D64545", "#2E9E6B" )'),
    meas("Acumulado Ano LOGMED", "VAR _d = MAX ( dDATAS[Data] ) RETURN CALCULATE ( [valorreallog], REMOVEFILTERS ( dDATAS ), dDATAS[Ano] = YEAR ( _d ), dDATAS[Data] <= _d )", BRL),
]
cols_log = [col("SERVIÇO","string"), col("Quantidade","double","#,0.##"), col("Valor","decimal",BRL2), col("Total","decimal",BRL),
    col("MÊS","string"), col("FILIAL","string"), col("BU","string"), col("TÍTULO","string"), col("ANO","string"), col("DataRef","dateTime","Short Date")]
cols_d = [col("Data","dateTime","Short Date"), col("Ano","int64","0"), col("Mês","int64","0"), col("NomeMês","string",sort="Mês"),
    col("AnoMês","string"), col("MêsAno","string",sort="Data"), col("Trimestre","string"), col("PTAX","double","0.0000")]

tables = [
    {"name": F, "columns": cols_endolog, "measures": mes_endolog, "partitions": part(F, ns["M_FATURA"])},
    {"name": L, "columns": cols_log, "measures": mes_log, "partitions": part(L, ns["M_LOGSERV"])},
    {"name": "dDATAS", "dataCategory": "Time", "columns": cols_d, "partitions": part("dDATAS", ns["M_DDATAS"])},
    {"name": "FILIAISENDOLOG", "columns": [col("FILIAL","string")], "partitions": part("FILIAISENDOLOG", ns["M_FILIAIS"])},
    {"name": "TipoMoeda",
     "calculationGroup": {"precedence": 0, "calculationItems": [
         {"name": "Real", "ordinal": 0, "expression": "SELECTEDMEASURE()", "formatStringDefinition": {"expression": "SELECTEDMEASUREFORMATSTRING()"}},
         {"name": "Dolar", "ordinal": 1, "expression": ns["CG_DOLAR"].strip("\n").splitlines(),
          "formatStringDefinition": {"expression": ns["CG_DOLAR_FMT"].strip("\n").splitlines()}}]},
     "columns": [col("Moeda","string",sort="Ordinal") | {"sourceColumn": "Name"}, col("Ordinal","int64",hidden=True)],
     "partitions": [{"name": "TipoMoeda", "mode": "import", "source": {"type": "calculationGroup"}}]},
    {"name": "Atualizacao", "isHidden": True, "columns": [col("Data","dateTime","General Date")], "partitions": part("Atualizacao", ns["M_ATU"])},
]
for t in tables:
    if "calculationGroup" not in t: t["annotations"] = [{"name": "PBI_ResultType", "value": "Table"}]

G = "Funções e consultas auxiliares"
def expr(name, m, result="Table"):
    e = {"name": name, "kind": "m", "expression": m.strip("\n").splitlines() if "\n" in m.strip() else m.strip(),
         "queryGroup": G, "annotations": [{"name": "PBI_ResultType", "value": result}]}
    return e
expressions = [
    expr("pTaxaDolarPadrao", '5.5 meta [IsParameterQuery=true, Type="Number", IsParameterQueryRequired=true]', "Number"),
    expr("PastaFaturas", ns["M_PASTA"]), expr("fxLerAba", ns["M_LERABA"], "Function"), expr("fxNumero", ns["M_NUMERO"], "Function"),
    expr("fxMes", ns["M_MES"], "Function"), expr("fxDataReferencia", ns["M_DATAREF"], "Function"), expr("Cambio", ns["M_CAMBIO"]),
    expr("FRETES", ns["m_endolog"]("Base Unificada Fretes Endolog.xlsx")), expr("Serviços", ns["m_endolog"]("Base Unificada Serviços Endolog.xlsx")),
    expr("LOGMED_armazenagem", ns["m_logmed"]("Armazenagem")), expr("LOGMED_atendimento", ns["m_logmed"]("atendimentos")),
]
rels = []
for i, (ft, fc, tt, tc) in enumerate([(F,"DataRef","dDATAS","Data"), (L,"DataRef","dDATAS","Data"),
                                      (F,"FILIAL","FILIAISENDOLOG","FILIAL"), (L,"FILIAL","FILIAISENDOLOG","FILIAL")]):
    rels.append({"name": f"rel{i}", "fromTable": ft, "fromColumn": fc, "toTable": tt, "toColumn": tc})

order = ["pTaxaDolarPadrao","PastaFaturas","fxLerAba","fxNumero","fxMes","fxDataReferencia","Cambio","FRETES","Serviços",F,
         "LOGMED_armazenagem","LOGMED_atendimento",L,"dDATAS","FILIAISENDOLOG","TipoMoeda","Atualizacao"]
schema = {"name": "FaturasEndolog_Executivo", "compatibilityLevel": 1567,
    "model": {"culture": "pt-BR", "defaultPowerBIDataSourceVersion": "powerBI_V3", "sourceQueryCulture": "pt-BR", "discourageImplicitMeasures": True,
              "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
              "tables": tables, "relationships": rels, "expressions": expressions,
              "queryGroups": [{"folder": G}],
              "annotations": [{"name": "PBI_QueryOrder", "value": json.dumps(order, ensure_ascii=False)},
                              {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"}]}}

L_json = json.load(open(REPORT_JSON, encoding="utf-8"))

# ---------- grava o .pbit ----------
z = zipfile.ZipFile(SRC)
ct = z.read("[Content_Types].xml").decode("utf-8-sig")
ct = ct.replace('<Override PartName="/DataModel" ContentType="" />', '<Override PartName="/DataModelSchema" ContentType="" />')
ct = ct.replace('<Override PartName="/SecurityBindings" ContentType="" />', '').replace('<Override PartName="/Connections" ContentType="" />', '')
def u16(obj): return json.dumps(obj, ensure_ascii=False).encode("utf-16-le")
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as o:
    o.writestr("[Content_Types].xml", ct.encode("utf-8"))
    o.writestr("Version", z.read("Version"))
    o.writestr("DataModelSchema", u16(schema))
    o.writestr("DiagramLayout", u16({"version": "1.1.0", "diagrams": []}))
    o.writestr("Report/Layout", u16(L_json))
    o.writestr("Settings", z.read("Settings"))
    o.writestr("Metadata", z.read("Metadata"))
    for it in z.infolist():
        if it.filename.startswith("Report/StaticResources/RegisteredResources/Png"):
            o.writestr(it.filename, z.read(it.filename))
    o.write(THEME, "Report/StaticResources/RegisteredResources/AbbottExecutivo.json")
print("pbit ok", OUT)
