import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import os

# ══════════════════════════════════════════════════════════════
#  THEMES
# ══════════════════════════════════════════════════════════════
THEMES = {
    "Dark": {
        "bg": "#050d1a", "surface": "#0a1628", "card": "#0f1f38",
        "card2": "#13263f", "border": "#1a3050", "text": "#e8f4fd",
        "muted": "#4a7090", "accent": "#00d4ff", "accent2": "#7c3aed",
        "green": "#00e5a0", "red": "#ff4d6d", "gold": "#f59e0b",
        "pgrid": "#1a3050", "ptick": "#4a7090",
    },
    "Light": {
        "bg": "#f0f4f8", "surface": "#ffffff", "card": "#ffffff",
        "card2": "#f7fafc", "border": "#dde3ed", "text": "#1a2332",
        "muted": "#6b7fa3", "accent": "#0077b6", "accent2": "#6d28d9",
        "green": "#059669", "red": "#dc2626", "gold": "#d97706",
        "pgrid": "#e2e8f0", "ptick": "#6b7fa3",
    },
}

PIE_COLORS   = ["#00d4ff","#7c3aed","#f59e0b","#00e5a0","#ff4d6d","#f97316","#ec4899","#06b6d4"]
CLASS_COLORS = {"Equity":"#00d4ff","Mutual Fund":"#7c3aed","Gold":"#f59e0b",
                "Debt":"#00e5a0","NPS":"#f97316","Real Estate":"#ec4899"}
GOAL_EMOJIS  = ["🛡️","🏠","🎓","🌅","✈️","🚗","💍","📱"]

INCOME_CATEGORIES = [
    "Salary","Freelance / Consulting","Business Income","Dividend",
    "Rental Income","Interest Income","Capital Gains","Bonus","Gift / Windfall","Other",
]
EXPENSE_CATEGORIES = [
    "Housing / Rent","Groceries","Food & Dining","Transport","Fuel","EMI / Loan",
    "Healthcare","Insurance","Education","Entertainment","Shopping","Utilities",
    "Subscriptions","Clothing","Travel","Personal Care","Gifts & Donations",
    "Savings / Investment","Children","Other",
]
MONTHS_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
INVESTMENT_CATS = {
    "Equity":      ["Direct Equity","ETF"],
    "Mutual Fund": ["Equity MF","Debt MF","Hybrid MF","Index Fund","ELSS"],
    "Gold":        ["Gold ETF","Gold Scheme","SGB","Physical Gold"],
    "Debt":        ["Bond","RD","FD","PPF","NSC","Post Office","NCD"],
    "Real Estate": ["Plot","Apartment","REITs"],
    "Crypto":      ["Bitcoin","Ethereum","Altcoin","Other Crypto"],
    "Other":       ["Cash","Chit Fund","Other"],
}
LTCG_EXEMPTION = 125000

PERSONS = ["Gokul","Yamuna","Kavitha"]
PERSONS_FAM = ["Family","Gokul","Yamuna","Kavitha"]

# ══════════════════════════════════════════════════════════════
#  FY HELPERS
# ══════════════════════════════════════════════════════════════
def current_fy():
    t = date.today()
    return f"FY {t.year}-{str(t.year+1)[-2:]}" if t.month >= 4 else f"FY {t.year-1}-{str(t.year)[-2:]}"

def get_fy_list(years_present):
    fys = set()
    for y in years_present:
        fys.add(f"FY {y-1}-{str(y)[-2:]}")
        fys.add(f"FY {y}-{str(y+1)[-2:]}")
    return sorted(fys, reverse=True)

def fy_date_range(fy_str):
    sy = int(fy_str.replace("FY ","").split("-")[0])
    return pd.Timestamp(f"{sy}-04-01"), pd.Timestamp(f"{sy+1}-03-31")

# ══════════════════════════════════════════════════════════════
#  FORMAT HELPERS
# ══════════════════════════════════════════════════════════════
def fmt(n):
    try:
        n = float(n)
        if abs(n) >= 1e7: return f"Rs.{n/1e7:.2f} Cr"
        if abs(n) >= 1e5: return f"Rs.{n/1e5:.1f} L"
        return f"Rs.{n:,.0f}"
    except: return "Rs.0"

def fmt_nav(n):
    """Exact NAV / price display — 2-4 decimal places."""
    try:
        n = float(n)
        if n == 0: return "Rs.0"
        if abs(n) >= 1e5: return f"Rs.{n/1e5:.2f}L"
        if abs(n) >= 1000: return f"Rs.{n:,.2f}"
        if abs(n) >= 100:  return f"Rs.{n:.2f}"
        s = f"{n:.4f}".rstrip("0").rstrip(".")
        return f"Rs.{s}"
    except: return "Rs.0"

