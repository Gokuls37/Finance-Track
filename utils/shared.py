import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# ══════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════
THEMES = {
    "Dark": {
        "bg":      "#050d1a", "surface": "#0a1628", "card":  "#0f1f38",
        "card2":   "#13263f", "border":  "#1a3050", "text":  "#e8f4fd",
        "muted":   "#4a7090", "muted2":  "#2a4a6a", "accent":"#00d4ff",
        "accent2": "#7c3aed", "green":   "#00e5a0", "red":   "#ff4d6d",
        "gold":    "#f59e0b", "pgrid":   "#1a3050", "ptick": "#4a7090",
    },
    "Light": {
        "bg":      "#f0f4f8", "surface": "#ffffff",  "card":  "#ffffff",
        "card2":   "#f7fafc", "border":  "#dde3ed",  "text":  "#1a2332",
        "muted":   "#6b7fa3", "muted2":  "#a0aec0",  "accent":"#0077b6",
        "accent2": "#6d28d9", "green":   "#059669",  "red":   "#dc2626",
        "gold":    "#d97706", "pgrid":   "#e2e8f0",  "ptick": "#6b7fa3",
    },
}

PIE_COLORS   = ["#00d4ff","#7c3aed","#f59e0b","#00e5a0","#ff4d6d","#f97316","#ec4899"]
CLASS_COLORS = {"Equity":"#00d4ff","Mutual Fund":"#7c3aed","Gold":"#f59e0b","Debt":"#00e5a0","NPS":"#f97316"}
GOAL_COLORS  = ["#00d4ff","#00e5a0","#f59e0b","#7c3aed","#ec4899","#f97316"]
GOAL_ICONS   = ["🛡️","🏠","🎓","🌅","✈️","🚗","💍","📱"]

INCOME_CATEGORIES = [
    "Salary","Freelance / Consulting","Business Income",
    "Dividend","Rental Income","Interest Income",
    "Capital Gains","Bonus","Gift / Windfall","Other",
]
EXPENSE_CATEGORIES = [
    "Housing / Rent","Groceries","Food & Dining",
    "Transport","Fuel","EMI / Loan","Healthcare","Insurance",
    "Education","Entertainment","Shopping","Utilities",
    "Subscriptions","Clothing","Travel","Personal Care",
    "Gifts & Donations","Savings / Investment","Children","Other",
]
MONTHS_ORDER  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
INVESTMENT_CATS = {
    "Equity":      ["Direct Equity","ETF"],
    "Mutual Fund": ["Equity MF","Debt MF","Hybrid MF","Index Fund","ELSS"],
    "Gold":        ["Gold ETF","Gold Scheme","SGB","Physical Gold"],
    "Debt":        ["Bond","RD","FD","PPF","NSC","Post Office"],
    "NPS":         ["Equity (E)","Corporate (C)","Government (G)","Alternative (A)"],
    "Real Estate": ["Plot","Apartment","REITs"],
    "Crypto":      ["Bitcoin","Ethereum","Altcoin","Other Crypto"],
    "Other":       ["Cash","Chit Fund","Other"],
}

# Indian tax constants (post-July 2024 budget)
LTCG_EXEMPTION = 125000   # Rs.1.25 L equity LTCG exemption


# ══════════════════════════════════════════════════════════════
#  FINANCIAL YEAR HELPERS
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
#  HELPERS
# ══════════════════════════════════════════════════════════════
def fmt(n):
    try:
        n = float(n)
        if abs(n) >= 1e7: return f"Rs.{n/1e7:.2f} Cr"
        if abs(n) >= 1e5: return f"Rs.{n/1e5:.1f} L"
        return f"Rs.{n:,.0f}"
    except: return "Rs.0"

def fmt_nav(n):
    """Format NAV / unit price with full decimal precision."""
    try:
        n = float(n)
        if n == 0: return "Rs.0"
        if abs(n) >= 1e5: return f"Rs.{n/1e5:.2f}L"
        if abs(n) >= 1000: return f"Rs.{n:,.2f}"
        if abs(n) >= 100:  return f"Rs.{n:.2f}"
        # For small NAV values (like MF NAV 15.85, 17.42) — show 4 decimals, strip trailing zeros
        s = f"{n:.4f}".rstrip("0").rstrip(".")
        return f"Rs.{s}"
    except:
        return "Rs.0"

def pct(n):
    try:
        n = float(n)
        return f"{'+'if n>=0 else ''}{n:.2f}%"
    except: return "0.00%"

def safe_roi(gain, invested):
    return (gain/invested*100) if invested>0 else 0.0

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
        font=dict(family="Inter",color=T["text"],size=12),
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color=T["muted"],size=11)),
        margin=dict(l=10,r=10,t=36,b=10),
        xaxis=dict(gridcolor=T["pgrid"],showgrid=True,zeroline=False,color=T["ptick"],tickfont=dict(size=11)),
        yaxis=dict(gridcolor=T["pgrid"],showgrid=True,zeroline=False,color=T["ptick"],tickfont=dict(size=11)),
    )


