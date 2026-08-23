"""theme.py -- Data Lab design system for Streamlit + Plotly.

Two themes, switchable at runtime (dark default + white/grey light).
Tokens lifted from the live Data Lab CSS (OKLCH -> hex):
  page #0A0A0A · card #262626 · text #FBFBFB / muted #A4A4A4 · accent #5C5CFC
  (light: #5226E5) · tangerine #E8944A · late #FF5251 · surface-teal #002121.
Typography: Manrope (UI/body) + DM Serif Display (big stat numbers).
"""
from __future__ import annotations

import streamlit as st
from urllib.parse import quote

PALETTES: dict[str, dict[str, str]] = {
    "dark": dict(
        smoke="#062325", panel="#083034", card="#0F3D42", plot="rgba(255,255,255,0.03)",
        ink="#F4F1E8", soft="#A9BDB9", faint="#6F8B88",
        voice="#C9A24E", deep="#E3C98A", gold="#5FB7AE", teal="#0B4046",
        line="rgba(255,255,255,.09)", line2="rgba(255,255,255,.16)",
        pos="#5CC8A0", neg="#E0645A", default="#4F6B69", shadow="rgba(0,0,0,.55)",
    ),
}

FONT_DISPLAY = "'Playfair Display', Georgia, serif"
FONT_BODY = "'Manrope', -apple-system, Helvetica, Arial, sans-serif"
FONT_LABEL = "'Manrope', Arial, sans-serif"


# ---- unified monoline SVG icon set (no emoji/unicode icons anywhere) ----
_SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">'
TAB_ICONS: dict[str, str] = {
    "overview": _SVG_HEAD + '<rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/>'
                            '<rect x="3" y="13" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/></svg>',
    "outstanding": _SVG_HEAD + '<path d="M3 21h18"/><path d="M4 21V10"/><path d="M20 21V10"/><path d="M8 21V10"/>'
                               '<path d="M16 21V10"/><path d="M2 10l10-6 10 6"/></svg>',
    "cumulative": _SVG_HEAD + '<polyline points="3,17 9,11 13,15 21,6"/><polyline points="15,6 21,6 21,12"/></svg>',
    "activity": _SVG_HEAD + '<polyline points="2,12 7,12 9,18 15,6 17,12 22,12"/></svg>',
    "funds": _SVG_HEAD + '<path d="M12 2s7 8.5 7 13a7 7 0 0 1-14 0c0-4.5 7-13 7-13z"/></svg>',
    "projects": _SVG_HEAD + '<rect x="4" y="3" width="10" height="18" rx="1"/><rect x="15" y="9" width="6" height="12" rx="1"/>'
                            '<line x1="7" y1="7" x2="7" y2="7.01"/><line x1="11" y1="7" x2="11" y2="7.01"/>'
                            '<line x1="7" y1="11" x2="7" y2="11.01"/><line x1="11" y1="11" x2="11" y2="11.01"/>'
                            '<line x1="7" y1="15" x2="7" y2="15.01"/><line x1="11" y1="15" x2="11" y2="15.01"/></svg>',
    "portfolio": _SVG_HEAD + '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 5-6 8-6s6.5 2 8 6"/></svg>',
    "risk": _SVG_HEAD + '<path d="M12 3.5 2.5 20h19L12 3.5z"/><path d="M12 10v4"/>'
                        '<circle cx="12" cy="17" r="0.5" fill="black" stroke="none"/></svg>',
    "split": _SVG_HEAD + '<path d="M4 6h16"/><path d="M4 12h10"/><path d="M4 18h6"/></svg>',
    "hover": _SVG_HEAD + '<circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><circle cx="12" cy="16" r="0.6" fill="black" stroke="none"/></svg>',
}

# tab order after Risk & Recovery moved into the Overview "More views" list
TAB_ICON_ORDER = ["overview", "outstanding", "cumulative", "risk"]


def _icon_uri(name: str) -> str:
    return "data:image/svg+xml," + quote(TAB_ICONS[name])



def atelier_colorway(theme: str) -> list[str]:
    p = PALETTES[theme]
    return [p["voice"], p["gold"], p["deep"], p["neg"], p["pos"], p["soft"]]


def status_colorway(theme: str) -> dict[str, str]:
    p = PALETTES[theme]
    return {
        "Repaid": p["voice"], "Active": p["gold"], "Recovery": p["deep"],
        "Available": p["faint"], "Restructured": "#E8944A", "In Recovery": p["neg"],
        "Defaulted": p["default"],
    }


def plotly_layout(theme: str, height: int = 340, title: str | None = None, showlegend: bool = True) -> dict:
    p = PALETTES[theme]
    axis = dict(gridcolor=p["line"], zerolinecolor=p["line2"], linecolor=p["line2"],
                automargin=True, tickfont=dict(family=FONT_BODY, color=p["soft"], size=12))
    layout = dict(
        height=height, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=p["plot"],
        font=dict(family=FONT_BODY, color=p["ink"], size=13),
        margin=dict(l=22, r=44, t=(48 if title else 40), b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(family=FONT_BODY, size=11.5, color=p["soft"])),
        showlegend=showlegend, colorway=atelier_colorway(theme),
        xaxis=dict(**axis), yaxis=dict(**axis), bargap=0.34,
        uniformtext=dict(mode="hide", minsize=9),
        hoverlabel=dict(font=dict(family=FONT_BODY, size=12), bgcolor=p["card"], bordercolor=p["line2"]),
        hovermode="x unified",
    )
    if title:
        layout["title"] = dict(text=title, font=dict(family=FONT_BODY, color=p["ink"], size=16), x=0, xanchor="left")
    return layout


