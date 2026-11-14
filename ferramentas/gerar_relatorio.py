"""Gera FaturasEndolog_Executivo.Report (layout legado report.json) a partir do pbix original,
com os visuais já ligados às medidas novas."""
import json, copy, zipfile, sys, uuid, os, shutil
SRC, OUT, THEME = sys.argv[1], sys.argv[2], sys.argv[3]
NAVY = "#000075"
z = zipfile.ZipFile(SRC)
L = json.loads(z.read("Report/Layout").decode("utf-16-le"))

def lit(v): return {"expr": {"Literal": {"Value": v}}}
def cor(c): return {"solid": {"color": lit(f"'{c}'")}}

# ---------- tema ----------
THEME_NAME = "AbbottExecutivo.json"
for rp in L["resourcePackages"]:
    p = rp["resourcePackage"]
    if p["name"] == "RegisteredResources":
        for it in p["items"]:
            if it["name"].startswith("Sunflower"):
                it["name"] = it["path"] = THEME_NAME
L["theme"] = THEME_NAME
cfg = json.loads(L["config"])
cfg["themeCollection"]["customTheme"]["name"] = THEME_NAME
L["config"] = json.dumps(cfg, ensure_ascii=False)
L.pop("publicCustomVisuals", None)

# ---------- helpers de campos ----------
ALIAS = {"Fatura_Endolog": "f", "LOGMED-Serviços": "l", "dDATAS": "d", "FILIAISENDOLOG": "fi", "TipoMoeda": "t"}
def C(tab, prop):   # coluna
    return {"Column": {"Expression": {"SourceRef": {"Source": ALIAS[tab]}}, "Property": prop}, "Name": f"{tab}.{prop}", "NativeReferenceName": prop}, tab
def M(tab, prop):   # medida
    return {"Measure": {"Expression": {"SourceRef": {"Source": ALIAS[tab]}}, "Property": prop}, "Name": f"{tab}.{prop}", "NativeReferenceName": prop}, tab

def campos(v, roles, order_desc=None, extras=(), nomes=None):
    """roles: {"Category":[(sel,tab)], "Y":[...], ...}. Reescreve a consulta do visual."""
    c = json.loads(v["config"]); sv = c["singleVisual"]
    tabs, sel, proj = [], [], {}
    for role, items in roles.items():
        proj[role] = []
        for i, (s, tab) in enumerate(items):
            if tab not in tabs: tabs.append(tab)
            sel.append(s)
            p = {"queryRef": s["Name"]}
            if role in ("Category", "Rows", "Columns") and i == 0: p["active"] = True
            proj[role].append(p)
    for s_, tab in extras:
        if tab not in tabs: tabs.append(tab)
        sel.append(s_)
    q = {"Version": 2, "From": [{"Name": ALIAS[t], "Entity": t, "Type": 0} for t in tabs], "Select": sel}
    if order_desc:
        q["OrderBy"] = [{"Direction": 2, "Expression": {k: v2 for k, v2 in order_desc.items() if k != "Name" and k != "NativeReferenceName"}}]
    sv["prototypeQuery"] = q
    sv["projections"] = proj
    for k in ("columnProperties", "hasDefaultSort"): sv.pop(k, None)
    if nomes: sv["columnProperties"] = {k: {"displayName": n} for k, n in nomes.items()}
    for k in ("query", "dataTransforms"): v.pop(k, None)
    v["filters"] = "[]"
    c["singleVisual"] = sv
    v["config"] = json.dumps(c, ensure_ascii=False)

CORES = ("color", "Color", "enableBackground", "showBackground", "backgroundTransparency")
def limpar(o):
    if isinstance(o, dict):
        for k in [k for k in o if any(t in k for t in CORES)]: o.pop(k)
        for x in o.values(): limpar(x)
    elif isinstance(o, list):
        for x in o: limpar(x)

def mover(v, x, y, w, h, z=None):
    c = json.loads(v["config"])
    v["x"], v["y"], v["width"], v["height"] = x, y, w, h
    for lay in c.get("layouts", []):
        lay["position"].update({"x": x, "y": y, "width": w, "height": h})
        if z is not None: lay["position"]["z"] = z
    if z is not None: v["z"] = z
    v["config"] = json.dumps(c, ensure_ascii=False)

