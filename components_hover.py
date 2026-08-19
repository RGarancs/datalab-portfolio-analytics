"""components_hover.py -- a real custom Streamlit component.

`split_explorer` renders a Plotly chart (bar or donut) with an attached detail
PANEL that updates on **hover** -- something native Streamlit/Plotly cannot do
(it only surfaces click/select). It also carries an in-chart **"Split by"**
dropdown that changes the chart's x-axis / grouping, and a **Bars / Donut**
toggle -- both handled **entirely client-side** (no rerun) because every
dimension's aggregation is precomputed and shipped in one payload.

Hovering a bar/slice shows: the KPIs you picked (⚙ Tooltip KPIs, chosen in
Streamlit) and a "Top 10" list (projects / investors / whatever the caller
supplies) for that category.
"""
from __future__ import annotations

import json

import streamlit.components.v1 as components

from theme import PALETTES, _mix

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


def split_explorer(dims_payload: dict, theme: str, default_dim: str | None = None,
                   chart_type: str = "Bars", height: int = 460, panel_title: str = "Detail",
                   key: str = "split_explorer") -> None:
    """
    dims_payload: {dim_label: {"cats":[...], "values":[...], "labels":[...],
                                "detail": {cat: {"kpis":[[l,v],...],
                                                 "toplists": {list_name: [[name,val],...]}}}}}
    """
    if not dims_payload:
        return
    default_dim = default_dim if default_dim in dims_payload else next(iter(dims_payload))
    p = PALETTES[theme]
    panelbg = _mix(p["card"], "#ffffff", 0.09) if theme == "dark" else _mix(p["card"], "#000000", 0.03)
    colorway = [p["voice"], p["gold"], p["deep"], p["neg"], p["pos"], p["soft"], "#9B8CFF", "#4AB8A6"]
    payload = json.dumps({
        "dims": dims_payload, "default": default_dim, "chartType": chart_type,
        "colorway": colorway, "ink": p["ink"], "soft": p["soft"], "card": p["card"],
        "line": p["line2"], "grid": p["line"], "gold": p["gold"], "neg": p["neg"], "voice": p["voice"],
    })
    dim_options = "".join(f'<option value="{d}">{d}</option>' for d in dims_payload)
    uid = f"nk_{key}"
    html = f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=DM+Serif+Display&display=swap" rel="stylesheet">
