"""Gera FaturasEndolog_Executivo.pbix: aplica tema Abbott e novo layout,
sem mexer no modelo de dados (DataModel fica idêntico)."""
import json, copy, zipfile, shutil, sys, uuid, os

SRC, OUT, THEME = sys.argv[1], sys.argv[2], sys.argv[3]
NAVY, CIANO = "#000075", "#009CDE"
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

# ---------- visuais personalizados não usados ----------
usados = {"textFilter25A4896A83E0487089E2B90C9AE57C8A"}
remover_cv = [c for c in L.get("publicCustomVisuals", []) if c not in usados]
L["publicCustomVisuals"] = [c for c in L.get("publicCustomVisuals", []) if c in usados]

def campos(sv):
    return {s.get("Name", "") for s in sv.get("prototypeQuery", {}).get("Select", [])}

def mover(v, x, y, w, h, z=None):
    c = json.loads(v["config"])
    v["x"], v["y"], v["width"], v["height"] = x, y, w, h
    for lay in c.get("layouts", []):
        lay["position"].update({"x": x, "y": y, "width": w, "height": h})
        if z is not None: lay["position"]["z"] = z
    if z is not None: v["z"] = z
    v["config"] = json.dumps(c, ensure_ascii=False)

def formatar(v, titulo=None):
    """Remove formatação manual (fundo, borda, sombra, cores fixas) para o tema valer."""
    c = json.loads(v["config"]); sv = c.get("singleVisual", {})
    vc = sv.setdefault("vcObjects", {})
    for k in ("background", "border", "dropShadow", "subTitle"):
        vc.pop(k, None)
    if titulo is not None:
        vc["title"] = [{"properties": {"show": lit("true"), "text": lit("'" + titulo.replace("'", "''") + "'"),
                                        "fontColor": cor("#1B2A3A"), "fontSize": lit("12D")}}]
    ob = sv.setdefault("objects", {})
    ob.pop("dataPoint", None)
    for lab in ob.get("labels", []):
        lab.get("properties", {}).pop("color", None)
    v["config"] = json.dumps(c, ensure_ascii=False)

def texto(v, t, tam="18pt", cor_txt="#ffffff"):
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
    n.pop("id", None)
    return n

def tipo(v):
    c = json.loads(v["config"]); sv = c.get("singleVisual", {})
    return sv.get("visualType"), campos(sv)

def fundo_pagina(s):
    c = json.loads(s.get("config") or "{}"); c.setdefault("objects", {})
    for k in ("background", "outspace", "wallpaper"): c["objects"].pop(k, None)
    s["config"] = json.dumps(c, ensure_ascii=False)
    s["width"], s["height"], s["displayOption"] = 1280, 720, 1

S = {s["displayName"]: s for s in L["sections"]}
HDR, M = 56, 16

def cabecalho(s, titulo, modelo=None):
    vs = s["visualContainers"]
    shape = next((v for v in vs if tipo(v)[0] == "shape"), None)
    img = next((v for v in vs if tipo(v)[0] == "image"), None)
    if modelo:  # página sem cabeçalho: copia da página modelo
        shape = clonar(next(v for v in modelo["visualContainers"] if tipo(v)[0] == "shape")); vs.append(shape)
        img = clonar(next(v for v in modelo["visualContainers"] if tipo(v)[0] == "image")); vs.append(img)
        tb = clonar(next(v for v in modelo["visualContainers"] if tipo(v)[0] == "textbox")); vs.append(tb)
    else:
        tb = next(v for v in vs if tipo(v)[0] == "textbox")
    faixa(shape); mover(shape, 0, 0, 1280, HDR, z=0)
    mover(img, M, 8, 110, 40, z=90000)
    texto(tb, titulo); mover(tb, 140, 6, 700, 44, z=91000)