def formatar(v, titulo=None, rotulos=True):
    c = json.loads(v["config"]); sv = c["singleVisual"]
    vc = sv.setdefault("vcObjects", {})
    for k in ("background", "border", "dropShadow", "subTitle"): vc.pop(k, None)
    if titulo is not None:
        vc["title"] = [{"properties": {"show": lit("true"), "text": lit("'" + titulo.replace("'", "''") + "'"),
                                        "fontColor": cor("#1B2A3A"), "fontSize": lit("12D")}}]
    ob = sv.setdefault("objects", {})
    ob.pop("dataPoint", None); limpar(ob); limpar({k: x for k, x in vc.items() if k != "title"})
    t = sv.get("visualType")
    if t == "slicer":
        hd = (ob.get("header") or [{"properties": {}}])[0].get("properties", {}); hd["show"] = lit("true")
        ob["header"] = [{"properties": hd}]
    if t in ("clusteredBarChart", "lineStackedColumnComboChart", "lineChart"):
        ob.setdefault("categoryAxis", [{"properties": {}}])[0]["properties"]["show"] = lit("true")
        lab = ob.setdefault("labels", [{"properties": {}}])[0]["properties"]
        lab["show"] = lit("true" if rotulos else "false")
    if t == "card":
        ob["labels"] = [{"properties": {"fontSize": lit("26D")}}]
        ob["categoryLabels"] = [{"properties": {"show": lit("true"), "fontSize": lit("10D")}}]
    v["config"] = json.dumps(c, ensure_ascii=False)

def texto(v, t, tam="16pt", cor_txt="#ffffff"):
    c = json.loads(v["config"])
    c["singleVisual"]["objects"]["general"] = [{"properties": {"paragraphs": [{"textRuns": [
        {"value": t, "textStyle": {"fontWeight": "bold", "fontSize": tam, "color": cor_txt}}]}]}}]
    c["singleVisual"].setdefault("vcObjects", {})["background"] = [{"properties": {"show": lit("false")}}]
    v["config"] = json.dumps(c, ensure_ascii=False)

def faixa(v):
    c = json.loads(v["config"]); ob = c["singleVisual"]["objects"]
    ob["shape"] = [{"properties": {"tileShape": lit("'rectangle'")}}]
    ob["fill"] = [{"properties": {"show": lit("true"), "fillColor": cor(NAVY), "transparency": lit("0D")}}]
    ob["outline"] = [{"properties": {"show": lit("false")}}]
    v["config"] = json.dumps(c, ensure_ascii=False)

def clonar(v):
    n = copy.deepcopy(v); c = json.loads(n["config"])
    c["name"] = uuid.uuid4().hex[:20]; n["config"] = json.dumps(c, ensure_ascii=False)
    n.pop("id", None); n.pop("tabOrder", None)
    return n

def tipo(v):
    c = json.loads(v["config"]); sv = c.get("singleVisual", {})
    return sv.get("visualType"), {s.get("Name", "") for s in sv.get("prototypeQuery", {}).get("Select", [])}

def slicer_cfg(v, titulo, selecao=None, horizontal=False):
    c = json.loads(v["config"]); sv = c["singleVisual"]; ob = sv.setdefault("objects", {})
    ob["header"] = [{"properties": {"show": lit("true"), "text": lit(f"'{titulo}'"), "textSize": lit("10D")}}]
    ob["data"] = [{"properties": {"mode": lit("'Basic'" if horizontal else "'Dropdown'")}}]
    ob["general"] = [{"properties": ({"orientation": lit("2D")} if horizontal else {})}]
    if selecao:
        tab, prop, val = selecao
        ob["general"][0]["properties"]["filter"] = {"filter": {"Version": 2, "From": [{"Name": "s", "Entity": tab, "Type": 0}],
            "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": prop}}],
                                             "Values": [[{"Literal": {"Value": val}}]]}}}]}}
    ob["selection"] = [{"properties": {"singleSelect": lit("true" if horizontal else "false"), "selectAllCheckboxEnabled": lit("false")}}]
    v["config"] = json.dumps(c, ensure_ascii=False)