# ══════════════════════════════════════════════════════════════
#  TAX CALCULATION
# ══════════════════════════════════════════════════════════════
def compute_tax_summary(inv_df, fy_str=None):
    if inv_df is None or inv_df.empty:
        return {}
    df = inv_df.copy()
    df["Date"]          = pd.to_datetime(df["Date"], errors="coerce")
    df["Quantity"]      = pd.to_numeric(df["Quantity"],     errors="coerce").fillna(0)
    df["Price"]         = pd.to_numeric(df["Price"],        errors="coerce").fillna(0)
    df["Current_Price"] = pd.to_numeric(df.get("Current_Price", pd.Series([0]*len(df))), errors="coerce").fillna(0)
    df["Invested"]      = df["Quantity"] * df["Price"]
    df["Current_Value"] = df["Quantity"] * df["Current_Price"]
    df["Gain"]          = df["Current_Value"] - df["Invested"]

    today = pd.Timestamp.today()
    if not fy_str:
        fy_str = current_fy()
    fy_start, fy_end = fy_date_range(fy_str)

    # Realized: SELL within FY
    sells = pd.DataFrame()
    if "Transaction_Type" in df.columns:
        sells = df[(df["Transaction_Type"]=="SELL") &
                   (df["Date"]>=fy_start) & (df["Date"]<=fy_end)].copy()

    # Compute hold period and categorize each position
    buys = df.copy()
    if "Transaction_Type" in df.columns:
        buys = df[df["Transaction_Type"].isin(["BUY","SIP"])].copy()

    rows_detail = []
    unreal = dict(stcg_eq=0,ltcg_eq=0,stcg_gold=0,ltcg_gold=0,stcg_debt=0,ltcg_debt=0)
    real   = dict(stcg_eq=0,ltcg_eq=0,stcg_gold=0,ltcg_gold=0,stcg_debt=0,ltcg_debt=0)

    for _, row in buys.iterrows():
        gain = float(row["Gain"])
        ac   = str(row.get("Asset_Class",""))
        cat  = str(row.get("Category","")).lower()
        dt   = row["Date"]
        name = str(row.get("Asset_Name",""))
        if pd.isna(dt): continue
        months = (today - dt).days / 30.44

        is_equity = (ac=="Equity") or (ac=="Mutual Fund" and ("equity" in cat or "index" in cat or "elss" in cat))
        is_gold   = (ac=="Gold")
        is_debt   = (ac in ("Debt","NPS")) or (ac=="Mutual Fund" and "debt" in cat)

        if is_equity:
            tag = "STCG" if months<12 else "LTCG"
            key = "stcg_eq" if months<12 else "ltcg_eq"
            tax_rate = 0.20 if months<12 else 0.125
            threshold = 12
        elif is_gold:
            tag = "STCG" if months<24 else "LTCG"
            key = "stcg_gold" if months<24 else "ltcg_gold"
            tax_rate = 0.30 if months<24 else 0.125
            threshold = 24
        elif is_debt:
            tag = "STCG" if months<36 else "LTCG"
            key = "stcg_debt" if months<36 else "ltcg_debt"
            tax_rate = 0.30
            threshold = 36
        else:
            continue

        if gain > 0:
            unreal[key] += gain

        rows_detail.append({
            "Asset": name,
            "Class": ac,
            "Invested": float(row["Invested"]),
            "Current":  float(row["Current_Value"]),
            "Gain":     gain,
            "Hold_Mo":  round(months,1),
            "Type":     tag,
            "Tax_Rate": f"{int(tax_rate*100)}%",
            "Est_Tax":  max(0,gain)*tax_rate if gain>0 else 0,
        })

    # Equity LTCG exemption
    ltcg_eq_taxable = max(0, unreal["ltcg_eq"] - LTCG_EXEMPTION)
    tax = {
        "stcg_eq":   unreal["stcg_eq"]   * 0.20,
        "ltcg_eq":   ltcg_eq_taxable      * 0.125,
        "stcg_gold": unreal["stcg_gold"]  * 0.30,
        "ltcg_gold": unreal["ltcg_gold"]  * 0.125,
        "debt":      (unreal["stcg_debt"]+unreal["ltcg_debt"]) * 0.30,
    }
    tax["total"] = sum(tax.values())

    return {
        "fy": fy_str,
        "unreal": unreal,
        "tax": tax,
        "ltcg_exemption_used": min(unreal["ltcg_eq"], LTCG_EXEMPTION),
        "ltcg_eq_taxable": ltcg_eq_taxable,
        "detail_rows": rows_detail,
        "sells": sells,
    }


# ══════════════════════════════════════════════════════════════
#  CSS  — sidebar force-open, full theme coverage
# ══════════════════════════════════════════════════════════════
def inject_css():
    t = get_theme()
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Base ── */
html,body,[class*="css"],.stApp{{font-family:'Inter',sans-serif!important;background-color:{t['bg']}!important;color:{t['text']}!important;}}
.block-container{{background:{t['bg']}!important;padding-top:1.4rem!important;padding-bottom:1rem!important;max-width:100%!important;}}
/* Force entire app background — catches all white flashes in light mode */
[data-testid="stAppViewContainer"]{{background-color:{t['bg']}!important;}}
[data-testid="stAppViewBlockContainer"]{{background-color:{t['bg']}!important;}}
[data-testid="stMain"]{{background-color:{t['bg']}!important;}}
[data-testid="stMainBlockContainer"]{{background-color:{t['bg']}!important;}}
.main .block-container{{background:{t['bg']}!important;}}
/* Fix white tab content areas */
[data-baseweb="tab-panel"]{{background:{t['bg']}!important;}}

/* ── SIDEBAR — always visible, never collapse ── */
section[data-testid="stSidebar"]{{
    background:{t['surface']}!important;
    border-right:1px solid {t['border']}!important;
    min-width:270px!important;
    max-width:270px!important;
    transform:none!important;
    visibility:visible!important;
    display:block!important;
}}
section[data-testid="stSidebar"] *{{color:{t['text']}!important;}}
/* Kill ALL collapse/expand buttons */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarNavCollapseButton"],
button[data-testid="stBaseButton-headerNoPadding"],
section[data-testid="stSidebar"] > div > div > button,
.st-emotion-cache-1gwvy71,
.st-emotion-cache-rb5j44{{display:none!important;width:0!important;height:0!important;}}
/* ── Hide Streamlit's built-in auto page nav (we use custom nav) ── */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavSeparator"],
nav[data-testid="stSidebarNav"],
section[data-testid="stSidebar"] nav,
div[data-testid="stSidebarNavLink"],
ul[data-testid="stSidebarNavItems"]{{display:none!important;height:0!important;overflow:hidden!important;}}