def round_bars(fig, radius: int = 8):
    fig.update_traces(selector=dict(type="bar"), marker_cornerradius=radius)
    return fig



# ---- colour helpers (for gradient bars) ----
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def _mix(hex_a, hex_b, t):
    a, b = _hex_to_rgb(hex_a), _hex_to_rgb(hex_b)
    return _rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


def _sparkline_svg(values, w: int = 96, h: int = 26, pad: float = 2.5) -> str:
    """Tiny inline sparkline (uses currentColor so it inherits the accent)."""
    vs = [float(v) for v in values if v is not None]
    if len(vs) < 2:
        return ""
    lo, hi = min(vs), max(vs)
    rng = (hi - lo) or 1.0
    n = len(vs)
    step = (w - 2 * pad) / (n - 1)
    pts = [(pad + i * step, (h - pad) - (v - lo) / rng * (h - 2 * pad)) for i, v in enumerate(vs)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pad:.1f},{h - pad:.1f} " + line + f" {w - pad:.1f},{h - pad:.1f}"
    lx, ly = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<polyline points="{area}" fill="currentColor" fill-opacity="0.13" stroke="none"/>'
            f'<polyline points="{line}" fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="1.9" fill="currentColor"/></svg>')


# ---- card badge icons (blue-tinted square badge, thin monoline, currentColor) ----
def _badge(paths: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="19" height="19">'
            + paths + "</svg>")


BADGE_SVGS = {
    "euro": _badge('<path d="M18 7.5A6 6 0 1 0 18 16.5"/><path d="M4 10.5h9"/><path d="M4 13.5h9"/>'),
    "percent": _badge('<line x1="19" y1="5" x2="5" y2="19"/><circle cx="7" cy="7" r="2.3"/><circle cx="17" cy="17" r="2.3"/>'),
    "users": _badge('<circle cx="9" cy="8" r="3.1"/><path d="M3.5 20c.7-3.3 3-5 5.5-5s4.8 1.7 5.5 5"/>'
                    '<path d="M16 6.4a3 3 0 0 1 0 5.9"/><path d="M20.5 20c-.4-1.8-1.3-3.1-2.6-3.9"/>'),
    "building": _badge('<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M8 7h.01"/><path d="M12 7h.01"/>'
                       '<path d="M8 11h.01"/><path d="M12 11h.01"/><path d="M8 15h.01"/><path d="M12 15h.01"/>'),
    "check": _badge('<circle cx="12" cy="12" r="9"/><path d="M8.3 12.4l2.6 2.6 4.8-5.2"/>'),
    "clock": _badge('<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5l3.2 2"/>'),
    "coins": _badge('<ellipse cx="9" cy="7" rx="5" ry="2.6"/><path d="M4 7v5c0 1.4 2.2 2.6 5 2.6s5-1.2 5-2.6"/>'
                    '<path d="M10 15.6c.3 1.3 2.4 2.3 5 2.3s5-1.2 5-2.6v-5"/><ellipse cx="15" cy="10.3" rx="5" ry="2.6"/>'),
    "wallet": _badge('<rect x="3" y="6" width="18" height="13" rx="2.5"/><path d="M3 10.5h18"/><circle cx="17" cy="14.5" r="1.1"/>'),
    "hash": _badge('<line x1="9.5" y1="4" x2="7.5" y2="20"/><line x1="16.5" y1="4" x2="14.5" y2="20"/>'
                   '<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/>'),
    "layers": _badge('<path d="M12 3 3 8l9 5 9-5-9-5z"/><path d="M3 13l9 5 9-5"/>'),
    "trend": _badge('<polyline points="4,16 9,11 13,14 20,6"/><polyline points="15,6 20,6 20,11"/>'),
    "award": _badge('<circle cx="12" cy="9" r="5"/><path d="M9 13.5 7.5 21 12 18.5 16.5 21 15 13.5"/>'),
    "tag": _badge('<path d="M4 4h7l9 9-7 7-9-9V4z"/><circle cx="8" cy="8" r="1.2"/>'),
    "alert": _badge('<path d="M12 3 2.5 20h19L12 3z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>'),
    "userplus": _badge('<circle cx="9" cy="8" r="3.1"/><path d="M3.5 20c.7-3.3 3-5 5.5-5s4.8 1.7 5.5 5"/><path d="M18 8v6"/><path d="M15 11h6"/>'),
    "ticket": _badge('<path d="M4 7h16v3a2 2 0 0 0 0 4v3H4v-3a2 2 0 0 0 0-4V7z"/><path d="M14 7v10"/>'),
    "download": _badge('<path d="M12 4v10"/><path d="M8 11l4 4 4-4"/><path d="M5 19h14"/>'),
    "shield": _badge('<path d="M12 3l7 3v5c0 4.3-3 7.3-7 8.5-4-1.2-7-4.2-7-8.5V6l7-3z"/><path d="M9 11.5l2 2 4-4.2"/>'),
    "pulse": _badge('<path d="M3 12h4l2 6 4-14 2 8h6"/>'),
    "pause": _badge('<circle cx="12" cy="12" r="9"/><line x1="10" y1="9" x2="10" y2="15"/><line x1="14" y1="9" x2="14" y2="15"/>'),
    "idcard": _badge('<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="11" r="2.2"/><path d="M5.5 16c.4-1.6 1.6-2.4 3-2.4s2.6.8 3 2.4"/><path d="M14 10h4"/><path d="M14 13h4"/>'),
    "hourglass": _badge('<path d="M7 4h10"/><path d="M7 20h10"/><path d="M7 4c0 4 5 4 5 8s-5 4-5 8"/><path d="M17 4c0 4-5 4-5 8s5 4 5 8"/>'),
}

