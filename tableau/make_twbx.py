"""Generate the packaged Tableau workbook (.twbx) behind the published dashboard.

Writes the workbook XML (data source, 11 calculated fields, 10 sheets, 1400x1100 dashboard) and packs it
with a Hyper extract of exports/orders.csv, because Tableau Public only accepts extract-based workbooks.

    pip install tableauhyperapi
    python tableau/make_twbx.py exports/orders.csv "tableau/QSR Revenue Growth Command Center.twbx"

Final polish (channel colours, sort, tile fit, satisfaction axis 3.3-4.0, grand-total row) was applied in
Tableau Public before publishing.
"""
import sys, zipfile, datetime
from tableauhyperapi import HyperProcess, Telemetry, Connection, CreateMode, TableDefinition, SqlType, TableName, escape_string_literal
from xml.sax.saxutils import quoteattr as qa, escape as esc

CSV = sys.argv[1]; OUT = sys.argv[2]
DS = "federated.0qsrorders0001"; CONN = "textscan.0qsrorders0001"
P = f"[{DS}]"

# (name, datatype) in CSV order
FIELDS = [("Order ID","string"),("Order Date","date"),("Order Month","date"),("Order Timestamp","datetime"),
  ("Order Hour","integer"),("Daypart","string"),("Weekday Number","integer"),("Weekday","string"),
  ("Order Channel","string"),("Is App Order","string"),("Is Order Ahead","string"),("Store ID","string"),
  ("Store Location Type","string"),("Region","string"),("Customer ID","string"),("Age Group","string"),
  ("Gender","string"),("Customer App Adoption","string"),("Is Rewards Member","string"),("Drink Category","string"),
  ("Has Food Item","string"),("Items","integer"),("Customizations","integer"),("Revenue","real"),
  ("Fulfillment Minutes","real"),("Fulfillment Bucket (min)","integer"),("Satisfaction Score","integer")]
DTYPE = dict(FIELDS)

# calculated fields: key -> (caption, formula, datatype, role, type, default-format)
CALCS = {
 "orders":   ("Orders", "COUNT([Order ID])", "integer", "measure", "quantitative", "n#,##0;-#,##0"),
 "revenue":  ("Revenue Total", "SUM([Revenue])", "real", "measure", "quantitative", 'c"$"#,##0;-"$"#,##0'),
 "ticket":   ("Avg Ticket", "SUM([Revenue]) / COUNT([Order ID])", "real", "measure", "quantitative", 'c"$"#,##0.00;-"$"#,##0.00'),
 "appshare": ("App % of Revenue", 'SUM(IIF([Is App Order] = "True", [Revenue], 0)) / SUM([Revenue])', "real", "measure", "quantitative", "p0.0%"),
 "sat":      ("Avg Satisfaction", "AVG([Satisfaction Score])", "real", "measure", "quantitative", "n#,##0.00;-#,##0.00"),
 "agemix":   ("Share of Age Group", "COUNT([Order ID]) / MIN({EXCLUDE [Order Channel] : COUNT([Order ID])})", "real", "measure", "quantitative", "p0%"),
 "sat300":   ("Avg Satisfaction (300+ orders)", "IF COUNT([Order ID]) >= 300 THEN AVG([Satisfaction Score]) END", "real", "measure", "quantitative", "n#,##0.00;-#,##0.00"),
 "items":    ("Items per Order", "SUM([Items]) / COUNT([Order ID])", "real", "measure", "quantitative", "n#,##0.00;-#,##0.00"),
 "food":     ("Food Attach Rate", 'SUM(IIF([Has Food Item] = "True", 1, 0)) / COUNT([Order ID])', "real", "measure", "quantitative", "p0%"),
 "rewards":  ("Rewards Status", 'IIF([Is Rewards Member] = "True", "Rewards member", "Non-member")', "string", "dimension", "nominal", None),
 "wday":     ("Weekday Label", 'STR([Weekday Number]) + " " + [Weekday]', "string", "dimension", "nominal", None),
}
CALC_ID = {k: f"Calculation_{1000000000000001 + i}" for i, k in enumerate(CALCS)}
CALC_DEPS = {"orders": ["Order ID"], "revenue": ["Revenue"], "ticket": ["Revenue", "Order ID"],
  "appshare": ["Is App Order", "Revenue"], "sat": ["Satisfaction Score"], "agemix": ["Order ID", "Order Channel"],
  "sat300": ["Order ID", "Satisfaction Score"], "items": ["Items", "Order ID"], "food": ["Has Food Item", "Order ID"],
  "rewards": ["Is Rewards Member"], "wday": ["Weekday Number", "Weekday"]}