<script src="{PLOTLY_CDN}"></script>
<style>
  :root{{--ink:{p['ink']};--soft:{p['soft']};--card:{p['card']};--panelbg:{panelbg};--line:{p['line2']};--voice:{p['voice']};--gold:{p['gold']}}}
  html,body{{margin:0;background:transparent;font-family:'Manrope',sans-serif;color:var(--ink)}}
  #toolbar{{display:flex;gap:10px;align-items:center;margin-bottom:8px;flex-wrap:wrap}}
  #toolbar label{{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--soft);font-weight:700;margin-right:2px}}
  select, .seg-btn{{font-family:'Manrope',sans-serif;font-size:12.5px;font-weight:700;border-radius:9px;border:1px solid var(--line);
      background:color-mix(in srgb, var(--ink) 5%, transparent);color:var(--ink);padding:6px 12px;cursor:pointer}}
  .segwrap{{display:inline-flex;background:color-mix(in srgb, var(--ink) 6%, transparent);border-radius:11px;padding:3px;gap:2px}}
  .seg-btn{{border:0;background:transparent;padding:5px 13px}}
  .seg-btn.active{{background:var(--voice);color:#fff}}
  #wrap{{display:flex;gap:14px;align-items:flex-start}}
  #left{{flex:1 1 72%;min-width:0}}
  #chart{{width:100%;height:{height-64}px}}
  #panel{{flex:0 0 27%;max-height:{height}px;background:var(--panelbg);border:1px solid var(--line);border-radius:16px;padding:12px 14px;overflow:auto;
      box-shadow:inset 0 1px 0 rgba(255,255,255,.05)}}
  #panel .cat{{font-family:'DM Serif Display',serif;font-size:20px;line-height:1.1;margin:0 0 9px;color:var(--voice);word-break:break-word}}
  .kpis{{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:11px}}
  .kpi{{border:1px solid var(--line);border-radius:11px;padding:7px 10px}}
  .kpi .l{{font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--soft);font-weight:700}}
  .kpi .v{{font-family:'DM Serif Display',serif;font-size:18px}}
  .tlsel{{display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap}}
  .tlbtn{{font-size:10.5px;font-weight:700;border:1px solid var(--line);border-radius:8px;padding:4px 9px;background:transparent;color:var(--soft);cursor:pointer}}
  .tlbtn.active{{background:var(--voice);color:#fff;border-color:var(--voice)}}
  .row{{display:flex;align-items:center;gap:8px;padding:5.5px 0;border-top:1px solid var(--line);font-size:12px}}
  .row:first-child{{border-top:none}}
  .row .rk{{flex:0 0 15px;color:var(--soft);font-weight:800;font-size:10.5px;text-align:right;font-variant-numeric:tabular-nums}}
  .row .n{{flex:1 1 auto;color:var(--ink);font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .row .x{{flex:0 0 auto;color:var(--soft);white-space:nowrap;font-variant-numeric:tabular-nums}}
  .hint{{font-size:11px;color:var(--soft);margin-top:10px}}
</style></head>
<body>
<div id="wrap">
<div id="left">
<div id="toolbar">
  <label>Split by</label>
  <select id="dimsel">{dim_options}</select>
  <div class="segwrap">
    <button class="seg-btn" id="btn-bars">Bars</button>
    <button class="seg-btn" id="btn-donut">Donut</button>
  </div>
</div>
<div id="chart"></div>
</div>
<div id="panel"><div class="cat" id="p-cat">—</div>
<div class="kpis" id="p-kpis"></div><div class="tlsel" id="p-tlsel"></div><div id="p-top"></div>
<div class="hint">Hover a {'"segment"' if chart_type=='Donut' else '"bar"'} to drill in.</div></div></div>
<script>
const D = {payload};
let curDim = D.default, curType = D.chartType, curTop = null;
const gd = document.getElementById('chart');

function dimData(){{ return D.dims[curDim]; }}

function draw(){{
  const dd = dimData();
  const trace = curType === 'Donut'
    ? {{type:'pie', labels:dd.cats, values:dd.values, hole:0.62, sort:false,
        marker:{{colors:D.colorway}}, textinfo:'label+percent', textfont:{{size:12}}}}
    : {{type:'bar', x:dd.cats, y:dd.values,
        text:(dd.cats.length>18 ? dd.cats.map(function(){{return '';}}) : dd.labels),
        textposition:'outside', cliponaxis:false, marker:{{color:D.voice, cornerradius:8}}, hoverinfo:'x+y'}};
  const layout = {{
    height:{height}-64, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    font:{{family:'Manrope', color:D.ink, size:12}}, margin:{{l:8,r:12,t:10,b:34}}, bargap:0.34,
    showlegend:false,
    xaxis: curType==='Donut' ? {{visible:false}} : {{type:'category', tickangle:-28, gridcolor:D.grid,
        tickfont:{{color:D.soft, size:10.5}}, automargin:true, tickmode:'array', tickvals:dd.cats,
        ticktext: dd.cats.map(function(c){{ return (c && c.length>18) ? c.slice(0,17)+'\u2026' : c; }})}},
    yaxis: curType==='Donut' ? {{visible:false}} : {{visible:false, gridcolor:D.grid}}
  }};
  Plotly.react(gd, [trace], layout, {{displayModeBar:false, responsive:true}});
}}

function panel(cat){{
  const dd = dimData();
  const d = (dd.detail && dd.detail[cat]) || {{kpis:[], toplists:{{}}}};
  document.getElementById('p-cat').textContent = cat;
  document.getElementById('p-kpis').innerHTML = (d.kpis||[]).map(k =>
    `<div class="kpi"><div class="l">${{k[0]}}</div><div class="v">${{k[1]}}</div></div>`).join('');
  const names = Object.keys(d.toplists || {{}});
  if (!curTop || !names.includes(curTop)) curTop = names[0];
  document.getElementById('p-tlsel').innerHTML = names.map(n =>
    `<button class="tlbtn ${{n===curTop?'active':''}}" data-n="${{n}}">${{n}}</button>`).join('');
  const list = (d.toplists && d.toplists[curTop]) || [];
  document.getElementById('p-top').innerHTML = list.map((t,i) =>
    `<div class="row"><span class="rk">${{i+1}}</span><span class="n">${{t[0]}}</span><span class="x">${{t[1]}}</span></div>`).join('');
  document.querySelectorAll('.tlbtn').forEach(b => b.onclick = () => {{ curTop = b.dataset.n; panel(cat); }});
}}

function firstCat(){{ const dd = dimData(); return (curType==='Donut' ? dd.cats[0] : dd.cats[0]); }}

document.getElementById('dimsel').value = curDim;
document.getElementById('dimsel').onchange = e => {{ curDim = e.target.value; curTop = null; draw(); panel(firstCat()); }};
document.getElementById('btn-bars').onclick = () => {{ curType='Bars'; syncSeg(); draw(); }};
document.getElementById('btn-donut').onclick = () => {{ curType='Donut'; syncSeg(); draw(); }};
function syncSeg(){{
  document.getElementById('btn-bars').classList.toggle('active', curType==='Bars');
  document.getElementById('btn-donut').classList.toggle('active', curType==='Donut');
}}
syncSeg(); draw(); panel(firstCat());
gd.on('plotly_hover', e => {{
  const pt = e.points[0];
  panel(curType==='Donut' ? pt.label : pt.x);
}});
</script></body></html>
"""
    components.html(html, height=height + 60, scrolling=False)