# unique icon per KPI catalog key (so no two cards share the euro sign)
KPI_ICON = {
    "outstanding": "wallet", "total_funded": "layers", "funded_period": "trend",
    "avg_return": "percent", "aroi_net": "award", "interest_paid": "coins",
    "platform_fees": "tag", "default_rate_12m": "alert", "n_investors": "users",
    "new_investors": "userplus", "avg_investment": "ticket", "deposits_period": "download",
    "net_deposits_period": "wallet", "avg_ltv": "shield", "n_projects": "building",
    "avg_loan_term": "hourglass",
}


def _infer_badge(label: str, value: str) -> str:
    l, v = str(label).lower(), str(value)
    pairs = [
        ("passive", "pause"), ("identified", "idcard"), ("registered", "users"),
        ("active", "pulse"), ("new investor", "userplus"), ("investors", "users"), ("investor", "users"),
        ("avg. investment", "ticket"), ("avg investment", "ticket"), ("est. annual", "coins"),
        ("project size", "building"), ("projects", "building"), ("project", "building"),
        ("open loans", "building"), ("outstanding", "wallet"), ("pipeline", "download"),
        ("repaid", "check"), ("returned", "check"), ("loans fully", "check"),
        ("loan term", "hourglass"), ("loan duration", "hourglass"),
        ("duration", "clock"), ("life", "clock"), ("last login", "clock"), ("recovery", "clock"),
        ("net deposit", "wallet"), ("available", "wallet"), ("wallet", "wallet"),
        ("deposit", "download"), ("collecting", "download"),
        ("interest", "coins"), ("fee", "tag"), ("aroi", "award"),
        ("default", "alert"), ("late", "alert"), ("sell-through", "trend"),
        ("ltc", "shield"), ("completion", "percent"), ("rate", "percent"), ("return", "percent"),
        ("funded", "layers"), ("total", "layers"), ("volume", "trend"), ("growth", "trend"),
    ]
    for k, ic in pairs:
        if k in l:
            return ic
    if v.strip().endswith("%"):
        return "percent"
    if "€" in v:
        return "euro"
    return "hash"


def _gradient_bars_impl(fig, steps: int = 10, region: float = 0.33, light: float = 0.24, radius: int = 9):
    """Give a single-series vertical bar a *subtle* vertical gradient confined to
    the bottom third of the bar: `steps` fine colour bands fade from ~76% colour
    at the very bottom up to the solid bar colour at `region` height; the top
    ~67% stays solid, with a rounded top that carries the data label.

    Kept deliberately minute (small colour delta, few bands) so it reads as a soft
    sheen rather than a banded gradient -- and so the extra stacked traces stay
    cheap to render. Multi-series / horizontal bars fall back to plain rounded bars."""
    import plotly.graph_objects as go
    bar_idx = [i for i, t in enumerate(fig.data) if t.type == "bar"]
    if len(bar_idx) != 1:
        fig.update_traces(selector=dict(type="bar"), marker_cornerradius=radius)
        return fig
    t = fig.data[bar_idx[0]]
    color = t.marker.color
    if not (isinstance(color, str) and color.startswith("#")) or getattr(t, "orientation", "v") == "h":
        fig.update_traces(selector=dict(type="bar"), marker_cornerradius=radius)
        return fig
    x = list(t.x)
    y = [float(v) if v is not None else 0.0 for v in t.y]
    text, name = t.text, t.name
    top = color
    fig.data = tuple(d for j, d in enumerate(fig.data) if j != bar_idx[0])

    m = max(int(steps), 3)
    seg_h = region / m                   # each band = (bottom third) / steps
    for k in range(m):                   # bottom-up: k=0 lightest -> near-solid at region top
        frac_light = light * (1 - k / m)  # 0.24 at the very bottom, ~0 near region top
        fig.add_trace(go.Bar(
            x=x, y=[v * seg_h for v in y], marker=dict(color=_mix(top, "#ffffff", frac_light), line=dict(width=0)),
            hoverinfo="skip", showlegend=False, cliponaxis=False, name=name,
        ))
    # top ~two-thirds: one solid segment, rounded top, carries the data label
    fig.add_trace(go.Bar(
        x=x, y=[v * (1 - region) for v in y], marker=dict(color=top, cornerradius=radius, line=dict(width=0)),
        hoverinfo="skip", showlegend=False, cliponaxis=False, name=name,
        text=text, textposition="outside", textfont=dict(size=12),
    ))
    fig.update_layout(barmode="stack", bargap=0.34)
    return fig