def card_header(v, medida_tab, medida):
    """Cartão branco sobre a faixa azul (período / atualização)."""
    campos(v, {"Values": [M(medida_tab, medida)]})
    c = json.loads(v["config"]); sv = c["singleVisual"]
    sv["objects"] = {"labels": [{"properties": {"fontSize": lit("10D"), "color": cor("#FFFFFF"), "wordWrap": lit("true")}}],
                     "categoryLabels": [{"properties": {"show": lit("false")}}]}
    sv["vcObjects"] = {"background": [{"properties": {"show": lit("false")}}], "title": [{"properties": {"show": lit("false")}}],
                       "border": [{"properties": {"show": lit("false")}}]}
    v["config"] = json.dumps(c, ensure_ascii=False)

def fundo_pagina(s):
    c = json.loads(s.get("config") or "{}"); c.setdefault("objects", {})
    for k in ("background", "outspace", "wallpaper"): c["objects"].pop(k, None)
    s["config"] = json.dumps(c, ensure_ascii=False)
    s["width"], s["height"], s["displayOption"] = 1280, 720, 1

S = {s["displayName"]: s for s in L["sections"]}
HDR, MG = 56, 16
KW = (1248 - 36) / 4

def pegar(vs, t, pred=lambda cp: True, remove=False):
    for v in vs:
        tt, cp = tipo(v)
        if tt == t and pred(cp):
            if remove: vs.remove(v)
            return v
    raise KeyError(t)

MODELO = S["Faturas ENDOLOG"]
moeda_modelo = pegar(S["Cost Drive"]["visualContainers"], "slicer", lambda cp: "TipoMoeda.Moeda" in cp)

def cabecalho(s, titulo, novo=False):
    vs = s["visualContainers"]
    if novo:
        shape = clonar(pegar(MODELO["visualContainers"], "shape")); vs.append(shape)
        img = clonar(pegar(MODELO["visualContainers"], "image")); vs.append(img)
        tb = clonar(pegar(MODELO["visualContainers"], "textbox")); vs.append(tb)
    else:
        shape, img, tb = pegar(vs, "shape"), pegar(vs, "image"), pegar(vs, "textbox")
    faixa(shape); mover(shape, 0, 0, 1280, HDR, z=0)
    ci = json.loads(img["config"])
    ci["singleVisual"]["objects"]["imageScaling"] = [{"properties": {"imageScalingType": lit("'Fit'")}}]
    ci["singleVisual"].setdefault("vcObjects", {})["background"] = [{"properties": {"show": lit("false")}}]
    img["config"] = json.dumps(ci, ensure_ascii=False)
    mover(img, MG, 6, 130, 44, z=90000)
    texto(tb, titulo); mover(tb, 156, 2, 640, 52, z=91000)
    info = clonar(pegar(MODELO["visualContainers"], "card")); card_header(info, "Fatura_Endolog", "Cabeçalho Info")
    mover(info, 820, 4, 444, 48, z=92000); vs.append(info)
    return vs

def filtros(vs, lista, moeda=True):
    """lista: [(slicer, titulo, campo, selecao)] -> linha abaixo do cabeçalho."""
    for i, (v, titulo, campo, sel) in enumerate(lista):
        campos(v, {"Values": [campo]}); formatar(v); slicer_cfg(v, titulo, sel)
        mover(v, MG + i * 178, HDR + 8, 170, 52)
    if moeda:
        m = clonar(moeda_modelo); campos(m, {"Values": [C("TipoMoeda", "Moeda")]}); formatar(m)
        slicer_cfg(m, "Moeda", ("TipoMoeda", "Moeda", "'Real'"), horizontal=True)
        mover(m, 1264 - 170, HDR + 8, 170, 52); vs.append(m)