def pagina_fatura(s, titulo, f):
    """f: dicionário com nomes de campos de cada tabela."""
    cabecalho(s, titulo)
    vs = s["visualContainers"]
    sl = [v for v in vs if tipo(v)[0] == "slicer"]
    ordem = [f["ano"], f["mes"], f["filial"], f["bu"]]
    sl.sort(key=lambda v: next((i for i, k in enumerate(ordem) if k in tipo(v)[1]), 9))
    for i, v in enumerate(sl):
        formatar(v); mover(v, M + i * 178, HDR + 8, 170, 52)
    cards = [v for v in vs if tipo(v)[0] == "card"]
    cards.sort(key=lambda v: 0 if f["valor"] in tipo(v)[1] else 1)
    nomes_card = ["Valor cobrado", "Qtde de serviços"]
    for i, v in enumerate(cards):
        formatar(v, nomes_card[i]); mover(v, M + i * 630, 124, 618, 84)
    y2, y3, y4 = 220, 422, 604
    for v in vs:
        t, cp = tipo(v)
        if t == "lineChart":
            formatar(v, "Evolução mensal do valor cobrado"); mover(v, M, y2, 760, 190)
        elif t == "donutChart":
            formatar(v, "Participação por filial"); mover(v, 788, y2, 476, 190)
        elif t == "clusteredBarChart" and f["titulo"] in cp:
            formatar(v, "Valor por título"); mover(v, M, y3, 400, 170)
        elif t == "clusteredBarChart":
            formatar(v, "Preço por tipo de serviço"); mover(v, 428, y3, 400, 170)
        elif t == "lineStackedColumnComboChart":
            formatar(v, "Valor por filial (last mile)"); mover(v, 840, y3, 424, 170)
        elif t == "tableEx":
            formatar(v, "Detalhe das faturas"); mover(v, M, y4, 1248, 104)

pagina_fatura(S["Faturas ENDOLOG"], "Faturas Last Mile – ENDOLOG", dict(
    ano="Ano.Ano", mes="dDATAS.NomeMês", filial="FILIAISENDOLOG.FILIAL", bu="Fatura.BU",
    valor="Sum(Fatura.COBRADO)", titulo="Fatura_Endolog.TÍTULO"))
pagina_fatura(S["Faturas LOGMED"], "Faturas Last Mile – LOGMED", dict(
    ano="LOGMED-Serviços.ANO", mes="dDATAS.NomeMês", filial="LOGMED-Serviços.FILIAL", bu="LOGMED-Serviços.BU",
    valor="Sum(LOGMED-Serviços.Total)", titulo="LOGMED-Serviços.TÍTULO"))

# ---------- Cost Drive ----------
cd = S["Cost Drive"]
cabecalho(cd, "Cost Drive – Endolog + LOGMED", modelo=S["Faturas ENDOLOG"])
vs = cd["visualContainers"]
sl = [v for v in vs if tipo(v)[0] == "slicer"]
pref = ["TipoMoeda.Moeda", "Fatura_Endolog.FILIAL", "Fatura_Endolog.BU", "Fatura_Endolog.TÍTULO",
        "LOGMED-Serviços.FILIAL", "LOGMED-Serviços.BU", "LOGMED-Serviços.TÍTULO"]
sl.sort(key=lambda v: next((i for i, k in enumerate(pref) if k in tipo(v)[1]), 9))
w = (1248 - 6 * 8) / 7
for i, v in enumerate(sl):
    formatar(v); mover(v, M + i * (w + 8), HDR + 8, w, 52)
piv = {("endolog" if any("Fatura_Endolog" in c for c in tipo(v)[1]) else "logmed"): v
       for v in vs if tipo(v)[0] == "pivotTable"}
tbs = [v for v in vs if tipo(v)[0] == "textbox"]
rot = {}
for v in tbs:
    txt = json.loads(v["config"])["singleVisual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"]
    if txt in ("ENDOLOG", "LOGMED"): rot[txt.lower()] = v
formatar(piv["endolog"], "ENDOLOG – valor por tipo de serviço e mês"); mover(piv["endolog"], M, 124, 1248, 290)
formatar(piv["logmed"], "LOGMED – valor por tipo de serviço e mês"); mover(piv["logmed"], M, 422, 1248, 286)
for k, v in rot.items():   # rótulos viraram título do próprio visual
    vs.remove(v)

for nome in ("Faturas ENDOLOG", "Faturas LOGMED", "Cost Drive"):
    fundo_pagina(S[nome])

# ---------- páginas quebradas: ocultar ----------
for nome in ("Saídas Logmed", "validações"):
    c = json.loads(S[nome].get("config") or "{}"); c["visibility"] = 1
    S[nome]["config"] = json.dumps(c, ensure_ascii=False)

# ---------- grava o novo pbix ----------
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as o:
    for it in z.infolist():
        n = it.filename
        if n == "SecurityBindings":  # precisa sair quando o layout muda
            continue
        if n.startswith("Report/StaticResources/RegisteredResources/Sunflower"):
            continue
        if n.startswith("Report/CustomVisuals/") and n.split("/")[2] in remover_cv:
            continue
        if n == "Report/Layout":
            o.writestr(it, json.dumps(L, ensure_ascii=False).encode("utf-16-le")); continue
        if n == "[Content_Types].xml":
            o.writestr(it, z.read(n)); continue
        o.writestr(it, z.read(n), compress_type=it.compress_type)
    o.write(THEME, "Report/StaticResources/RegisteredResources/" + THEME_NAME)
print("ok", OUT, "removidos:", remover_cv)