/* ── Header / Footer ── */
header[data-testid="stHeader"]{{background:{t['bg']}!important;border-bottom:1px solid {t['border']}!important;height:0!important;min-height:0!important;}}
footer,#MainMenu,[data-testid="stToolbar"],[data-testid="stDecoration"]{{display:none!important;}}

/* ── Metrics ── */
[data-testid="stMetric"]{{background:{t['card']}!important;border:1px solid {t['border']}!important;border-radius:14px!important;padding:16px 20px!important;}}
[data-testid="stMetricLabel"]>div{{font-size:11px!important;font-weight:600!important;text-transform:uppercase;letter-spacing:.07em;color:{t['muted']}!important;}}
[data-testid="stMetricValue"]>div{{font-size:24px!important;font-weight:800!important;color:{t['text']}!important;}}
[data-testid="stMetricDelta"] svg{{display:none;}}
[data-testid="stMetricDelta"]{{font-size:12px!important;font-weight:600!important;}}

/* ── Typography ── */
h1{{font-size:26px!important;font-weight:800!important;color:{t['text']}!important;margin-bottom:4px!important;}}
h2{{font-size:17px!important;font-weight:700!important;color:{t['text']}!important;margin-top:0!important;}}
h3{{font-size:14px!important;font-weight:700!important;color:{t['text']}!important;}}
p,label,span,div{{color:{t['text']};}}
hr{{border:none!important;border-top:1px solid {t['border']}!important;margin:18px 0!important;}}

/* ── Alert boxes ── */
[data-testid="stAlert"],div[class*="stAlert"],.stInfo,.stSuccess,.stWarning,.stError{{background:{t['card']}!important;border:1px solid {t['border']}!important;border-radius:10px!important;color:{t['text']}!important;}}
.stInfo{{border-left:4px solid {t['accent']}!important;}}
.stSuccess{{border-left:4px solid {t['green']}!important;}}
.stWarning{{border-left:4px solid {t['gold']}!important;}}
.stError{{border-left:4px solid {t['red']}!important;}}

/* ── Inputs ── */
[data-testid="stSelectbox"]>div>div,[data-testid="stSelectbox"]>div>div>div,
[data-testid="stTextInput"]>div>div,[data-testid="stTextInput"]>div>div>input,
[data-testid="stNumberInput"]>div,[data-testid="stNumberInput"]>div>div,[data-testid="stNumberInput"]>div>div>input,
[data-testid="stTextArea"]>div,[data-testid="stTextArea"]>div>div,[data-testid="stTextArea"] textarea{{
    background:{t['surface']}!important;border:1px solid {t['border']}!important;
    color:{t['text']}!important;border-radius:10px!important;font-size:13px!important;}}
[data-testid="stNumberInput"] button{{background:{t['card2']}!important;border-color:{t['border']}!important;color:{t['text']}!important;}}
[data-testid="stDateInput"]>div,[data-testid="stDateInput"]>div>div,[data-testid="stDateInput"] input{{
    background:{t['surface']}!important;border-color:{t['border']}!important;color:{t['text']}!important;border-radius:10px!important;}}
select option{{background:{t['surface']}!important;color:{t['text']}!important;}}

/* ── Plotly ── */
.js-plotly-plot,.plotly,.plot-container,[data-testid="stPlotlyChart"]>div,[data-testid="stPlotlyChart"] iframe,.stPlotlyChart{{background:transparent!important;}}
.modebar{{background:transparent!important;}}
.modebar-btn path{{fill:{t['muted']}!important;}}

/* ── Dropdowns ── */
[data-baseweb="popover"] [role="listbox"],[data-baseweb="popover"] ul{{background:{t['surface']}!important;border:1px solid {t['border']}!important;border-radius:10px!important;}}
[data-baseweb="popover"] li,[data-baseweb="popover"] [role="option"]{{background:{t['surface']}!important;color:{t['text']}!important;}}
[data-baseweb="popover"] li:hover,[data-baseweb="popover"] [role="option"]:hover{{background:{t['card2']}!important;}}

/* ── Transparent wrappers ── */
[data-testid="column"],div[class*="element-container"],div[class*="stMarkdown"],div[class*="stText"]{{background:transparent!important;}}

/* ── Buttons — main ── */
.stButton>button{{background:linear-gradient(135deg,{t['accent']},{t['accent2']})!important;color:white!important;border:none!important;border-radius:10px!important;font-weight:700!important;font-size:13px!important;padding:10px 24px!important;font-family:'Inter',sans-serif!important;}}
.stButton>button:hover{{opacity:.85!important;}}
/* Number input +/- buttons — always themed */
[data-testid="stNumberInput"] button,
[data-testid="stNumberInput"] button *{{background:{t['card2']}!important;border:1px solid {t['border']}!important;color:{t['text']}!important;border-radius:6px!important;}}
[data-testid="stNumberInput"] button:hover{{background:{t['surface']}!important;}}
[data-testid="stNumberInput"] button svg,
[data-testid="stNumberInput"] button svg path,
[data-testid="stNumberInput"] button svg rect{{fill:{t['text']}!important;stroke:{t['text']}!important;background:transparent!important;}}
/* Quick-amount buttons — plain style */
[data-testid="stHorizontalBlock"] .stButton>button{{background:{t['card2']}!important;color:{t['text']}!important;border:1px solid {t['border']}!important;padding:6px 8px!important;font-size:12px!important;font-weight:600!important;}}
[data-testid="stHorizontalBlock"] .stButton>button:hover{{background:{t['surface']}!important;opacity:1!important;}}
/* Sidebar nav buttons */
[data-testid="stSidebar"] .stButton>button{{background:{t['surface']}!important;color:{t['text']}!important;border:1px solid {t['border']}!important;padding:6px 10px!important;font-weight:500!important;font-size:13px!important;}}
[data-testid="stSidebar"] .nav-btn-active .stButton>button{{background:{t['card']}!important;color:{t['accent']}!important;border:1px solid {t['border']}!important;font-weight:700!important;}}
[data-testid="stSidebar"] .stButton>button:hover{{background:{t['card2']}!important;opacity:1!important;}}