def fmt_units(qty):
    """Show exact units — up to 6 decimals, min 3."""
    try:
        s = f"{float(qty):.6f}".rstrip("0")
        if "." in s and len(s.split(".")[1]) < 3:
            s = f"{float(qty):.3f}"
        return s or "0"
    except: return "0"

def pct(n):
    try:
        n = float(n)
        return f"{'+'if n>=0 else ''}{n:.2f}%"
    except: return "0.00%"

def safe_roi(gain, invested):
    return (gain / invested * 100) if invested > 0 else 0.0

def get_theme():
    if "theme" not in st.session_state:
        st.session_state.theme = "Dark"
    return THEMES[st.session_state.theme]

def sh(title):
    T = get_theme()
    st.markdown(
        f'<div class="sh"><div class="sh-bar"></div><span class="sh-title">{title}</span></div>',
        unsafe_allow_html=True)

def info_box(msg):
    st.markdown(f'<div class="info-box">ℹ️&nbsp; {msg}</div>', unsafe_allow_html=True)

def plot_layout():
    T = get_theme()
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=T["text"], size=12),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=T["muted"], size=11)),
        margin=dict(l=10, r=10, t=36, b=10),
        xaxis=dict(gridcolor=T["pgrid"], showgrid=True, zeroline=False,
                   color=T["ptick"], tickfont=dict(size=11)),
        yaxis=dict(gridcolor=T["pgrid"], showgrid=True, zeroline=False,
                   color=T["ptick"], tickfont=dict(size=11)),
    )