ORDINAL_DIMS = {"Order Hour", "Weekday Number", "Fulfillment Bucket (min)"}

def base_col(name):
    dt = DTYPE[name]
    if name in ORDINAL_DIMS:
        return f"<column datatype={qa(dt)} name={qa('['+name+']')} role='dimension' type='ordinal' />"
    if dt in ("integer", "real"):
        return f"<column datatype={qa(dt)} name={qa('['+name+']')} role='measure' type='quantitative' />"
    t = "ordinal" if dt in ("date", "datetime") else "nominal"
    return f"<column datatype={qa(dt)} name={qa('['+name+']')} role='dimension' type={qa(t)} />"

def calc_col(k):
    cap, f, dt, role, typ, fmt = CALCS[k]
    fa = f" default-format={qa(fmt)}" if fmt else ""
    return (f"<column caption={qa(cap)} datatype={qa(dt)}{fa} name={qa('['+CALC_ID[k]+']')} role={qa(role)} type={qa(typ)}>"
            f"<calculation class='tableau' formula={qa(f)} /></column>")

# field reference helpers -> (column-instance name, column xml, instance xml)
def dim(name, ordinal=False):
    key = "ok" if ordinal else "nk"; t = "ordinal" if ordinal else "nominal"
    inst = f"[none:{name}:{key}]"
    return inst, [base_col(name)], f"<column-instance column={qa('['+name+']')} derivation='None' name={qa(inst)} pivot='key' type={qa(t)} />"
def cdim(k):
    inst = f"[none:{CALC_ID[k]}:nk]"
    deps = [calc_col(k)] + [base_col(d) for d in CALC_DEPS[k]]
    return inst, deps, f"<column-instance column={qa('['+CALC_ID[k]+']')} derivation='None' name={qa(inst)} pivot='key' type='nominal' />"
def cmeas(k):
    inst = f"[usr:{CALC_ID[k]}:qk]"
    deps = [calc_col(k)] + [base_col(d) for d in CALC_DEPS[k]]
    return inst, deps, f"<column-instance column={qa('['+CALC_ID[k]+']')} derivation='User' name={qa(inst)} pivot='key' type='quantitative' />"

def worksheet(name, mark, rows=None, cols=None, color=None, text=None, tooltips=(), labels=False):
    refs = [r for r in [rows, cols, color, text, *tooltips] if r]
    cols_xml, insts = [], []
    for _, deps, inst in refs:
        for d in deps:
            if d not in cols_xml: cols_xml.append(d)
        if inst not in insts: insts.append(inst)
    enc = []
    if color: enc.append(f"<color column={qa(P+'.'+color[0])} />")
    if text: enc.append(f"<text column={qa(P+'.'+text[0])} />")
    for t in tooltips: enc.append(f"<tooltip column={qa(P+'.'+t[0])} />")
    style = ("<style><style-rule element='mark'><format attr='mark-labels-show' value='true' />"
             "<format attr='mark-labels-cull' value='true' /></style-rule></style>") if labels else ""
    return (f"<worksheet name={qa(name)}><table><view>"
            f"<datasources><datasource caption='orders' name={qa(DS)} /></datasources>"
            f"<datasource-dependencies datasource={qa(DS)}>{''.join(cols_xml)}{''.join(insts)}</datasource-dependencies>"
            f"<aggregation value='true' /></view><style />"
            f"<panes><pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view>"
            f"<mark class={qa(mark)} />" + (f"<encodings>{''.join(enc)}</encodings>" if enc else "") + style +
            f"</pane></panes>"
            f"<rows>{esc(P+'.'+rows[0]) if rows else ''}</rows><cols>{esc(P+'.'+cols[0]) if cols else ''}</cols>"
            f"</table></worksheet>")

ch = dim("Order Channel")
SHEETS = [
  ("Revenue", dict(mark="Text", text=cmeas("revenue"))),
  ("Orders", dict(mark="Text", text=cmeas("orders"))),
  ("Avg Ticket", dict(mark="Text", text=cmeas("ticket"))),
  ("App % of Revenue", dict(mark="Text", text=cmeas("appshare"))),
  ("Avg Satisfaction", dict(mark="Text", text=cmeas("sat"))),
  ("Avg Ticket by Channel", dict(mark="Bar", rows=ch, cols=cmeas("ticket"), color=ch, text=cmeas("ticket"),
                                 tooltips=(cmeas("orders"), cmeas("items"), cmeas("food")), labels=True)),
  ("Channel Mix by Age Group", dict(mark="Bar", rows=dim("Age Group"), cols=cmeas("agemix"), color=ch,
                                    text=cmeas("agemix"), labels=True)),
  ("Rewards vs Non-member Ticket", dict(mark="Circle", rows=ch, cols=cmeas("ticket"), color=cdim("rewards"),
                                        tooltips=(cmeas("orders"),))),
  ("Satisfaction vs Wait Time", dict(mark="Line", cols=dim("Fulfillment Bucket (min)", ordinal=True),
                                     rows=cmeas("sat300"), color=ch, tooltips=(cmeas("orders"),))),
  ("Orders by Weekday and Hour", dict(mark="Square", cols=dim("Order Hour", ordinal=True), rows=cdim("wday"),
                                      color=cmeas("orders"))),
]