/* ── Progress ── */
.stProgress>div>div{{background:linear-gradient(to right,{t['accent']},{t['accent2']})!important;border-radius:6px!important;}}
.stProgress>div{{background:{t['border']}!important;border-radius:6px!important;}}

/* ── Form ── */
[data-testid="stForm"]{{background:{t['card']}!important;border:1px solid {t['border']}!important;border-radius:14px!important;padding:20px!important;}}
.stCaption,[data-testid="stCaptionContainer"]{{color:{t['muted']}!important;font-size:12px!important;}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{{background:{t['surface']}!important;border-radius:10px!important;gap:4px!important;padding:4px!important;border:1px solid {t['border']}!important;}}
.stTabs [data-baseweb="tab"]{{background:transparent!important;color:{t['muted']}!important;border-radius:8px!important;font-weight:600!important;font-size:13px!important;}}
.stTabs [aria-selected="true"]{{background:{t['card']}!important;color:{t['accent']}!important;border:1px solid {t['border']}!important;}}

/* ── Custom table ── */
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

/* ── Section header ── */
.sh{{display:flex;align-items:center;gap:10px;margin-bottom:16px;margin-top:2px;}}
.sh-bar{{width:4px;height:22px;background:linear-gradient(to bottom,{t['accent']},{t['accent2']});border-radius:2px;flex-shrink:0;}}
.sh-title{{font-size:16px;font-weight:800;color:{t['text']};margin:0;}}

/* ── Info box ── */
.info-box{{background:{t['card']};border:1px solid {t['border']};border-left:4px solid {t['accent']};border-radius:10px;padding:14px 18px;color:{t['muted']};font-size:13px;margin-bottom:12px;}}

/* ── Sidebar widgets ── */
.nw-widget{{background:{t['card']};border:1px solid {t['border']};border-radius:12px;padding:12px 14px;text-align:center;margin-top:4px;}}
.cf-row{{display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid {t['border']}44;background:transparent!important;}}
.cf-label{{font-size:11px;color:{t['muted']};background:transparent!important;}}
.cf-val{{font-size:12px;font-weight:700;background:transparent!important;}}
.tax-pill{{border-radius:8px;padding:3px 10px;font-size:11px;font-weight:700;display:inline-block;}}
/* Fix sidebar card inner elements - prevent dark bg bleeding in light mode */
[data-testid="stSidebar"] div[style*="background:{t['card']}"] span,
[data-testid="stSidebar"] div[style*="background:{t['card']}"] div:not([style*="background"]) {{
  background:transparent!important;
}}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  SIDEBAR  (always-visible, nav + cash flow widget)
# ══════════════════════════════════════════════════════════════
def render_sidebar(active_page):
    T = get_theme()
    with st.sidebar:
        # Logo
        st.markdown(f"""
        <div style='text-align:center;padding:6px 0 10px'>
          <div style='font-size:32px'>💼</div>
          <div style='font-size:14px;font-weight:800;color:{T["text"]}'>Finance Track</div>
          <div style='font-size:10px;color:{T["muted"]}'>Family Portfolio System</div>
        </div>""", unsafe_allow_html=True)

        cl, cr = st.columns(2)
        if cl.button("🌙 Dark",  use_container_width=True, key="sb_dark"):
            st.session_state.theme = "Dark";  st.rerun()
        if cr.button("☀️ Light", use_container_width=True, key="sb_light"):
            st.session_state.theme = "Light"; st.rerun()

        st.markdown(f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{T["muted"]};margin:10px 0 4px 2px">Portfolio View</div>', unsafe_allow_html=True)
        st.selectbox("", ["Family","Gokul","Yamuna","Kavitha"], key="sb_person", label_visibility="collapsed")

        st.markdown(f'<hr style="border-color:{T["border"]};margin:8px 0">', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{T["muted"]};margin-bottom:6px">Navigate</div>', unsafe_allow_html=True)

        pages = [
            ("📊", "Dashboard",     "app.py"),
            ("➕", "Add Investment","pages/1_Add_Investment.py"),
            ("📋", "Transactions",  "pages/2_Transactions.py"),
            ("📈", "Equity",        "pages/3_Equity.py"),
            ("🏦", "Mutual Funds",  "pages/4_Mutual_Funds.py"),
            ("🥇", "Gold",          "pages/5_Gold.py"),
            ("🏛️", "Debt",          "pages/6_Debt.py"),
            ("🎖️", "NPS",           "pages/7_NPS.py"),
            ("💵", "Income",        "pages/8_Income.py"),
            ("💸", "Expenses",      "pages/9_Expenses.py"),
            ("🎯", "Goals",         "pages/10_Goals.py"),
            ("📆", "Cash Flow",     "pages/11_Cash_Flow.py"),
            ("🧾", "Tax Summary",   "pages/12_Tax_Summary.py"),
            ("💰", "Dividend Ledger","pages/13_Dividend_Ledger.py"),
        ]

        st.markdown(f"""<style>
        [data-testid="stSidebar"] .nav-btn > button {{
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 8px !important;
            padding: 5px 10px !important;
            width: 100% !important;
            text-align: left !important;
            color: {T['text']} !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            margin-bottom: 1px !important;
            justify-content: flex-start !important;
        }}
        [data-testid="stSidebar"] .nav-btn > button:hover {{
            background: {T['card2']} !important;
            border-color: {T['border']} !important;
        }}
        [data-testid="stSidebar"] .nav-btn-active > button {{
            background: {T['card']} !important;
            border: 1px solid {T['border']} !important;
            color: {T['accent']} !important;
            font-weight: 700 !important;
        }}
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
        st.markdown(f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{T["muted"]};margin-bottom:6px">💰 This Month\'s Flow</div>', unsafe_allow_html=True)

        _d = get_data()
        inc_df = _d.get("income",  pd.DataFrame())
        exp_df = _d.get("expenses", pd.DataFrame())

        today     = pd.Timestamp.today()
        cur_month = today.to_period("M")
        prev_mon  = (today - pd.DateOffset(months=1)).to_period("M")

        def _msum(df, period):
            if df is None or df.empty: return 0.0
            d = df.copy()
            d["Date"]   = pd.to_datetime(d.get("Date", pd.Series()), errors="coerce")
            d["Amount"] = pd.to_numeric(d.get("Amount", pd.Series()), errors="coerce").fillna(0)
            d["M"]      = d["Date"].dt.to_period("M")
            return float(d[d["M"]==period]["Amount"].sum())

        inc_c = _msum(inc_df, cur_month)
        exp_c = _msum(exp_df, cur_month)
        inc_p = _msum(inc_df, prev_mon)
        exp_p = _msum(exp_df, prev_mon)
        net   = inc_c - exp_c
        nc    = T["green"] if net>=0 else T["red"]
        sr    = (net/inc_c*100) if inc_c>0 else 0
        ic    = ((inc_c-inc_p)/inc_p*100) if inc_p>0 else 0
        ec    = ((exp_c-exp_p)/exp_p*100) if exp_p>0 else 0
        ic_c  = T["green"] if ic>=0 else T["red"]
        ec_c  = T["red"]   if ec>=0 else T["green"]

        # Pre-compute trend badges to avoid nested f-string span issues
        inc_badge = (f'<span style="font-size:9px;color:{ic_c};background:transparent">'
                     f' {"▲" if ic>=0 else "▼"}{abs(ic):.0f}%</span>') if inc_p > 0 else ""
        exp_badge = (f'<span style="font-size:9px;color:{ec_c};background:transparent">'
                     f' {"▲" if ec>=0 else "▼"}{abs(ec):.0f}%</span>') if exp_p > 0 else ""

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

        # ── Price Refresh ──
        st.markdown(f'<hr style="border-color:{T["border"]};margin:8px 0">', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{T["muted"]};margin-bottom:6px">🔄 Live Prices</div>',
                    unsafe_allow_html=True)

        _data    = get_data()
        _inv     = _data.get("inv", pd.DataFrame())
        _is_demo = _data.get("demo", True)

        if st.button("🔄 Refresh Prices", use_container_width=True, key="sb_refresh_prices"):
            if _is_demo:
                st.toast("Demo mode — connect credentials.json for live prices", icon="⚠️")
            else:
                try:
                    try:
                        from utils.price_updater import fetch_all_prices, update_prices_sheet
                    except ImportError:
                        st.toast("yfinance not installed - update prices manually", icon="⚠️"); raise
                    asset_list = _inv["Asset_Name"].dropna().unique().tolist()
                    inv_cols   = ["Asset_Name","Asset_Class","Category"] + \
                                 (["Ticker"] if "Ticker" in _inv.columns else [])
                    inv_json   = _inv[inv_cols].drop_duplicates("Asset_Name").to_json(orient="records")
                    with st.spinner("Fetching..."):
                        result   = fetch_all_prices(asset_list, inv_json)
                        ok, fail = update_prices_sheet(get_sheet(), result["prices"])
                        if ok > 0:
                            st.session_state["last_price_sync"] = result["fetched_at"]
                            st.toast(f"✅ {ok} prices updated", icon="✅")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.toast("⚠️ No prices updated", icon="⚠️")
                except ImportError:
                    st.toast("Install yfinance: pip install yfinance", icon="⚠️")
                except Exception as e:
                    st.toast(f"Error: {str(e)[:60]}", icon="❌")

        last_sync = st.session_state.get("last_price_sync", None)
        st.markdown(f"""
        <div style='font-size:10px;color:{T["muted"]};text-align:center;margin-top:4px'>
          {'Last synced: ' + last_sync if last_sync else 'Prices from Current_Prices sheet'}
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════
def _find_credentials():
    """Find credentials.json searching up from current file location."""
    import os
    # Try paths relative to this file (utils/shared.py)
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "..", "credentials.json"),     # Finance-Track/credentials.json
        os.path.join(base, "credentials.json"),           # utils/credentials.json
        "credentials.json",                               # cwd
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
        return dict(
            inv=inv, prices=prices,
            income=safe("Income_Ledger"),
            expenses=safe("Expenditure_Ledger"),
            nps=safe("NPS_Ledger"),
            dividend=safe("Dividend_Ledger"),
            goals=safe("Goals"),
            demo=False
        )
    except FileNotFoundError:
        return dict(inv=pd.DataFrame(), prices=pd.DataFrame(),
                    income=pd.DataFrame(), expenses=pd.DataFrame(),
                    nps=pd.DataFrame(), dividend=pd.DataFrame(),
                    goals=pd.DataFrame(), demo=True)
    except Exception as e:
        return dict(inv=pd.DataFrame(), prices=pd.DataFrame(),
                    income=pd.DataFrame(), expenses=pd.DataFrame(),
                    nps=pd.DataFrame(), dividend=pd.DataFrame(),
                    goals=pd.DataFrame(), demo=True)


def save_row(sheet_name, row):
    try:
        get_sheet().worksheet(sheet_name).append_row(row)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(str(e))
        return False


# ══════════════════════════════════════════════════════════════
#  DEMO DATA  (spans FY 2024-25 and FY 2025-26)
# ══════════════════════════════════════════════════════════════
def get_demo_data():
    inv = pd.DataFrame([
        dict(Person="Gokul", Asset_Class="Equity",      Category="Direct Equity", Asset_Name="Reliance Industries",    Tag="Large Cap", Transaction_Type="BUY", Quantity=50,   Price=2400,   Date="2023-01-15",Notes=""),
        dict(Person="Gokul", Asset_Class="Equity",      Category="Direct Equity", Asset_Name="HDFC Bank",              Tag="Large Cap", Transaction_Type="BUY", Quantity=30,   Price=1600,   Date="2023-03-10",Notes=""),
        dict(Person="Gokul", Asset_Class="Equity",      Category="ETF",           Asset_Name="Nifty BeES",             Tag="Index",     Transaction_Type="BUY", Quantity=200,  Price=195,    Date="2023-06-01",Notes=""),
        dict(Person="Yamuna",Asset_Class="Equity",      Category="Direct Equity", Asset_Name="Infosys",                Tag="IT",        Transaction_Type="BUY", Quantity=40,   Price=1450,   Date="2023-02-20",Notes=""),
        dict(Person="Yamuna",Asset_Class="Equity",      Category="Direct Equity", Asset_Name="TCS",                    Tag="IT",        Transaction_Type="BUY", Quantity=20,   Price=3400,   Date="2023-05-15",Notes=""),
        dict(Person="Gokul", Asset_Class="Mutual Fund", Category="Equity MF",     Asset_Name="Mirae Asset Large Cap",  Tag="Large Cap", Transaction_Type="BUY", Quantity=500,  Price=85,     Date="2022-08-01",Notes=""),
        dict(Person="Gokul", Asset_Class="Mutual Fund", Category="Equity MF",     Asset_Name="Parag Parikh Flexi Cap", Tag="Flexi",     Transaction_Type="BUY", Quantity=300,  Price=55,     Date="2022-11-01",Notes=""),
        dict(Person="Yamuna",Asset_Class="Mutual Fund", Category="Debt MF",       Asset_Name="HDFC Short Term Debt",   Tag="Debt",      Transaction_Type="BUY", Quantity=1000, Price=42,     Date="2023-01-05",Notes=""),
        dict(Person="Gokul", Asset_Class="Gold",        Category="Gold ETF",      Asset_Name="Nippon Gold ETF",        Tag="Commodity", Transaction_Type="BUY", Quantity=10,   Price=4800,   Date="2022-05-10",Notes=""),
        dict(Person="Yamuna",Asset_Class="Gold",        Category="Gold Scheme",   Asset_Name="SGB 2023",               Tag="Sovereign", Transaction_Type="BUY", Quantity=5,    Price=5600,   Date="2023-03-30",Notes=""),
        dict(Person="Gokul", Asset_Class="Debt",        Category="FD",            Asset_Name="SBI FD 7.2%",            Tag="Fixed",     Transaction_Type="BUY", Quantity=1,    Price=200000, Date="2023-01-01",Notes="2yr lock"),
        dict(Person="Yamuna",Asset_Class="Debt",        Category="RD",            Asset_Name="Post Office RD",         Tag="Govt",      Transaction_Type="BUY", Quantity=12,   Price=5000,   Date="2023-04-01",Notes="Monthly"),
        dict(Person="Gokul", Asset_Class="NPS",         Category="Equity (E)",    Asset_Name="NPS Equity - Gokul",     Tag="Retirement",Transaction_Type="BUY", Quantity=1,    Price=85000,  Date="2022-04-01",Notes=""),
        dict(Person="Yamuna",Asset_Class="NPS",         Category="Government (G)",Asset_Name="NPS Govt - Yamuna",      Tag="Retirement",Transaction_Type="BUY", Quantity=1,    Price=60000,  Date="2022-04-01",Notes=""),
    ])
    prices = pd.DataFrame([
        dict(Asset_Name="Reliance Industries",    Current_Price=2890),
        dict(Asset_Name="HDFC Bank",              Current_Price=1720),
        dict(Asset_Name="Nifty BeES",             Current_Price=248),
        dict(Asset_Name="Infosys",                Current_Price=1680),
        dict(Asset_Name="TCS",                    Current_Price=3950),
        dict(Asset_Name="Mirae Asset Large Cap",  Current_Price=112),
        dict(Asset_Name="Parag Parikh Flexi Cap", Current_Price=78),
        dict(Asset_Name="HDFC Short Term Debt",   Current_Price=45),
        dict(Asset_Name="Nippon Gold ETF",        Current_Price=6100),
        dict(Asset_Name="SGB 2023",               Current_Price=6400),
        dict(Asset_Name="SBI FD 7.2%",            Current_Price=214400),
        dict(Asset_Name="Post Office RD",         Current_Price=5000),
        dict(Asset_Name="NPS Equity - Gokul",     Current_Price=105000),
        dict(Asset_Name="NPS Govt - Yamuna",      Current_Price=72000),
    ])
    # Income data across FY 2024-25 and FY 2025-26
    income_rows = [
        # FY 2024-25 (Apr 2024 - Mar 2025)
        ("2024-04-01","Gokul","Salary",85000,"April salary"),
        ("2024-04-05","Yamuna","Salary",65000,"April salary"),
        ("2024-05-01","Gokul","Salary",85000,"May salary"),
        ("2024-05-05","Yamuna","Salary",65000,"May salary"),
        ("2024-05-15","Yamuna","Rental Income",15000,"Flat rent"),
        ("2024-06-01","Gokul","Salary",85000,"June salary"),
        ("2024-06-05","Yamuna","Salary",65000,"June salary"),
        ("2024-06-20","Gokul","Dividend",3200,"HDFC dividend"),
        ("2024-07-01","Gokul","Salary",85000,"July salary"),
        ("2024-07-05","Yamuna","Salary",65000,"July salary"),
        ("2024-07-15","Yamuna","Rental Income",15000,"Flat rent"),
        ("2024-08-01","Gokul","Salary",85000,"August salary"),
        ("2024-08-05","Yamuna","Salary",65000,"August salary"),
        ("2024-08-25","Gokul","Bonus",40000,"Mid-year bonus"),
        ("2024-09-01","Gokul","Salary",85000,"September salary"),
        ("2024-09-05","Yamuna","Salary",65000,"September salary"),
        ("2024-09-15","Yamuna","Rental Income",15000,"Flat rent"),
        ("2024-10-01","Gokul","Salary",85000,"October salary"),
        ("2024-10-05","Yamuna","Salary",65000,"October salary"),
        ("2024-10-12","Gokul","Freelance / Consulting",22000,"Project X"),
        ("2024-10-20","Gokul","Dividend",3200,"HDFC dividend"),
        ("2024-11-01","Gokul","Salary",85000,"November salary"),
        ("2024-11-05","Yamuna","Salary",65000,"November salary"),
        ("2024-11-18","Yamuna","Rental Income",15000,"Flat rent"),
        ("2024-11-25","Gokul","Bonus",40000,"Q2 bonus"),
        ("2024-12-01","Gokul","Salary",85000,"December salary"),
        ("2024-12-05","Yamuna","Salary",65000,"December salary"),
        ("2024-12-15","Gokul","Interest Income",8500,"FD interest"),
        ("2024-12-20","Yamuna","Rental Income",15000,"Flat rent"),
        ("2025-01-01","Gokul","Salary",92000,"Hike!"),
        ("2025-01-05","Yamuna","Salary",70000,"January salary"),
        ("2025-01-14","Gokul","Freelance / Consulting",18000,"Short project"),
        ("2025-02-01","Gokul","Salary",92000,"February salary"),
        ("2025-02-05","Yamuna","Salary",70000,"February salary"),
        ("2025-02-10","Yamuna","Rental Income",15000,"Flat rent"),
        ("2025-02-20","Gokul","Dividend",4100,"Reliance dividend"),
        ("2025-03-01","Gokul","Salary",92000,"March salary"),
        ("2025-03-05","Yamuna","Salary",70000,"March salary"),
        ("2025-03-12","Gokul","Capital Gains",28000,"MF redemption"),
        ("2025-03-18","Yamuna","Rental Income",15000,"Flat rent"),
        # FY 2025-26 (Apr 2025 - Mar 2026)
        ("2025-04-01","Gokul","Salary",93000,"Apr 2025"),
        ("2025-04-05","Yamuna","Salary",71000,"Apr 2025"),
        ("2025-04-15","Yamuna","Rental Income",15500,"Flat rent"),
        ("2025-05-01","Gokul","Salary",93000,"May 2025"),
        ("2025-05-05","Yamuna","Salary",71000,"May 2025"),
        ("2025-06-01","Gokul","Salary",93000,"Jun 2025"),
        ("2025-06-05","Yamuna","Salary",71000,"Jun 2025"),
        ("2025-06-20","Gokul","Dividend",3800,"Dividend"),
        ("2025-07-01","Gokul","Salary",93000,"Jul 2025"),
        ("2025-07-05","Yamuna","Salary",71000,"Jul 2025"),
        ("2025-07-15","Yamuna","Rental Income",15500,"Flat rent"),
        ("2025-08-01","Gokul","Salary",93000,"Aug 2025"),
        ("2025-08-05","Yamuna","Salary",71000,"Aug 2025"),
        ("2025-08-20","Gokul","Freelance / Consulting",30000,"New project"),
        ("2025-09-01","Gokul","Salary",95000,"Sep 2025 hike"),
        ("2025-09-05","Yamuna","Salary",72000,"Sep 2025"),
        ("2025-10-01","Gokul","Salary",95000,"Oct 2025"),
        ("2025-10-05","Yamuna","Salary",72000,"Oct 2025"),
        ("2025-10-15","Yamuna","Rental Income",16000,"Flat rent"),
        ("2025-11-01","Gokul","Salary",95000,"Nov 2025"),
        ("2025-11-05","Yamuna","Salary",72000,"Nov 2025"),
        ("2025-11-25","Gokul","Bonus",50000,"Year-end bonus"),
        ("2025-12-01","Gokul","Salary",95000,"Dec 2025"),
        ("2025-12-05","Yamuna","Salary",72000,"Dec 2025"),
        ("2025-12-15","Gokul","Interest Income",9000,"FD interest"),
        ("2026-01-01","Gokul","Salary",98000,"Jan 2026 hike"),
        ("2026-01-05","Yamuna","Salary",75000,"Jan 2026"),
        ("2026-01-15","Yamuna","Rental Income",16000,"Flat rent"),
        ("2026-02-01","Gokul","Salary",98000,"Feb 2026"),
        ("2026-02-05","Yamuna","Salary",75000,"Feb 2026"),
        ("2026-02-14","Gokul","Freelance / Consulting",35000,"Big project"),
        ("2026-03-01","Gokul","Salary",98000,"Mar 2026"),
        ("2026-03-05","Yamuna","Salary",75000,"Mar 2026"),
        ("2026-03-10","Yamuna","Rental Income",16000,"Flat rent"),
        ("2026-03-15","Gokul","Capital Gains",45000,"MF partial exit"),
    ]
    income = pd.DataFrame(income_rows, columns=["Date","Person","Category","Amount","Note"])

    expense_rows = [
        # FY 2024-25
        ("2024-04-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2024-04-08","Family","Groceries",6500,"Monthly"),
        ("2024-04-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2024-05-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2024-05-08","Family","Groceries",7000,"Monthly"),
        ("2024-05-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2024-06-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2024-06-08","Family","Groceries",6800,"Monthly"),
        ("2024-06-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2024-06-20","Family","Utilities",3200,"EB+Water"),
        ("2024-07-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2024-07-08","Family","Groceries",7200,"July groceries"),
        ("2024-07-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2024-07-22","Yamuna","Healthcare",2500,"Doctor"),
        ("2024-08-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2024-08-08","Family","Groceries",6900,"Monthly"),
        ("2024-08-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2024-09-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2024-09-08","Family","Groceries",6700,"Monthly"),
        ("2024-09-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2024-09-25","Yamuna","Education",15000,"Tuition"),
        ("2024-10-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2024-10-08","Family","Groceries",6500,"BigBasket"),
        ("2024-10-10","Gokul","Transport",3200,"Metro+Uber"),
        ("2024-10-14","Yamuna","Food & Dining",4800,"Restaurants"),
        ("2024-10-18","Family","Utilities",3100,"EB+Water"),
        ("2024-10-28","Family","Children",8500,"School fees"),
        ("2024-11-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2024-11-07","Family","Groceries",7200,"Shopping"),
        ("2024-11-12","Yamuna","Shopping",9500,"Diwali clothes"),
        ("2024-11-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2024-12-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2024-12-08","Family","Groceries",8100,"December"),
        ("2024-12-15","Family","Travel",22000,"Ooty trip"),
        ("2024-12-24","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-01-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2025-01-09","Family","Groceries",6800,"Pongal"),
        ("2025-01-18","Yamuna","Education",15000,"Tuition fees"),
        ("2025-01-22","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-02-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2025-02-07","Family","Groceries",6200,"Monthly"),
        ("2025-02-22","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-03-03","Gokul","Housing / Rent",18000,"Rent"),
        ("2025-03-08","Family","Groceries",7400,"Monthly"),
        ("2025-03-20","Gokul","EMI / Loan",12000,"Car EMI"),
        # FY 2025-26
        ("2025-04-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2025-04-08","Family","Groceries",7000,"Apr groceries"),
        ("2025-04-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-05-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2025-05-08","Family","Groceries",7200,"May groceries"),
        ("2025-05-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-06-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2025-06-08","Family","Groceries",6800,"Jun groceries"),
        ("2025-06-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-07-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2025-07-08","Family","Groceries",7500,"Jul groceries"),
        ("2025-07-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-08-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2025-08-08","Family","Groceries",7100,"Aug groceries"),
        ("2025-08-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-09-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2025-09-08","Family","Groceries",6900,"Sep groceries"),
        ("2025-09-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-10-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2025-10-08","Family","Groceries",7000,"Oct groceries"),
        ("2025-10-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-11-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2025-11-10","Family","Groceries",7500,"Nov groceries"),
        ("2025-11-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2025-12-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2025-12-15","Family","Travel",18000,"Year-end trip"),
        ("2025-12-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2026-01-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2026-01-08","Family","Groceries",7200,"Jan groceries"),
        ("2026-01-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2026-02-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2026-02-08","Family","Groceries",6800,"Feb groceries"),
        ("2026-02-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2026-03-03","Gokul","Housing / Rent",19000,"Rent"),
        ("2026-03-08","Family","Groceries",7600,"Mar groceries"),
        ("2026-03-15","Gokul","EMI / Loan",12000,"Car EMI"),
        ("2026-03-20","Yamuna","Shopping",8500,"Year-end shopping"),
    ]
    expenses = pd.DataFrame(expense_rows, columns=["Date","Person","Category","Amount","Note"])

    goals = pd.DataFrame([
        dict(Goal="Emergency Fund",    Target=600000,   Current=420000,  Deadline="Dec 2025"),
        dict(Goal="Home Down Payment", Target=2000000,  Current=680000,  Deadline="Dec 2027"),
        dict(Goal="Child Education",   Target=5000000,  Current=320000,  Deadline="Jan 2035"),
        dict(Goal="Retirement Corpus", Target=30000000, Current=1890000, Deadline="Apr 2045"),
        dict(Goal="Europe Vacation",   Target=300000,   Current=180000,  Deadline="Jun 2026"),
        dict(Goal="Car Upgrade",       Target=800000,   Current=240000,  Deadline="Mar 2026"),
    ])
    return dict(inv=inv, prices=prices, income=income, expenses=expenses,
                nps=pd.DataFrame(), dividend=pd.DataFrame(),
                goals=goals, demo=True)


def build_investment_df(inv, prices, person="Family"):
    df = inv.copy()
    if person != "Family":
        df = df[df["Person"] == person]
    if df.empty:
        return df
    # Merge with prices — deduplicate first to prevent row multiplication
    if not prices.empty and "Asset_Name" in prices.columns and "Current_Price" in prices.columns:
        prices_clean = prices[["Asset_Name","Current_Price"]].copy()
        prices_clean["Current_Price"] = pd.to_numeric(prices_clean["Current_Price"], errors="coerce").fillna(0)
        # Keep only the last (most recent) price per asset — prevents duplicate rows on merge
        prices_clean = prices_clean.drop_duplicates(subset="Asset_Name", keep="last")
        df = df.merge(prices_clean, on="Asset_Name", how="left")
    else:
        df["Current_Price"] = 0
    for c in ["Quantity", "Price", "Current_Price"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["Invested"]      = df["Quantity"] * df["Price"]
    df["Current_Value"] = df["Quantity"] * df["Current_Price"]
    df["Gain"]          = df["Current_Value"] - df["Invested"]
    df["Date"]          = pd.to_datetime(df["Date"], errors="coerce")
    return df


def get_data():
    data = load_all_data()
    # Use demo ONLY when credentials.json is missing
    # If sheet is connected but empty, keep live mode so saves still work
    if data["demo"]:
        return get_demo_data()
    return data