# ══════════════════════════════════════════════════════════════
#  TAX CALCULATION
# ══════════════════════════════════════════════════════════════
def compute_tax_summary(inv_df, fy_str=None):
    if inv_df is None or inv_df.empty:
        return {}
    df = inv_df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for c in ["Quantity","Price","Current_Price","Invested","Current_Value","Gain"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if not fy_str:
        fy_str = current_fy()
    fy_start, fy_end = fy_date_range(fy_str)
    today = pd.Timestamp.today()

    buys = df[df.get("Transaction_Type", pd.Series(["BUY"]*len(df))).isin(["BUY","SIP"])] \
           if "Transaction_Type" in df.columns else df.copy()

    unreal = dict(stcg_eq=0, ltcg_eq=0, stcg_gold=0, ltcg_gold=0, stcg_debt=0, ltcg_debt=0)
    rows_detail = []

    for _, row in buys.iterrows():
        gain = float(row.get("Gain", 0))
        ac   = str(row.get("Asset_Class",""))
        cat  = str(row.get("Category","")).lower()
        dt   = row["Date"]
        name = str(row.get("Asset_Name",""))
        if pd.isna(dt): continue
        months = (today - dt).days / 30.44

        is_equity = (ac == "Equity") or (ac == "Mutual Fund" and
                    any(k in cat for k in ["equity","index","elss","hybrid"]))
        is_gold   = (ac == "Gold")
        is_debt   = (ac in ("Debt",)) or (ac == "Mutual Fund" and "debt" in cat)

        if is_equity:
            key = "stcg_eq" if months < 12 else "ltcg_eq"
            tax_rate = 0.20 if months < 12 else 0.125
            tag = "STCG" if months < 12 else "LTCG"
        elif is_gold:
            key = "stcg_gold" if months < 24 else "ltcg_gold"
            tax_rate = 0.30 if months < 24 else 0.125
            tag = "STCG" if months < 24 else "LTCG"
        elif is_debt:
            key = "stcg_debt" if months < 36 else "ltcg_debt"
            tax_rate = 0.30
            tag = "STCG" if months < 36 else "LTCG"
        else:
            continue

        if gain > 0:
            unreal[key] += gain

        rows_detail.append({
            "Asset": name, "Class": ac,
            "Invested": float(row.get("Invested",0)),
            "Current":  float(row.get("Current_Value",0)),
            "Gain": gain, "Hold_Mo": round(months, 1),
            "Type": tag, "Tax_Rate": f"{int(tax_rate*100)}%",
            "Est_Tax": max(0, gain) * tax_rate if gain > 0 else 0,
        })

    ltcg_eq_taxable = max(0, unreal["ltcg_eq"] - LTCG_EXEMPTION)
    tax = {
        "stcg_eq":   unreal["stcg_eq"]  * 0.20,
        "ltcg_eq":   ltcg_eq_taxable    * 0.125,
        "stcg_gold": unreal["stcg_gold"] * 0.30,
        "ltcg_gold": unreal["ltcg_gold"] * 0.125,
        "debt":      (unreal["stcg_debt"] + unreal["ltcg_debt"]) * 0.30,
    }
    tax["total"] = sum(tax.values())

    return {
        "fy": fy_str, "unreal": unreal, "tax": tax,
        "ltcg_exemption_used": min(unreal["ltcg_eq"], LTCG_EXEMPTION),
        "ltcg_eq_taxable": ltcg_eq_taxable,
        "detail_rows": rows_detail,
    }

# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════
def inject_css():
    t = get_theme()
    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{{font-family:'Inter',sans-serif!important;background-color:{t['bg']}!important;color:{t['text']}!important;}}
[data-testid="stAppViewContainer"],[data-testid="stAppViewBlockContainer"],
[data-testid="stMain"],[data-testid="stMainBlockContainer"],.block-container,
.main .block-container{{background:{t['bg']}!important;}}
.block-container{{padding-top:1.4rem!important;padding-bottom:1rem!important;max-width:100%!important;}}
[data-baseweb="tab-panel"]{{background:{t['bg']}!important;}}
section[data-testid="stSidebar"]{{background:{t['surface']}!important;border-right:1px solid {t['border']}!important;
  min-width:270px!important;max-width:270px!important;transform:none!important;visibility:visible!important;display:block!important;}}
section[data-testid="stSidebar"] *{{color:{t['text']}!important;}}
[data-testid="collapsedControl"],[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarNavCollapseButton"],button[data-testid="stBaseButton-headerNoPadding"],
[data-testid="stSidebarNav"],[data-testid="stSidebarNavItems"],nav[data-testid="stSidebarNav"],
section[data-testid="stSidebar"] nav,.st-emotion-cache-1gwvy71,.st-emotion-cache-rb5j44
{{display:none!important;width:0!important;height:0!important;}}
header[data-testid="stHeader"]{{background:{t['bg']}!important;border-bottom:1px solid {t['border']}!important;height:0!important;min-height:0!important;}}
footer,#MainMenu,[data-testid="stToolbar"],[data-testid="stDecoration"]{{display:none!important;}}
[data-testid="stMetric"]{{background:{t['card']}!important;border:1px solid {t['border']}!important;border-radius:14px!important;padding:16px 20px!important;}}
[data-testid="stMetricLabel"]>div{{font-size:11px!important;font-weight:600!important;text-transform:uppercase;letter-spacing:.07em;color:{t['muted']}!important;}}
[data-testid="stMetricValue"]>div{{font-size:24px!important;font-weight:800!important;color:{t['text']}!important;}}
[data-testid="stMetricDelta"] svg{{display:none;}}
[data-testid="stMetricDelta"]{{font-size:12px!important;font-weight:600!important;}}
h1{{font-size:26px!important;font-weight:800!important;color:{t['text']}!important;margin-bottom:4px!important;}}
h2{{font-size:17px!important;font-weight:700!important;color:{t['text']}!important;margin-top:0!important;}}
h3{{font-size:14px!important;font-weight:700!important;color:{t['text']}!important;}}
p,label,span,div{{color:{t['text']};}}
hr{{border:none!important;border-top:1px solid {t['border']}!important;margin:18px 0!important;}}
[data-testid="stAlert"],div[class*="stAlert"],.stInfo,.stSuccess,.stWarning,.stError
{{background:{t['card']}!important;border:1px solid {t['border']}!important;border-radius:10px!important;color:{t['text']}!important;}}
[data-testid="stSelectbox"]>div>div,[data-testid="stSelectbox"]>div>div>div,
[data-testid="stTextInput"]>div>div,[data-testid="stTextInput"]>div>div>input,
[data-testid="stNumberInput"]>div,[data-testid="stNumberInput"]>div>div,
[data-testid="stNumberInput"]>div>div>input,
[data-testid="stTextArea"]>div,[data-testid="stTextArea"]>div>div,[data-testid="stTextArea"] textarea
{{background:{t['surface']}!important;border:1px solid {t['border']}!important;color:{t['text']}!important;border-radius:10px!important;font-size:13px!important;}}
[data-testid="stNumberInput"] button,
[data-testid="stNumberInput"] button *
{{background:{t['card2']}!important;border:1px solid {t['border']}!important;color:{t['text']}!important;border-radius:6px!important;}}
[data-testid="stNumberInput"] button svg path,
[data-testid="stNumberInput"] button svg rect
{{fill:{t['text']}!important;stroke:{t['text']}!important;background:transparent!important;}}
[data-testid="stDateInput"]>div,[data-testid="stDateInput"]>div>div,[data-testid="stDateInput"] input
{{background:{t['surface']}!important;border-color:{t['border']}!important;color:{t['text']}!important;border-radius:10px!important;}}
select option{{background:{t['surface']}!important;color:{t['text']}!important;}}
.js-plotly-plot,.plotly,.plot-container,[data-testid="stPlotlyChart"]>div,.stPlotlyChart{{background:transparent!important;}}
.modebar{{background:transparent!important;}}
[data-baseweb="popover"] [role="listbox"],[data-baseweb="popover"] ul
{{background:{t['surface']}!important;border:1px solid {t['border']}!important;border-radius:10px!important;}}
[data-baseweb="popover"] li,[data-baseweb="popover"] [role="option"]
{{background:{t['surface']}!important;color:{t['text']}!important;}}
[data-baseweb="popover"] li:hover{{background:{t['card2']}!important;}}
[data-testid="column"],div[class*="element-container"],
div[class*="stMarkdown"],div[class*="stText"]{{background:transparent!important;}}
.stButton>button{{background:linear-gradient(135deg,{t['accent']},{t['accent2']})!important;color:white!important;
  border:none!important;border-radius:10px!important;font-weight:700!important;font-size:13px!important;
  padding:10px 24px!important;font-family:'Inter',sans-serif!important;}}
.stButton>button:hover{{opacity:.85!important;}}
[data-testid="stHorizontalBlock"] .stButton>button
{{background:{t['card2']}!important;color:{t['text']}!important;border:1px solid {t['border']}!important;
  padding:6px 8px!important;font-size:12px!important;font-weight:600!important;}}
[data-testid="stHorizontalBlock"] .stButton>button:hover{{background:{t['surface']}!important;opacity:1!important;}}
[data-testid="stSidebar"] .stButton>button{{background:{t['surface']}!important;color:{t['text']}!important;
  border:1px solid {t['border']}!important;padding:5px 10px!important;font-weight:500!important;font-size:13px!important;}}
[data-testid="stSidebar"] .nav-btn-active .stButton>button{{background:{t['card']}!important;
  color:{t['accent']}!important;border:1px solid {t['border']}!important;font-weight:700!important;}}
[data-testid="stSidebar"] .stButton>button:hover{{background:{t['card2']}!important;opacity:1!important;}}
.stProgress>div>div{{background:linear-gradient(to right,{t['accent']},{t['accent2']})!important;border-radius:6px!important;}}
.stProgress>div{{background:{t['border']}!important;border-radius:6px!important;}}
[data-testid="stForm"]{{background:{t['card']}!important;border:1px solid {t['border']}!important;border-radius:14px!important;padding:20px!important;}}
.stCaption,[data-testid="stCaptionContainer"]{{color:{t['muted']}!important;font-size:12px!important;}}
.stTabs [data-baseweb="tab-list"]{{background:{t['surface']}!important;border-radius:10px!important;
  gap:4px!important;padding:4px!important;border:1px solid {t['border']}!important;}}
.stTabs [data-baseweb="tab"]{{background:transparent!important;color:{t['muted']}!important;
  border-radius:8px!important;font-weight:600!important;font-size:13px!important;}}
.stTabs [aria-selected="true"]{{background:{t['card']}!important;color:{t['accent']}!important;border:1px solid {t['border']}!important;}}
.ft-wrap{{background:{t['card']};border:1px solid {t['border']};border-radius:14px;overflow:hidden;margin-bottom:6px;}}
.ft{{width:100%;border-collapse:collapse;font-size:13px;font-family:'Inter',sans-serif;}}
.ft thead tr{{background:{t['card2']};border-bottom:2px solid {t['border']};}}
.ft thead th{{padding:10px 15px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:{t['muted']};white-space:nowrap;}}
.ft tbody tr{{border-bottom:1px solid {t['border']}55;}}
.ft tbody tr:hover{{background:{t['card2']};}}
.ft tbody td{{padding:11px 15px;color:{t['text']};font-weight:500;vertical-align:middle;}}
.ft .mono{{font-family:'Courier New',monospace;font-weight:600;font-size:12.5px;}}
.ft .bold{{font-weight:700;color:{t['text']};}}
.badge{{border-radius:6px;padding:2px 9px;font-size:11px;font-weight:700;display:inline-block;white-space:nowrap;}}
.sh{{display:flex;align-items:center;gap:10px;margin-bottom:16px;margin-top:2px;}}
.sh-bar{{width:4px;height:22px;background:linear-gradient(to bottom,{t['accent']},{t['accent2']});border-radius:2px;flex-shrink:0;}}
.sh-title{{font-size:16px;font-weight:800;color:{t['text']};margin:0;}}
.info-box{{background:{t['card']};border:1px solid {t['border']};border-left:4px solid {t['accent']};
  border-radius:10px;padding:14px 18px;color:{t['muted']};font-size:13px;margin-bottom:12px;}}
.nw-widget{{background:{t['card']};border:1px solid {t['border']};border-radius:12px;padding:12px 14px;text-align:center;margin-top:4px;}}
</style>
<script>
(function keepSidebarOpen(){{
  function expand(){{
    var sb=document.querySelector('section[data-testid="stSidebar"]');
    if(sb&&sb.getAttribute('aria-expanded')==='false'){{
      sb.setAttribute('aria-expanded','true');
      sb.style.transform='none';sb.style.visibility='visible';sb.style.display='block';
    }}
  }}
  expand();
  var obs=new MutationObserver(expand);
  obs.observe(document.body,{{subtree:true,attributes:true,attributeFilter:['aria-expanded']}});
}})();
</script>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════
def render_sidebar(active_page):
    T = get_theme()
    with st.sidebar:
        st.markdown(f"""
        <div style='text-align:center;padding:6px 0 10px'>
          <div style='font-size:32px'>💼</div>
          <div style='font-size:14px;font-weight:800;color:{T["text"]}'>Finance Track</div>
          <div style='font-size:10px;color:{T["muted"]}'>Family Portfolio System</div>
        </div>""", unsafe_allow_html=True)

        cl, cr = st.columns(2)
        if cl.button("🌙 Dark",  use_container_width=True, key="sb_dark"):
            st.session_state.theme = "Dark"; st.rerun()
        if cr.button("☀️ Light", use_container_width=True, key="sb_light"):
            st.session_state.theme = "Light"; st.rerun()

        st.markdown(f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{T["muted"]};margin:10px 0 4px 2px">Portfolio View</div>',
                    unsafe_allow_html=True)
        st.selectbox("", PERSONS_FAM, key="sb_person", label_visibility="collapsed")

        st.markdown(f'<hr style="border-color:{T["border"]};margin:8px 0">', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{T["muted"]};margin-bottom:6px">Navigate</div>',
                    unsafe_allow_html=True)

        pages = [
            ("📊","Dashboard",         "app.py"),
            ("➕","Add Investment",    "pages/1_Add_Investment.py"),
            ("📋","Transactions",      "pages/2_Transactions.py"),
            ("📈","Equity",            "pages/3_Equity.py"),
            ("🏦","Mutual Funds",      "pages/4_Mutual_Funds.py"),
            ("🥇","Gold",              "pages/5_Gold.py"),
            ("🏛️","Debt",              "pages/6_Debt.py"),
            ("🎖️","NPS",               "pages/7_NPS.py"),
            ("💵","Income",            "pages/8_Income.py"),
            ("💸","Expenses",          "pages/9_Expenses.py"),
            ("🎯","Goals",             "pages/10_Goals.py"),
            ("📆","Cash Flow",         "pages/11_Cash_Flow.py"),
            ("🧾","Tax Summary",       "pages/12_Tax_Summary.py"),
            ("💰","Dividend Ledger",   "pages/13_Dividend_Ledger.py"),
        ]

        st.markdown(f"""<style>
        [data-testid="stSidebar"] .nav-btn>button{{background:transparent!important;border:1px solid transparent!important;
          border-radius:8px!important;padding:5px 10px!important;width:100%!important;text-align:left!important;
          color:{T['text']}!important;font-size:13px!important;font-weight:500!important;margin-bottom:1px!important;
          justify-content:flex-start!important;}}
        [data-testid="stSidebar"] .nav-btn>button:hover{{background:{T['card2']}!important;border-color:{T['border']}!important;}}
        [data-testid="stSidebar"] .nav-btn-active>button{{background:{T['card']}!important;
          border:1px solid {T['border']}!important;color:{T['accent']}!important;font-weight:700!important;}}
        </style>""", unsafe_allow_html=True)

        for icon, name, path in pages:
            is_active = (name == active_page)
            css_class = "nav-btn-active" if is_active else "nav-btn"
            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
            if st.button(f"{icon}  {name}", key=f"nav_{name}", use_container_width=True):
                st.switch_page(path)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Monthly Cash Flow widget ──
        st.markdown(f'<hr style="border-color:{T["border"]};margin:8px 0">', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{T["muted"]};margin-bottom:6px">💰 This Month\'s Flow</div>',
                    unsafe_allow_html=True)

        _d = get_data()
        inc_df = _d.get("income", pd.DataFrame())
        exp_df = _d.get("expenses", pd.DataFrame())

        today = pd.Timestamp.today()
        cur_m = today.to_period("M")
        prv_m = (today - pd.DateOffset(months=1)).to_period("M")

        def _ms(df, period):
            if df is None or df.empty: return 0.0
            d = df.copy()
            d["Date"]   = pd.to_datetime(d.get("Date", pd.Series()), errors="coerce")
            d["Amount"] = pd.to_numeric(d.get("Amount", pd.Series()), errors="coerce").fillna(0)
            d["M"]      = d["Date"].dt.to_period("M")
            return float(d[d["M"] == period]["Amount"].sum())

        inc_c = _ms(inc_df, cur_m); exp_c = _ms(exp_df, cur_m)
        inc_p = _ms(inc_df, prv_m); exp_p = _ms(exp_df, prv_m)
        net = inc_c - exp_c
        nc  = T["green"] if net >= 0 else T["red"]
        sr  = (net / inc_c * 100) if inc_c > 0 else 0
        ic  = ((inc_c - inc_p) / inc_p * 100) if inc_p > 0 else 0
        ec  = ((exp_c - exp_p) / exp_p * 100) if exp_p > 0 else 0
        ic_c = T["green"] if ic >= 0 else T["red"]
        ec_c = T["red"]   if ec >= 0 else T["green"]

        inc_badge = (f'<span style="font-size:9px;color:{ic_c};background:transparent"> '
                     f'{"▲" if ic>=0 else "▼"}{abs(ic):.0f}%</span>') if inc_p > 0 else ""
        exp_badge = (f'<span style="font-size:9px;color:{ec_c};background:transparent"> '
                     f'{"▲" if ec>=0 else "▼"}{abs(ec):.0f}%</span>') if exp_p > 0 else ""

        st.markdown(f"""
        <div style='background:{T["card"]};border:1px solid {T["border"]};border-radius:12px;padding:11px 13px;'>
          <div style='font-size:10px;color:{T["muted"]};margin-bottom:7px;font-weight:600;background:transparent'>{today.strftime("%B %Y")}</div>
          <div style='display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid {T["border"]}44;background:transparent'>
            <span style='font-size:11px;color:{T["muted"]};background:transparent'>📥 Income</span>
            <span style='font-size:12px;font-weight:700;color:{T["green"]};background:transparent'>{fmt(inc_c)} {inc_badge}</span>
          </div>
          <div style='display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid {T["border"]}44;background:transparent;margin-top:3px'>
            <span style='font-size:11px;color:{T["muted"]};background:transparent'>📤 Expense</span>
            <span style='font-size:12px;font-weight:700;color:{T["red"]};background:transparent'>{fmt(exp_c)} {exp_badge}</span>
          </div>
          <div style='display:flex;justify-content:space-between;margin-top:8px;padding-top:6px;border-top:1px solid {T["border"]}44;background:transparent'>
            <span style='font-size:10px;font-weight:700;color:{T["muted"]};background:transparent'>Net</span>
            <span style='font-size:13px;font-weight:800;color:{nc};background:transparent'>{"+" if net>=0 else ""}{fmt(net)}</span>
          </div>
          <div style='background:{T["border"]};border-radius:3px;height:3px;overflow:hidden;margin-top:6px;'>
            <div style='width:{min(abs(sr),100):.0f}%;height:100%;background:{nc};border-radius:3px'></div>
          </div>
          <div style='font-size:9px;color:{T["muted"]};margin-top:3px;text-align:right;background:transparent'>{sr:.1f}% savings rate</div>
        </div>""", unsafe_allow_html=True)

        # ── Refresh Prices button ──
        st.markdown(f'<hr style="border-color:{T["border"]};margin:8px 0">', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{T["muted"]};margin-bottom:6px">🔄 Live Prices</div>',
                    unsafe_allow_html=True)
        _inv     = _d.get("inv", pd.DataFrame())
        _is_demo = _d.get("demo", True)
        if st.button("🔄 Refresh Prices", use_container_width=True, key="sb_refresh_prices"):
            if _is_demo:
                st.toast("Connect credentials.json for live prices", icon="⚠️")
            else:
                try:
                    from utils.price_updater import fetch_all_prices, update_prices_sheet
                    asset_list = _inv["Asset_Name"].dropna().unique().tolist()
                    inv_cols   = ["Asset_Name","Asset_Class","Category"] + \
                                 (["Ticker"] if "Ticker" in _inv.columns else [])
                    inv_json   = _inv[inv_cols].drop_duplicates("Asset_Name").to_json(orient="records")
                    with st.spinner("Fetching..."):
                        result   = fetch_all_prices(asset_list, inv_json)
                        ok, fail = update_prices_sheet(get_sheet(), result["prices"])
                        if ok > 0:
                            st.toast(f"✅ {ok} prices updated", icon="✅")
                            st.cache_data.clear(); st.rerun()
                        else:
                            st.toast("⚠️ No prices updated", icon="⚠️")
                except Exception as e:
                    st.toast(f"Error: {str(e)[:60]}", icon="❌")
        last = st.session_state.get("last_price_sync","")
        if last:
            st.caption(f"Last sync: {last}")


# ══════════════════════════════════════════════════════════════
#  GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════
def _find_credentials():
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "..", "credentials.json"),
        os.path.join(base, "credentials.json"),
        "credentials.json",
        os.path.join(os.path.expanduser("~"), "credentials.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None

@st.cache_resource
def get_sheet():
    sc = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
    cred_path = _find_credentials()
    if not cred_path:
        raise FileNotFoundError("credentials.json not found")
    cr = Credentials.from_service_account_file(cred_path, scopes=sc)
    return gspread.authorize(cr).open("Family Portfolio System")

@st.cache_data(ttl=300)
def load_all_data():
    try:
        s = get_sheet()
        inv    = pd.DataFrame(s.worksheet("Investment_Ledger").get_all_records())
        prices = pd.DataFrame(s.worksheet("Current_Prices").get_all_records())
        def safe(n):
            try:    return pd.DataFrame(s.worksheet(n).get_all_records())
            except: return pd.DataFrame()
        return dict(inv=inv, prices=prices,
                    income=safe("Income_Ledger"), expenses=safe("Expenditure_Ledger"),
                    nps=safe("NPS_Ledger"), dividend=safe("Dividend_Ledger"),
                    goals=safe("Goals"), demo=False)
    except FileNotFoundError:
        return dict(inv=pd.DataFrame(), prices=pd.DataFrame(), income=pd.DataFrame(),
                    expenses=pd.DataFrame(), nps=pd.DataFrame(), dividend=pd.DataFrame(),
                    goals=pd.DataFrame(), demo=True)
    except Exception:
        return dict(inv=pd.DataFrame(), prices=pd.DataFrame(), income=pd.DataFrame(),
                    expenses=pd.DataFrame(), nps=pd.DataFrame(), dividend=pd.DataFrame(),
                    goals=pd.DataFrame(), demo=True)

def save_row(sheet_name, row):
    try:
        get_sheet().worksheet(sheet_name).append_row(row, value_input_option="USER_ENTERED")
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False

def get_data():
    data = load_all_data()
    if data["demo"]:
        return _demo_data()
    return data

def build_investment_df(inv, prices, person="Family"):
    df = inv.copy()
    if person != "Family" and "Person" in df.columns:
        df = df[df["Person"] == person]
    if df.empty:
        return df
    if not prices.empty and "Asset_Name" in prices.columns and "Current_Price" in prices.columns:
        pc = prices[["Asset_Name","Current_Price"]].copy()
        pc["Current_Price"] = pd.to_numeric(pc["Current_Price"], errors="coerce").fillna(0)
        pc = pc.drop_duplicates(subset="Asset_Name", keep="last")
        df = df.merge(pc, on="Asset_Name", how="left")
    else:
        df["Current_Price"] = 0
    for c in ["Quantity","Price","Current_Price"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["Invested"]      = df["Quantity"] * df["Price"]
    df["Current_Value"] = df["Quantity"] * df["Current_Price"]
    df["Gain"]          = df["Current_Value"] - df["Invested"]
    df["Date"]          = pd.to_datetime(df["Date"], errors="coerce")
    return df

# ══════════════════════════════════════════════════════════════
#  DEMO DATA
# ══════════════════════════════════════════════════════════════
def _demo_data():
    inv = pd.DataFrame([
        dict(Person="Gokul",  Asset_Class="Equity",      Category="Direct Equity", Asset_Name="Reliance Industries", Tag="Large Cap", Ticker="RELIANCE", Transaction_Type="BUY", Quantity=50,    Price=2400,  Date="2023-01-15", Notes=""),
        dict(Person="Gokul",  Asset_Class="Equity",      Category="Direct Equity", Asset_Name="HDFC Bank",           Tag="Large Cap", Ticker="HDFCBANK", Transaction_Type="BUY", Quantity=30,    Price=1600,  Date="2023-03-10", Notes=""),
        dict(Person="Yamuna", Asset_Class="Mutual Fund",  Category="Equity MF",    Asset_Name="EDELWEISS NLM250",    Tag="Index",     Ticker="INF754K01NR9", Transaction_Type="SIP", Quantity=72.565, Price=17.23, Date="2025-11-06", Notes=""),
        dict(Person="Yamuna", Asset_Class="Mutual Fund",  Category="Equity MF",    Asset_Name="EDELWEISS NLM250",    Tag="Index",     Ticker="INF754K01NR9", Transaction_Type="SIP", Quantity=71.506, Price=17.48, Date="2026-02-09", Notes=""),
        dict(Person="Gokul",  Asset_Class="Gold",         Category="Gold ETF",     Asset_Name="GOLDBEES",            Tag="Commodity", Ticker="GOLDBEES", Transaction_Type="BUY", Quantity=10,    Price=74.33, Date="2025-02-01", Notes=""),
        dict(Person="Gokul",  Asset_Class="Debt",         Category="FD",           Asset_Name="SBI FD 7.5%",         Tag="Fixed",     Ticker="",         Transaction_Type="BUY", Quantity=1,     Price=200000, Date="2024-01-01", Notes="2yr"),
    ])
    prices = pd.DataFrame([
        dict(Asset_Name="Reliance Industries", Current_Price=2650),
        dict(Asset_Name="HDFC Bank",           Current_Price=1720),
        dict(Asset_Name="EDELWEISS NLM250",    Current_Price=15.85),
        dict(Asset_Name="GOLDBEES",            Current_Price=82.5),
        dict(Asset_Name="SBI FD 7.5%",         Current_Price=200000),
    ])
    income = pd.DataFrame([
        dict(Date="2026-03-01", Person="Gokul",  Category="Salary",  Amount=95000, Note="March salary"),
        dict(Date="2026-03-05", Person="Yamuna", Category="Salary",  Amount=72000, Note="March salary"),
        dict(Date="2026-02-01", Person="Gokul",  Category="Salary",  Amount=95000, Note="Feb salary"),
        dict(Date="2026-02-05", Person="Yamuna", Category="Salary",  Amount=72000, Note="Feb salary"),
    ])
    expenses = pd.DataFrame([
        dict(Date="2026-03-03", Person="Gokul",  Category="Housing / Rent", Amount=19000, Note="Rent"),
        dict(Date="2026-03-08", Person="Family", Category="Groceries",      Amount=7600,  Note="Groceries"),
        dict(Date="2026-03-15", Person="Gokul",  Category="EMI / Loan",     Amount=12000, Note="Car EMI"),
        dict(Date="2026-02-03", Person="Gokul",  Category="Housing / Rent", Amount=19000, Note="Rent"),
    ])
    nps = pd.DataFrame([
        dict(Date="2026-01-15", Person="Gokul", Tier="Tier I", Fund_Manager="SBI Pension", Asset_Class="Equity (E)", Amount=5000, NAV=42.35, Units=118.065, Current_NAV=44.20),
        dict(Date="2026-02-15", Person="Gokul", Tier="Tier I", Fund_Manager="SBI Pension", Asset_Class="Equity (E)", Amount=5000, NAV=43.10, Units=116.009, Current_NAV=44.20),
    ])
    goals = pd.DataFrame([
        dict(Goal="Emergency Fund",    Target=600000,  Current=420000, Deadline="Dec 2025"),
        dict(Goal="Home Down Payment", Target=2000000, Current=680000, Deadline="Dec 2027"),
        dict(Goal="Retirement Corpus", Target=30000000,Current=1890000,Deadline="Apr 2045"),
    ])
    return dict(inv=inv, prices=prices, income=income, expenses=expenses,
                nps=nps, dividend=pd.DataFrame(), goals=goals, demo=True)