def pagina_fatura(s, titulo, T, medidas, campo_titulo, campo_tipo, campo_bu):
    vs = cabecalho(s, titulo)
    sl = [v for v in vs if tipo(v)[0] == "slicer"]
    ano = pegar(sl, "slicer", lambda cp: any("ANO" in x or "Ano" in x for x in cp))
    mes = pegar(sl, "slicer", lambda cp: "dDATAS.NomeMês" in cp)
    fil = pegar(sl, "slicer", lambda cp: any("FILIAL" in x for x in cp))
    bu = pegar(sl, "slicer", lambda cp: any(".BU" in x for x in cp))
    tit = clonar(bu); vs.append(tit)
    filtros(vs, [(ano, "Ano", C("dDATAS", "Ano"), ("dDATAS", "Ano", "2026L")),
                 (mes, "Mês", C("dDATAS", "NomeMês"), None),
                 (fil, "Filial", C("FILIAISENDOLOG", "FILIAL"), None),
                 (bu, "BU", C(T, campo_bu), None),
                 (tit, "Título", C(T, campo_titulo), None)])
    cards = [v for v in vs if tipo(v)[0] == "card" and not any("Cabeçalho Info" in x for x in tipo(v)[1])]
    while len(cards) < 4:
        n = clonar(cards[0]); vs.append(n); cards.append(n)
    nomes = [("Valor cobrado", medidas["valor"]), ("Qtde de serviços", medidas["qtde"]),
             ("Preço médio por serviço", medidas["preco"]), ("Variação vs mês anterior", medidas["var"])]
    for i, (v, (nome, med)) in enumerate(zip(cards, nomes)):
        if i == 3:
            campos(v, {"Values": [M(T, med)]}, extras=[M(T, medidas["cor"])]); formatar(v, nome)
            c = json.loads(v["config"]); c["singleVisual"]["objects"]["labels"] = [{"properties": {"fontSize": lit("26D"),
                "color": {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": T}}, "Property": medidas["cor"]}}}}}}}]
            v["config"] = json.dumps(c, ensure_ascii=False)
        else:
            campos(v, {"Values": [M(T, med)]}); formatar(v, nome)
        mover(v, MG + i * (KW + 12), 124, KW, 84)
    y2, y3, y4 = 220, 422, 604
    ln = pegar(vs, "lineChart"); campos(ln, {"Category": [C("dDATAS", "MêsAno")], "Y": [M(T, medidas["valor"])]})
    formatar(ln, "Evolução mensal do valor cobrado"); mover(ln, MG, y2, 760, 190)
    dn = pegar(vs, "donutChart"); campos(dn, {"Category": [C("FILIAISENDOLOG", "FILIAL")], "Y": [M(T, medidas["valor"])]})
    formatar(dn, "Participação por filial"); mover(dn, 788, y2, 476, 190)
    b1 = pegar(vs, "clusteredBarChart", lambda cp: any("TÍTULO" in x for x in cp))
    campos(b1, {"Category": [C(T, campo_titulo)], "Y": [M(T, medidas["valor"])]}, order_desc=M(T, medidas["valor"])[0])
    formatar(b1, "Valor por título"); mover(b1, MG, y3, 400, 170)
    b2 = pegar(vs, "clusteredBarChart", lambda cp: not any("TÍTULO" in x for x in cp))
    campos(b2, {"Category": [C(T, campo_tipo)], "Y": [M(T, medidas["preco"])]}, order_desc=M(T, medidas["preco"])[0])
    formatar(b2, "Preço médio por tipo de serviço"); mover(b2, 428, y3, 400, 170)
    cb = pegar(vs, "lineStackedColumnComboChart")
    campos(cb, {"Category": [C("FILIAISENDOLOG", "FILIAL")], "Y": [M(T, medidas["valor"])]})
    formatar(cb, "Valor por filial (last mile)"); mover(cb, 840, y3, 424, 170)
    tb = pegar(vs, "tableEx")
    campos(tb, {"Values": [C(T, "FILIAL"), C(T, campo_bu), C(T, campo_tipo), C(T, campo_titulo), C("dDATAS", "MêsAno"),
                           M(T, medidas["qtde"]), M(T, medidas["preco"]), M(T, medidas["valor"])]},
           nomes={f"{T}.FILIAL": "Filial", f"{T}.{campo_bu}": "BU", f"{T}.{campo_tipo}": "Tipo de serviço", f"{T}.{campo_titulo}": "Título",
                  "dDATAS.MêsAno": "Mês", f"{T}.{medidas['qtde']}": "Qtde", f"{T}.{medidas['preco']}": "Preço médio", f"{T}.{medidas['valor']}": "Cobrado"})
    formatar(tb, "Detalhe das faturas"); mover(tb, MG, y4, 1248, 104)
    fundo_pagina(s)

pagina_fatura(S["Faturas ENDOLOG"], "Faturas Last Mile – ENDOLOG", "Fatura_Endolog",
              dict(valor="VALORREAL", qtde="Qtde Serviços Endolog", preco="Preço Médio Endolog", var="Var % Mês Endolog", cor="Cor Var Endolog"),
              "TÍTULO", "TIPO DE SERVIÇO", "BU")
pagina_fatura(S["Faturas LOGMED"], "Faturas Last Mile – LOGMED", "LOGMED-Serviços",
              dict(valor="valorreallog", qtde="Qtde Serviços LOGMED", preco="Preço Médio LOGMED", var="Var % Mês LOGMED", cor="Cor Var LOGMED"),
              "TÍTULO", "SERVIÇO", "BU")

# ---------- Cost Drive ----------
cd = S["Cost Drive"]
vs = cabecalho(cd, "Cost Drive – Endolog + LOGMED", novo=True)
sl = [v for v in vs if tipo(v)[0] == "slicer"]
def sl_get(pred):
    return pegar(sl, "slicer", pred)
moeda = sl_get(lambda cp: "TipoMoeda.Moeda" in cp); vs.remove(moeda)
f_fil = sl_get(lambda cp: "Fatura_Endolog.FILIAL" in cp)
l_fil = sl_get(lambda cp: "LOGMED-Serviços.FILIAL" in cp)
f_bu = sl_get(lambda cp: "Fatura_Endolog.BU" in cp); f_tit = sl_get(lambda cp: "Fatura_Endolog.TÍTULO" in cp)
l_bu = sl_get(lambda cp: "LOGMED-Serviços.BU" in cp); l_tit = sl_get(lambda cp: "LOGMED-Serviços.TÍTULO" in cp)
lista = [(l_fil, "Ano", C("dDATAS", "Ano"), ("dDATAS", "Ano", "2026L")), (f_fil, "Filial", C("FILIAISENDOLOG", "FILIAL"), None),
         (f_bu, "BU Endolog", C("Fatura_Endolog", "BU"), None), (f_tit, "Título Endolog", C("Fatura_Endolog", "TÍTULO"), None),
         (l_bu, "BU LOGMED", C("LOGMED-Serviços", "BU"), None), (l_tit, "Título LOGMED", C("LOGMED-Serviços", "TÍTULO"), None)]
w = (1248 - 170 - 12 - 5 * 8) / 6
for i, (v, titulo, campo, sel) in enumerate(lista):
    campos(v, {"Values": [campo]}); formatar(v); slicer_cfg(v, titulo, sel); mover(v, MG + i * (w + 8), HDR + 8, w, 52)
m = clonar(moeda_modelo); campos(m, {"Values": [C("TipoMoeda", "Moeda")]}); formatar(m)
slicer_cfg(m, "Moeda", ("TipoMoeda", "Moeda", "'Real'"), horizontal=True); mover(m, 1264 - 170, HDR + 8, 170, 52); vs.append(m)
kpis = [("Total faturado", "Fatura_Endolog", "Total Faturado"), ("Peso Endolog no total", "Fatura_Endolog", "Peso Endolog %"),
        ("Acumulado no ano – Endolog", "Fatura_Endolog", "Acumulado Ano Endolog"), ("Acumulado no ano – LOGMED", "LOGMED-Serviços", "Acumulado Ano LOGMED")]
for i, (nome, tab, med) in enumerate(kpis):
    v = clonar(pegar(MODELO["visualContainers"], "card", lambda cp: not any("Cabeçalho Info" in x for x in cp))); vs.append(v)
    campos(v, {"Values": [M(tab, med)]}); formatar(v, nome); mover(v, MG + i * (KW + 12), 124, KW, 84)
piv_e = pegar(vs, "pivotTable", lambda cp: any("Fatura_Endolog" in x for x in cp))
piv_l = pegar(vs, "pivotTable", lambda cp: any("LOGMED" in x for x in cp))
campos(piv_e, {"Rows": [C("Fatura_Endolog", "TIPO DE SERVIÇO")], "Columns": [C("dDATAS", "MêsAno")], "Values": [M("Fatura_Endolog", "VALORREAL")]},
       nomes={"Fatura_Endolog.TIPO DE SERVIÇO": "Tipo de serviço", "Fatura_Endolog.VALORREAL": "Valor"})
campos(piv_l, {"Rows": [C("LOGMED-Serviços", "SERVIÇO")], "Columns": [C("dDATAS", "MêsAno")], "Values": [M("LOGMED-Serviços", "valorreallog")]},
       nomes={"LOGMED-Serviços.SERVIÇO": "Serviço", "LOGMED-Serviços.valorreallog": "Valor"})
formatar(piv_e, "ENDOLOG – valor por tipo de serviço e mês"); mover(piv_e, MG, 220, 618, 290)
formatar(piv_l, "LOGMED – valor por tipo de serviço e mês"); mover(piv_l, 646, 220, 618, 290)
for v in list(vs):
    if tipo(v)[0] == "textbox":
        txt = json.loads(v["config"])["singleVisual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"]
        if txt in ("ENDOLOG", "LOGMED"): vs.remove(v)
tot = clonar(pegar(MODELO["visualContainers"], "lineChart")); vs.append(tot)
campos(tot, {"Category": [C("dDATAS", "MêsAno")], "Y": [M("Fatura_Endolog", "VALORREAL"), M("LOGMED-Serviços", "valorreallog")]},
       nomes={"Fatura_Endolog.VALORREAL": "Endolog", "LOGMED-Serviços.valorreallog": "LOGMED"})
formatar(tot, "Total faturado por mês – Endolog e LOGMED", rotulos=False); mover(tot, MG, 522, 1248, 186)
c = json.loads(tot["config"]); c["singleVisual"]["objects"]["legend"] = [{"properties": {"show": lit("true"), "position": lit("'Top'")}}]
tot["config"] = json.dumps(c, ensure_ascii=False)
fundo_pagina(cd)

# ---------- páginas quebradas: removidas (tabelas não existem no modelo) ----------
L["sections"] = [S["Faturas ENDOLOG"], S["Faturas LOGMED"], S["Cost Drive"]]
for i, s in enumerate(L["sections"]):
    s["ordinal"] = i
    for j, v in enumerate(s["visualContainers"]):
        v["tabOrder"] = j * 100
        v.pop("id", None)
    s.pop("id", None)
L.pop("id", None)

# ---------- grava ----------
os.makedirs(os.path.join(OUT, "StaticResources", "RegisteredResources"), exist_ok=True)
with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
    json.dump(L, f, ensure_ascii=False)
for it in z.infolist():
    if it.filename.startswith("Report/StaticResources/") and not it.filename.endswith("Sunflower_Twilight4218505826991814.json"):
        dest = os.path.join(OUT, it.filename[len("Report/"):])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "wb").write(z.read(it.filename))
shutil.copy(THEME, os.path.join(OUT, "StaticResources", "RegisteredResources", THEME_NAME))
with open(os.path.join(OUT, "definition.pbir"), "w") as f:
    json.dump({"version": "1.0", "datasetReference": {"byPath": {"path": "../FaturasEndolog_Executivo.SemanticModel"}}}, f, indent=2)
with open(os.path.join(OUT, ".platform"), "w") as f:
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
               "metadata": {"type": "Report", "displayName": "FaturasEndolog_Executivo"},
               "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}}, f, indent=2)
print("relatório ok")
