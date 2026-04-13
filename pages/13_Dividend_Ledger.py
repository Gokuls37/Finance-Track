import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.shared import (
    inject_css, render_sidebar, get_data, get_theme, sh, fmt,
    plot_layout, info_box, PIE_COLORS, get_fy_list, fy_date_range, current_fy
)

st.set_page_config(page_title="Dividend Ledger – Finance Track", page_icon="💰",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
T = get_theme()
data = get_data()
render_sidebar("Dividend Ledger")

st.title("💰 Dividend & Interest Ledger")
st.caption("Track all dividend, interest, and passive income receipts")

# ── Load dividend data ──
div_raw = data.get("dividend", pd.DataFrame())

if div_raw is None or div_raw.empty:
    info_box("No dividend records yet. Use Add Investment → Dividend Income tab to log entries.")
    st.stop()

# ── Prep ──
div = div_raw.copy()
div["Date"]       = pd.to_datetime(div["Date"], errors="coerce")
div["Amount"]     = pd.to_numeric(div.get("Amount", div.get("Gross_Amount", 0)), errors="coerce").fillna(0)
div["Net_Amount"] = pd.to_numeric(div.get("Net_Amount", div.get("Amount", 0)), errors="coerce").fillna(0)
div["Tax_Deducted"] = pd.to_numeric(div.get("Tax_Deducted", div.get("TDS", 0)), errors="coerce").fillna(0)
div["MonthN"]     = div["Date"].dt.to_period("M")
div["MonthStr"]   = div["Date"].dt.strftime("%b %Y")

# ── FY Filter ──
years = div["Date"].dt.year.dropna().unique().astype(int)
fy_opts = ["All Time"] + get_fy_list(years)
cfy     = current_fy()
c_fy, c_per = st.columns([1,1])
sel_fy  = c_fy.selectbox("Financial Year", fy_opts,
                           index=fy_opts.index(cfy) if cfy in fy_opts else 0)
persons = ["All"] + sorted(div["Person"].dropna().unique().tolist()) if "Person" in div.columns else ["All"]
sel_per = c_per.selectbox("Person", persons)

filt = div.copy()
if sel_fy != "All Time":
    s, e = fy_date_range(sel_fy)
    filt = filt[(filt["Date"] >= s) & (filt["Date"] <= e)]
if sel_per != "All" and "Person" in filt.columns:
    filt = filt[filt["Person"] == sel_per]

if filt.empty:
    info_box("No records for selected filters.")
    st.stop()

# ── KPIs ──
total_gross = filt["Amount"].sum()
total_tds   = filt["Tax_Deducted"].sum()
total_net   = filt["Net_Amount"].sum()
num_txn     = len(filt)

k1,k2,k3,k4 = st.columns(4)
k1.metric("Gross Dividend",   fmt(total_gross))
k2.metric("TDS Deducted",     fmt(total_tds))
k3.metric("Net Received",     fmt(total_net))
k4.metric("Transactions",     str(num_txn))

st.markdown("---")

ca, cb = st.columns(2)

with ca:
    sh("Monthly Dividend Income")
    monthly = (filt.groupby("MonthStr")["Net_Amount"].sum()
               .reset_index().sort_values("MonthStr"))
    if not monthly.empty:
        fig_m = go.Figure(go.Bar(
            x=monthly["MonthStr"], y=monthly["Net_Amount"],
            marker_color=T["green"], marker_line_width=0,
            hovertemplate="%{x}<br>Net: Rs.%{y:,.0f}<extra></extra>"
        ))
        fig_m.update_layout(**plot_layout(), height=260)
        st.plotly_chart(fig_m, use_container_width=True)

with cb:
    sh("By Asset Class")
    if "Asset_Class" in filt.columns:
        by_cls = filt.groupby("Asset_Class")["Net_Amount"].sum().reset_index()
        if not by_cls.empty:
            fig_p = go.Figure(go.Pie(
                labels=by_cls["Asset_Class"], values=by_cls["Net_Amount"],
                hole=0.55, marker=dict(colors=PIE_COLORS, line=dict(color=T["bg"], width=2)),
                textinfo="percent+label", textfont=dict(size=11)
            ))
            fig_p.update_layout(**plot_layout(), height=260)
            st.plotly_chart(fig_p, use_container_width=True)

st.markdown("---")

# ── By Asset ──
sh("Dividend by Asset")
by_asset = (filt.groupby("Asset_Name")
            .agg(Gross=("Amount","sum"), TDS=("Tax_Deducted","sum"), Net=("Net_Amount","sum"), Count=("Amount","count"))
            .reset_index().sort_values("Net", ascending=False))

rows = ""
for _, r in by_asset.iterrows():
    rows += f"""<tr>
      <td class="bold">{r["Asset_Name"]}</td>
      <td class="mono">{fmt(r["Gross"])}</td>
      <td class="mono" style="color:{T['red']}">{fmt(r["TDS"])}</td>
      <td class="mono" style="color:{T['green']};font-weight:700">{fmt(r["Net"])}</td>
      <td style="color:{T['muted']}">{int(r["Count"])}</td>
    </tr>"""

st.markdown(f"""
<div class="ft-wrap"><table class="ft">
  <thead><tr><th>Asset</th><th>Gross</th><th>TDS</th><th>Net Received</th><th>Entries</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>""", unsafe_allow_html=True)

st.markdown("---")
sh("All Dividend Records")

# ── Full records table ──
rec_rows = ""
for _, r in filt.sort_values("Date", ascending=False).iterrows():
    date_str = r["Date"].strftime("%d %b %Y") if pd.notna(r["Date"]) else "—"
    dtype    = r.get("Dividend_Type", r.get("Type", "—"))
    person   = r.get("Person", "—")
    pc       = T["accent"] if person == "Gokul" else (T["accent2"] if person == "Yamuna" else T["muted"])
    rec_rows += f"""<tr>
      <td style="color:{T['muted']};font-size:12px">{date_str}</td>
      <td class="bold">{r.get("Asset_Name","—")}</td>
      <td><span class="badge" style="background:{pc}22;color:{pc}">{person}</span></td>
      <td style="color:{T['muted']};font-size:12px">{dtype}</td>
      <td class="mono">{fmt(r["Amount"])}</td>
      <td class="mono" style="color:{T['red']}">{fmt(r["Tax_Deducted"])}</td>
      <td class="mono" style="color:{T['green']};font-weight:700">{fmt(r["Net_Amount"])}</td>
      <td style="color:{T['muted']};font-size:12px">{r.get("Note","")}</td>
    </tr>"""

st.markdown(f"""
<div class="ft-wrap"><table class="ft">
  <thead><tr><th>Date</th><th>Asset</th><th>Person</th><th>Type</th>
  <th>Gross</th><th>TDS</th><th>Net</th><th>Note</th></tr></thead>
  <tbody>{rec_rows}</tbody>
</table></div>""", unsafe_allow_html=True)