def gradient_bars(fig, radius: int = 9):
    """Gradient temporarily DISABLED for performance (the stacked colour bands
    added many traces and slowed reruns). Now just applies rounded bar corners.
    The detailed bottom-third gradient lives in `_gradient_bars_impl` -- call it
    again here to restore the effect."""
    fig.update_traces(selector=dict(type="bar"), marker_cornerradius=radius)
    return fig


def fit_pies(fig):
    """Let pie/donut outside labels auto-expand so they are not cropped by the card."""
    fig.update_traces(selector=dict(type="pie"), automargin=True)
    return fig


def section_header(label: str, sub: str | None = None) -> None:
    """A 'Deep dive' style subsection divider: pill tag + hairline rule.
    Turns teal when the sidebar 'teal deep-dive' toggle is on."""
    teal = " teal" if st.session_state.get("_deep_teal", False) else ""
    sub_html = f'<span class="nk-deepdive-sub">{sub}</span>' if sub else ""
    st.markdown(
        f'<div class="nk-deepdive{teal}"><span class="nk-deepdive-tag">{label}</span>'
        f'<span class="nk-deepdive-rule"></span>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def render_kpi_row(items, columns: int = 4) -> None:
    if not items:
        return
    cards = []
    for it in items:
        if isinstance(it, (tuple, list)):
            it = {"label": it[0], "value": it[1], "delta": None, "dir": "none"}
        delta_html = ""
        if it.get("delta"):
            d = it.get("dir", "none")
            arrow = {"good": "▲", "bad": "▼", "flat": "▬", "none": ""}.get(d, "")
            delta_html = f'<div class="k-delta dir-{d}">{arrow} {it["delta"]}</div>'
        tip = f' title="{it["help"]}"' if it.get("help") else ""
        badge_name = it.get("icon") or KPI_ICON.get(it.get("key")) or _infer_badge(it["label"], it["value"])
        badge_svg = BADGE_SVGS.get(badge_name, BADGE_SVGS["hash"])
        spark_html = f'<div class="k-spark">{_sparkline_svg(it["spark"])}</div>' if it.get("spark") else ""
        cards.append(
            f'<div class="nk-card"{tip}><div class="k-main">'
            f'<div class="k-label">{it["label"]}</div>'
            f'<div class="k-value">{it["value"]}</div>{spark_html}{delta_html}</div>'
            f'<div class="k-badge">{badge_svg}</div></div>'
        )
    st.markdown(f'<div class="nk-row" style="--kpi-cols:{max(columns,1)}">{"".join(cards)}</div>',
                unsafe_allow_html=True)


def render_chips(chips: list[tuple[str, str]]) -> None:
    html = "".join(f'<span class="nk-chip"><i>{lbl}</i>&nbsp;{val}</span>' for lbl, val in chips)
    st.markdown(f'<div class="nk-chip-row">{html}</div>', unsafe_allow_html=True)


def render_masthead(title_html: str, subtitle: str | None = None) -> None:
    sub = f'<p class="nk-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<span class="nk-eyebrow">Data Lab · Portfolio analytics</span>'
        f'<h1 class="nk-h1">{title_html}</h1>{sub}',
        unsafe_allow_html=True,
    )


def section_title(text_html: str) -> None:
    st.markdown(f'<div class="nk-section">{text_html}</div>', unsafe_allow_html=True)