# dashboard (1400 x 1100, floating zones in 1/100000 units)
W, H = 1400, 1100
def z(px, total): return str(round(px * 100000 / total))
zones, zid = [], 3
def zone(name, x, y, w, h):
    global zid; zid += 1
    zones.append(f"<zone floating='true' h={qa(z(h,H))} id={qa(str(zid))} name={qa(name)} w={qa(z(w,W))} x={qa(z(x,W))} y={qa(z(y,H))} />")
def text_zone(t, x, y, w, h, size, bold, color):
    global zid; zid += 1
    b = " bold='true'" if bold else ""
    zones.append(f"<zone floating='true' h={qa(z(h,H))} id={qa(str(zid))} type='text' w={qa(z(w,W))} x={qa(z(x,W))} y={qa(z(y,H))}>"
                 f"<formatted-text><run{b} fontcolor={qa(color)} fontsize={qa(str(size))}>{esc(t)}</run></formatted-text></zone>")
text_zone("QSR Revenue Growth Command Center", 20, 10, 1000, 44, 22, True, "#0b0b0b")
text_zone("100,000 orders  |  500 stores  |  Jan 2024 - Dec 2025  |  source: BigQuery qsr_reporting.rpt_orders_tableau, built with dbt",
          20, 54, 1360, 26, 11, False, "#52514e")
for i, k in enumerate(["Revenue", "Orders", "Avg Ticket", "App % of Revenue", "Avg Satisfaction"]):
    zone(k, 20 + i * 275, 88, 259, 100)
zone("Avg Ticket by Channel", 20, 205, 670, 290); zone("Channel Mix by Age Group", 710, 205, 670, 290)
zone("Rewards vs Non-member Ticket", 20, 510, 670, 290); zone("Satisfaction vs Wait Time", 710, 510, 670, 290)
zone("Orders by Weekday and Hour", 20, 815, 1360, 270)
DASH = "QSR Revenue Growth Command Center"
dashboard = (f"<dashboards><dashboard name={qa(DASH)}><style />"
             f"<size maxheight='{H}' maxwidth='{W}' minheight='{H}' minwidth='{W}' />"
             f"<zones><zone h='100000' id='3' type='layout-basic' w='100000' x='0' y='0' />{''.join(zones)}</zones>"
             f"</dashboard></dashboards>")

# channel + rewards colours stored on the data source
def palette(field, mapping):
    maps = "".join(f"<map to={qa(c)}><bucket>{esc(chr(34)+v+chr(34))}</bucket></map>" for v, c in mapping.items())
    return f"<encoding attr='color' field={qa(field)} type='palette'>{maps}</encoding>"
ds_style = ("<style><style-rule element='mark'>"
    + palette("[none:Order Channel:nk]", {"Mobile App": "#2a78d6", "Drive-Thru": "#eb6834", "In-Store Cashier": "#1baf7a", "Kiosk": "#eda100"})
    + palette(f"[none:{CALC_ID['rewards']}:nk]", {"Rewards member": "#2a78d6", "Non-member": "#eb6834"})
    + "</style-rule></style>")


HYPER = OUT.replace(".twbx", ".hyper")
SQLT = {"string": SqlType.text(), "date": SqlType.date(), "datetime": SqlType.timestamp(),
        "integer": SqlType.big_int(), "real": SqlType.double()}
with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
    with Connection(hp.endpoint, HYPER, CreateMode.CREATE_AND_REPLACE) as con:
        con.catalog.create_schema("Extract")
        tdef = TableDefinition(TableName("Extract", "Extract"), [TableDefinition.Column(n, SQLT[dt]) for n, dt in FIELDS])
        con.catalog.create_table(tdef)
        n_rows = con.execute_command(f"COPY {tdef.table_name} FROM {escape_string_literal(CSV)} WITH (format csv, header)")