def inject_css(theme: str, tab_order=None) -> None:
    p = PALETTES[theme]
    order = tab_order or TAB_ICON_ORDER
    tab_icon_css = "\n".join(
        f'[data-testid="stTab"]:nth-of-type({i+1})::before {{ '
        f'-webkit-mask-image:url("{_icon_uri(name)}"); mask-image:url("{_icon_uri(name)}"); }}'
        for i, name in enumerate(order)
    )
    card_shadow = ("0 0 0 1px rgba(255,255,255,.05), 0 16px 44px -20px rgba(96,104,150,.18), 0 4px 14px -6px rgba(0,0,0,.7)"
                   if theme == "dark"
                   else "0 12px 32px -16px rgba(24,24,40,.18), 0 2px 6px -2px rgba(24,24,40,.10)")
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&family=Playfair+Display:ital,wght@0,400;0,500;1,400&display=swap');

        :root {{
            --smoke:{p['smoke']}; --panel:{p['panel']}; --card:{p['card']}; --ink:{p['ink']};
            --soft:{p['soft']}; --faint:{p['faint']}; --voice:{p['voice']}; --deep:{p['deep']};
            --gold:{p['gold']}; --teal:{p['teal']}; --line:{p['line']}; --line2:{p['line2']};
            --pos:{p['pos']}; --neg:{p['neg']}; --default:{p['default']}; --shadow:{p['shadow']};
            --card-shadow:{card_shadow};
            --tab-active:{p['voice']};
            --seg-idle:{(p['soft'] if theme=='dark' else p['ink'])};
            --seg-track:{('rgba(255,255,255,0.05)' if theme=='dark' else '#ECECF1')};
            --seg-active:{('rgba(255,255,255,0.10)' if theme=='dark' else '#ffffff')};
            --seg-active-text:{p['voice']};
            --seg-active-border:rgba(201,162,78,0.55);
        }}

        html, body, [class*="css"] {{ font-family:{FONT_BODY}; }}
        .nk-glass, [data-testid="stExpander"] details, .nk-chip, .nk-panel, .stPlotlyChart, [data-testid="stDataFrame"] {{
            background:rgba(255,255,255,.045) !important; backdrop-filter:blur(16px) saturate(1.1); -webkit-backdrop-filter:blur(16px) saturate(1.1);
            border:1px solid rgba(255,255,255,.11) !important; border-radius:16px; }}
        .stPlotlyChart {{ padding:8px 6px 2px; }}
        .stApp {{ background: var(--smoke); color: var(--ink); font-family:{FONT_BODY}; font-weight:400; }}
        .stApp::before {{ content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
            background:
              radial-gradient(900px 600px at 12% 8%, rgba(201,162,78,.16), transparent 62%),
              radial-gradient(1100px 700px at 88% 22%, rgba(95,183,174,.16), transparent 60%),
              radial-gradient(800px 600px at 50% 100%, rgba(227,201,138,.10), transparent 60%); }}
        /* public preview: no sidebar, no chrome */
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapseButton"], [data-testid="stMainMenu"], [data-testid="stToolbar"] {{ display:none !important; }}
        [data-testid="stHeader"] {{ height:0 !important; }}
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background: transparent; }}
        .block-container {{ position:relative; z-index:1; padding-top:1.4rem; max-width:1340px; }}

        h1,h2,h3,h4 {{ font-family:{FONT_BODY} !important; color:var(--ink) !important; font-weight:700 !important; letter-spacing:-0.01em; }}
        .nk-h1 {{ font-family:{FONT_DISPLAY} !important; font-weight:400 !important; font-size:clamp(34px,4.4vw,54px); margin:2px 0 8px; letter-spacing:-.01em;
            background:linear-gradient(96deg,#F7F2E4 0%,#E8D8A8 48%,#C9A24E 100%); -webkit-background-clip:text; background-clip:text; color:transparent !important; }}
        .nk-h1 em {{ font-style:italic; font-weight:400; background:linear-gradient(92deg,#E3C98A 0%,#C9A24E 45%,#5FB7AE 100%);
            -webkit-background-clip:text; background-clip:text; color:transparent; }}
        .nk-sub {{ color:var(--soft); font-weight:400; max-width:680px; margin:0 0 4px; }}
        .nk-section {{ font-family:{FONT_BODY}; font-weight:700; font-size:18px; color:var(--ink); margin:10px 0 6px; }}
        p, li, span, label, .stMarkdown {{ color: var(--ink); }}
        [data-testid="stCaptionContainer"], .stCaption, small {{ color: var(--soft) !important; }}

        .nk-eyebrow {{ display:inline-block; font-family:{FONT_LABEL}; font-weight:700; font-size:11px;
            letter-spacing:.22em; text-transform:uppercase; color:var(--soft);
            border:1px solid var(--line2); border-radius:999px; padding:5px 13px; margin-bottom:10px; }}

        /* sidebar */
        [data-testid="stSidebar"] {{ background: var(--panel); border-right:1px solid var(--line2); width:320px; }}
        [data-testid="stSidebar"] * {{ color: var(--ink); }}
        .nk-kicker {{ font-family:{FONT_LABEL}; font-weight:700; font-size:11px; letter-spacing:.2em;
            text-transform:uppercase; color:var(--soft); margin:2px 0 8px; display:block; }}
        .nk-kicker i {{ font-style:normal; color:var(--voice); }}
        .nk-hr {{ border:none; border-top:1px solid var(--line2); margin:14px 0; }}

        /* KPI stat cards */
        .nk-row {{ display:grid; grid-template-columns:repeat(var(--kpi-cols,4),1fr); gap:14px; margin:6px 0 16px; }}
        .nk-card {{ background:rgba(255,255,255,.055); backdrop-filter:blur(18px) saturate(1.15); -webkit-backdrop-filter:blur(18px) saturate(1.15); border:1px solid rgba(255,255,255,.13); border-radius:18px; padding:18px 20px 16px;
            box-shadow:var(--card-shadow); transition:transform .2s ease, box-shadow .2s ease;
            display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }}
        .nk-card:hover {{ transform:translateY(-2px); box-shadow:var(--card-shadow), 0 24px 50px -22px var(--shadow); }}
        .nk-card .k-main {{ flex:1 1 auto; min-width:0; }}
        .nk-card .k-badge {{ flex:0 0 auto; width:38px; height:38px; border-radius:11px; display:grid; place-items:center;
            background:color-mix(in srgb, var(--voice) 14%, transparent); color:var(--voice); }}
        .nk-card .k-badge svg {{ display:block; }}
        .nk-card .k-label {{ font-family:{FONT_LABEL}; font-weight:700; font-size:10.5px; letter-spacing:.14em;
            text-transform:uppercase; color:var(--soft); margin-bottom:10px; }}
        .nk-card .k-value {{ font-family:{FONT_DISPLAY}; font-weight:400; font-size:30px; color:var(--ink); background:linear-gradient(95deg,#F7F2E4 0%,#E3C98A 100%); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
            line-height:1; letter-spacing:-.01em; font-variant-numeric:tabular-nums; }}
        .nk-card .k-delta {{ font-family:{FONT_BODY}; font-size:12px; font-weight:600; margin-top:9px; }}
        .k-delta.dir-good {{ color:var(--pos); }} .k-delta.dir-bad {{ color:var(--neg); }} .k-delta.dir-flat {{ color:var(--faint); }}
        @media (max-width:900px) {{ .nk-row {{ grid-template-columns:repeat(2,1fr) !important; }} }}

        /* deep-dive subsection header */
        .nk-deepdive {{ display:flex; align-items:center; gap:14px; margin:22px 0 8px; }}
        .nk-deepdive-tag {{ font-family:{FONT_LABEL}; font-weight:700; font-size:12px; letter-spacing:.22em;
            text-transform:uppercase; color:var(--voice); border:1px solid color-mix(in srgb, var(--voice) 42%, transparent);
            border-radius:999px; padding:6px 15px; background:color-mix(in srgb, var(--voice) 10%, transparent); }}
        .nk-deepdive-rule {{ flex:1; height:1px; background:var(--line2); }}
        .nk-deepdive-sub {{ color:var(--soft); font-size:12.5px; white-space:nowrap; }}

        /* chips (active filter state) */
        .nk-chip-row {{ display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 12px; }}
        .nk-chip {{ font-family:{FONT_BODY}; font-size:12px; font-weight:500; color:var(--ink); background:var(--card);
            border:1px solid var(--line2); border-radius:999px; padding:5px 13px; }}
        .nk-chip i {{ font-style:normal; color:var(--voice); font-family:{FONT_LABEL}; font-weight:700; font-size:10px;
            letter-spacing:.1em; text-transform:uppercase; }}

        /* chart / table cards -- this build has no stable border testid, so we key them */
        [class*="st-key-nkcard"] {{ background:var(--card); border:1px solid var(--line2) !important;
            border-radius:20px; padding:14px 18px 10px; box-shadow:var(--card-shadow); margin-bottom:12px; }}
        [class*="st-key-nkcard_teal"] {{ background:var(--teal) !important;
            border-color:color-mix(in srgb, #5FB7AE 26%, transparent) !important; }}
        /* deep-dive teal header accent */
        .nk-deepdive.teal .nk-deepdive-tag {{ color:#7DE0D6; border-color:color-mix(in srgb, #7DE0D6 45%, transparent);
            background:color-mix(in srgb, #002121 60%, transparent); }}
        .chart-title {{ font-family:{FONT_BODY}; color:var(--ink); font-weight:700; font-size:16px; line-height:1.2; padding:4px 2px 0 2px; }}
        .chart-sub {{ font-family:{FONT_BODY}; color:var(--soft); font-size:12px; padding:0 2px 4px 2px; }}
        [data-testid="stHorizontalBlock"] [data-testid="column"]:has([data-testid="stSegmentedControl"]) {{ align-items:flex-end; }}

        /* legend rows */
        .nk-legend {{ display:flex; align-items:center; gap:10px; padding:9px 2px; border-top:1px solid var(--line); font-size:13.5px; }}
        .nk-legend:first-child {{ border-top:none; }}
        .nk-legend .dot {{ width:11px; height:11px; border-radius:4px; flex:0 0 auto; }}
        .nk-legend .rlabel {{ flex:0 0 130px; color:var(--ink); font-weight:600; }}
        .nk-legend .rval {{ color:var(--soft); font-variant-numeric:tabular-nums; }}

        /* HTML tables with data bars + badges */
        .nk-table-wrap {{ width:100%; overflow-x:auto; border-radius:12px; }}
        .nk-table-wrap.scroll-y {{ overflow-y:auto; }}   /* vertical scroll inside the card, header stays put */
        .nk-table-wrap::-webkit-scrollbar {{ height:9px; width:9px; }}
        .nk-table-wrap::-webkit-scrollbar-thumb {{ background:var(--line2); border-radius:6px; }}
        .nk-table-wrap.scroll-y thead th {{ position:sticky; top:0; z-index:3;
            background:var(--card); box-shadow:0 1px 0 var(--line2); }}
        .nk-table th, .nk-table td {{ white-space:nowrap; }}
        .nk-table {{ width:100%; border-collapse:collapse; font-family:{FONT_BODY}; font-size:13px; margin-top:4px; }}
        .nk-table thead th {{ text-align:left; font-family:{FONT_LABEL}; font-weight:700; font-size:10.5px; letter-spacing:.08em;
            text-transform:uppercase; color:var(--soft); padding:10px 12px; border-bottom:1px solid var(--line2); white-space:nowrap; }}
        .nk-table tbody td {{ padding:9px 12px; border-bottom:1px solid var(--line); color:var(--ink); }}
        .nk-table tbody tr {{ transition:background .15s ease; }}
        .nk-table tbody tr:hover {{ background:color-mix(in srgb, var(--voice) 8%, transparent); }}
        .nk-table td.num, .nk-table th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
        .nk-table tr.total td {{ font-weight:700; border-top:1px solid var(--line2); background:color-mix(in srgb, var(--voice) 6%, transparent); }}
        .nk-badge {{ display:inline-grid; place-items:center; min-width:24px; height:22px; padding:0 8px; border-radius:7px;
            font-weight:800; font-size:11px; color:#fff; }}
        .nk-bar {{ position:relative; }}
        .nk-bar .fill {{ position:absolute; left:6px; top:50%; transform:translateY(-50%); height:20px; border-radius:5px;
            background:color-mix(in srgb, var(--voice) 26%, transparent); z-index:0; }}
        .nk-bar .val {{ position:relative; z-index:1; }}
        .nk-bar.warm .fill {{ background:color-mix(in srgb, var(--gold) 30%, transparent); }}

        /* form controls */
        [data-baseweb="select"] > div, [data-testid="stNumberInput"] input, [data-baseweb="input"] {{
            background:var(--card) !important; border:1px solid var(--line2) !important; border-radius:10px !important; color:var(--ink) !important; }}
        [data-baseweb="select"] > div:focus-within, [data-testid="stNumberInput"] input:focus {{ border-color:var(--voice) !important; box-shadow:0 0 0 3px color-mix(in srgb, var(--voice) 24%, transparent) !important; }}
        [data-baseweb="tag"] {{ background:color-mix(in srgb, var(--voice) 22%, transparent) !important; border-radius:8px !important; color:var(--ink) !important; }}
        [data-baseweb="tag"] span {{ color:var(--ink) !important; }}
        [data-baseweb="popover"], [role="listbox"] {{ background:var(--card) !important; border:1px solid var(--line2) !important; }}
        [role="option"] {{ color:var(--ink) !important; }}
        [role="option"]:hover {{ background:color-mix(in srgb, var(--voice) 12%, transparent) !important; }}
        [data-testid="stWidgetLabel"] label {{ color:var(--soft) !important; font-weight:600; font-size:12.5px; }}

        /* segmented controls: this build renders them as a baseweb ButtonGroup
           (testid=stButtonGroup with kind="segmented_control(Active)" base buttons),
           NOT stSegmentedControl -- everything forced so the dark theme wins over
           Streamlit's base-light default (otherwise the track renders white). */
        [data-testid="stButtonGroup"]:has(button[kind^="segmented_control"]) {{
            background:var(--seg-track) !important; border:1px solid var(--line2) !important;
            border-radius:999px !important; padding:3px !important; gap:2px; display:inline-flex !important; }}
        button[kind="segmented_control"], button[kind="segmented_controlActive"] {{
            border:0 !important; border-radius:999px !important; box-shadow:none !important;
            font-family:{FONT_LABEL} !important; font-weight:600 !important; font-size:12.5px !important; padding:6px 16px !important;
            color:var(--seg-idle) !important; background:transparent !important; transition:all .15s ease; }}
        button[kind="segmented_control"] *, button[kind="segmented_controlActive"] *,
        button[kind="segmented_control"]:hover, button[kind="segmented_control"]:focus {{ background:transparent !important; }}
        button[kind="segmented_control"] * {{ color:inherit !important; }}
        button[kind="segmented_control"]:hover {{ color:var(--ink) !important; }}
        button[kind="segmented_controlActive"] {{
            background:var(--seg-active) !important; color:var(--seg-active-text) !important;
            border:1px solid var(--seg-active-border) !important; font-weight:700 !important; }}
        button[kind="segmented_controlActive"] * {{ color:var(--seg-active-text) !important; }}

        /* sparkline on KPI cards */
        .nk-card .k-spark {{ color:var(--voice); margin-top:8px; height:26px; }}
        .nk-card .k-spark svg {{ display:block; width:100%; height:26px; }}

        /* buttons (primary) */
        .stButton>button {{ border-radius:10px; border:1px solid var(--line2); background:var(--voice); color:#fff;
            font-family:{FONT_LABEL}; font-weight:700; }}
        .stButton>button:hover {{ filter:brightness(1.08); border-color:var(--voice); }}
        /* light-theme control contrast: crisper borders + readable placeholders */
        [data-baseweb="select"] > div {{ box-shadow:none; }}
        .stApp label, [data-testid="stWidgetLabel"] label {{ color:var(--soft) !important; }}

        /* ======== TABS (the sheet selector) ========
           Stable hooks are data-testid="stTabs" / "stTab" (not BaseWeb).
           No box/pill -- just a thin icon + regular-weight label; selection shown by
           red icon/text, a small trailing dot, and a red underline. */
        [data-testid="stTabs"] {{ width:100% !important; }}
        [data-testid="stTabs"] [role="tablist"] {{ display:flex !important; width:100% !important;
            flex-wrap:nowrap !important; gap:8px !important; border-bottom:1px solid var(--line2);
            padding-bottom:0; margin-bottom:14px; }}
        [data-testid="stTab"] {{ flex:1 1 0 !important; min-width:0 !important;
            display:flex !important; flex-direction:row !important; align-items:center !important;
            justify-content:center !important; gap:9px !important; text-align:center !important;
            font-family:{FONT_LABEL} !important; font-size:15px !important; font-weight:400 !important;
            letter-spacing:0; line-height:1.15 !important; white-space:nowrap !important;
            color:var(--soft) !important; padding:12px 10px !important; min-height:48px !important;
            border-radius:0 !important; background:transparent !important;
            border:0 !important; border-bottom:2px solid transparent !important;
            transition:color .16s ease, border-color .16s ease; position:relative; cursor:pointer; }}
        [data-testid="stTab"] * {{ font-size:15px !important; font-weight:400 !important;
            line-height:1.15 !important; white-space:nowrap !important; color:inherit !important; }}
        [data-testid="stTab"]::before {{ content:""; display:block; width:20px; height:20px;
            flex:0 0 auto; background-color:var(--soft); -webkit-mask-size:contain; mask-size:contain;
            -webkit-mask-repeat:no-repeat; mask-repeat:no-repeat; -webkit-mask-position:center; mask-position:center;
            transition:background-color .16s ease; }}
        [data-testid="stTab"]:hover {{ color:var(--ink) !important; }}
        [data-testid="stTab"]:hover::before {{ background-color:var(--voice); }}
        /* selected = red icon/text + red underline + small trailing dot */
        [data-testid="stTab"][aria-selected="true"] {{ color:var(--tab-active) !important;
            border-bottom:3px solid var(--tab-active) !important; }}
        [data-testid="stTab"][aria-selected="true"]::before {{ background-color:var(--tab-active) !important; }}
        [data-testid="stTab"][aria-selected="true"]::after {{ content:""; display:block; width:7px; height:7px;
            border-radius:50%; background:var(--tab-active); }}
        /* recolour Streamlit's own sliding tab indicator so only ONE colour shows per theme */
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background-color:var(--tab-active) !important; }}
        [data-testid="stTabs"] [data-baseweb="tab-border"] {{ background-color:var(--line2) !important; }}
        {tab_icon_css}
        [data-testid="stTabsScrollLeft"], [data-testid="stTabsScrollRight"] {{ display:none !important; }}
        [data-testid="stTabPanel"] {{ padding-top:16px !important; }}

        /* expanders (Marketing / Regulatory / Analytics, Data dictionary) */
        [data-testid="stExpander"] {{ border:1px solid var(--line2) !important; border-radius:16px !important;
            background:var(--card); box-shadow:0 10px 30px -22px var(--shadow); margin-bottom:10px; overflow:hidden; }}
        [data-testid="stExpander"] summary {{ font-family:{FONT_LABEL}; font-weight:700; font-size:15px; color:var(--ink); padding:6px 4px; }}
        [data-testid="stExpander"] summary:hover {{ color:var(--voice); }}
        /* deep-dive expander -> styled like the "PORTFOLIO SPLIT" section header:
           a bold blue pill + hairline rule; the whole header is the click target. */
        [class*="st-key-deepdivexp"] [data-testid="stExpander"] {{ border:none !important; background:transparent !important;
            box-shadow:none !important; margin:20px 0 4px; overflow:visible; }}
        [class*="st-key-deepdivexp"] [data-testid="stExpander"] details {{ border:none !important; background:transparent !important; }}
        [class*="st-key-deepdivexp"] [data-testid="stExpander"] summary {{ display:flex !important; align-items:center;
            gap:14px; padding:3px 2px !important; cursor:pointer; }}
        [class*="st-key-deepdivexp"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p {{
            font-family:{FONT_LABEL} !important; font-weight:800 !important; font-size:12px !important; letter-spacing:.22em !important;
            text-transform:uppercase !important; color:var(--voice) !important; margin:0 !important; white-space:nowrap;
            border:1px solid color-mix(in srgb, var(--voice) 42%, transparent); border-radius:999px;
            padding:6px 16px !important; background:color-mix(in srgb, var(--voice) 12%, transparent); }}
        [class*="st-key-deepdivexp"] [data-testid="stExpander"] summary::after {{ content:""; flex:1 1 auto; height:1px;
            background:var(--line2); order:3; }}
        [class*="st-key-deepdivexp"] [data-testid="stExpander"] summary svg {{ order:4; color:var(--voice) !important; fill:var(--voice) !important; }}
        [class*="st-key-deepdivexp"] [data-testid="stExpander"] summary:hover [data-testid="stMarkdownContainer"] p {{
            background:color-mix(in srgb, var(--voice) 20%, transparent); }}
        [class*="st-key-deepdivexp_teal"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p {{
            color:#7DE0D6 !important; border-color:color-mix(in srgb, #7DE0D6 45%, transparent);
            background:color-mix(in srgb, #002121 55%, transparent); }}
        [class*="st-key-deepdivexp_teal"] [data-testid="stExpander"] summary svg {{ color:#7DE0D6 !important; fill:#7DE0D6 !important; }}

        [data-testid="stMetricValue"] {{ font-family:{FONT_DISPLAY}; color:var(--ink); font-variant-numeric:tabular-nums; }}
        [data-testid="stMetricLabel"] {{ font-family:{FONT_LABEL}; text-transform:uppercase; letter-spacing:.1em; font-size:11px; color:var(--soft); }}

        /* tooltip help icon */
        [data-testid="stTooltipIcon"] svg {{ color:var(--soft); }}
        </style>
        """,
        unsafe_allow_html=True,
    )