print("hyper rows", n_rows)
REMOTE = {"string": ("129", "Count"), "date": ("133", "Year"), "datetime": ("135", "Year"),
          "integer": ("20", "Sum"), "real": ("5", "Sum")}
meta = "".join(
    f"<metadata-record class='column'><remote-name>{esc(n)}</remote-name><remote-type>{REMOTE[dt][0]}</remote-type>"
    f"<local-name>{esc('['+n+']')}</local-name><parent-name>[Extract]</parent-name><remote-alias>{esc(n)}</remote-alias>"
    f"<ordinal>{i}</ordinal><local-type>{dt}</local-type><aggregation>{REMOTE[dt][1]}</aggregation>"
    f"<contains-null>true</contains-null></metadata-record>" for i, (n, dt) in enumerate(FIELDS))
now = datetime.datetime.now(datetime.UTC)
extract_xml = (f"<extract count='-1' enabled='true' units='records'>"
    f"<connection access_mode='readonly' authentication='auth-none' author-locale='en_US' class='hyper' "
    f"dbname='Data/Extracts/orders.hyper' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract' "
    f"update-time={qa(now.strftime('%m/%d/%Y %I:%M:%S %p'))} username='tableau_internal_user'>"
    f"<relation name='Extract' table='[Extract].[Extract]' type='table' />"
    f"<refresh increment-key='' incremental-updates='false'><refresh-event add-from-file-path='orders' increment-value='%null%' "
    f"refresh-type='create' rows-inserted={qa(str(n_rows))} timestamp-start={qa(now.strftime('%Y-%m-%d %H:%M:%S.000'))} /></refresh>"
    f"<metadata-records>{meta}</metadata-records></connection></extract>")

csv_cols = "".join(f"<column datatype={qa(dt)} name={qa(n)} ordinal={qa(str(i))} />" for i, (n, dt) in enumerate(FIELDS))
ds_cols = "".join(base_col(n) for n, _ in FIELDS if n in ORDINAL_DIMS) + "".join(calc_col(k) for k in CALCS)
datasource = (f"<datasources><datasource caption='orders' inline='true' name={qa(DS)} version='18.1'>"
  f"<connection class='federated'><named-connections><named-connection caption='orders' name={qa(CONN)}>"
  f"<connection class='textscan' directory='Data/Datasources' filename='orders.csv' password='' server='' />"
  f"</named-connection></named-connections>"
  f"<relation connection={qa(CONN)} name='orders.csv' table='[orders#csv]' type='table'>"
  f"<columns character-set='UTF-8' header='yes' locale='en_US' separator=','>{csv_cols}</columns></relation>"
  f"</connection><aliases enabled='yes' />{ds_cols}{extract_xml}"
  f"<layout dim-ordering='alphabetic' dim-percentage='0.5' measure-ordering='alphabetic' measure-percentage='0.4' show-structure='true' />"
  f"{ds_style}</datasource></datasources>")

cards = ("<cards><edge name='left'><strip size='160'><card type='pages' /><card type='filters' /><card type='marks' /></strip></edge>"
         "<edge name='top'><strip size='2147483647'><card type='columns' /></strip><strip size='2147483647'><card type='rows' /></strip>"
         "<strip size='31'><card type='title' /></strip></edge></cards>")
windows = (f"<windows source-height='30'><window class='dashboard' maximized='true' name={qa(DASH)}><viewpoints>"
           + "".join(f"<viewpoint name={qa(n)} />" for n, _ in SHEETS) + "</viewpoints><active id='-1' /></window>"
           + "".join(f"<window class='worksheet' name={qa(n)}>{cards}</window>" for n, _ in SHEETS) + "</windows>")

twb = ("<?xml version='1.0' encoding='utf-8' ?>\n"
       "<workbook original-version='18.1' source-build='2020.1.0 (20201.20.0220.0213)' source-platform='mac' version='18.1' "
       "xmlns:user='http://www.tableausoftware.com/xml/user'>"
       "<preferences><preference name='ui.encoding.shelf.height' value='24' /><preference name='ui.shelf.height' value='26' /></preferences>"
       + datasource + "<worksheets>" + "".join(worksheet(n, **kw) for n, kw in SHEETS) + "</worksheets>"
       + dashboard + windows + "</workbook>\n")

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("QSR Revenue Growth Command Center.twb", twb)
    zf.write(CSV, "Data/Datasources/orders.csv")
    zf.write(HYPER, "Data/Extracts/orders.hyper")
open(OUT.replace(".twbx", ".twb"), "w").write(twb)
print("ok", OUT)
