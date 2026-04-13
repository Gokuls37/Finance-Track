import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.shared import (
    inject_css, render_sidebar, get_data, get_theme, sh, fmt,
    plot_layout, info_box, PIE_COLORS, get_fy_list, fy_date_range, current_fy, MONTHS_ORDER
)

st.set_page_config(page_title="Cash Flow – Finance Track", page_icon="📆",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
T = get_theme()
data = get_data()
render_sidebar("Cash Flow")

st.title("📆 Monthly Cash Flow")

inc_raw = data["income"].copy()   if not data["income"].empty   else pd.DataFrame()
exp_raw = data["expenses"].copy() if not data["expenses"].empty else pd.DataFrame()

if inc_raw.empty and exp_raw.empty:
    info_box("No income or expense data found.")
    st.stop()

# Prep
for df_x in [inc_raw, exp_raw]:
    if not df_x.empty:
        df_x["Date"]   = pd.to_datetime(df_x["Date"], errors="coerce")
        df_x["Amount"] = pd.to_numeric(df_x["Amount"], errors="coerce").fillna(0)
        df_x["MonthN"] = df_x["Date"].dt.to_period("M")
        df_x["Year"]   = df_x["Date"].dt.year

# ── FY filter ──
all_years = set()
for df_x in [inc_raw, exp_raw]:
    if not df_x.empty:
        all_years.update(df_x["Year"].dropna().astype(int).tolist())

fy_opts = ["All Time"] + get_fy_list(list(all_years))
cfy     = current_fy()
def_idx = fy_opts.index(cfy) if cfy in fy_opts else 0

col_fy, col_per, col_view = st.columns([1,1,1])
sel_fy  = col_fy.selectbox("Financial Year", fy_opts, index=def_idx)
sel_per = col_per.selectbox("Person", ["Family","Gokul","Yamuna","Kavitha"])

def filter_fy(df_x):
    if df_x.empty: return df_x
    d = df_x.copy()
    if sel_fy != "All Time":
        s, e = fy_date_range(sel_fy)
        d = d[d["Date"].between(s, e)]
    if sel_per != "Family":
        d = d[d["Person"]==sel_per]
    return d

inc = filter_fy(inc_raw)
exp = filter_fy(exp_raw)

# ── Monthly aggregation ──
def monthly_agg(df_x):
    if df_x.empty: return pd.DataFrame(columns=["MonthN","MonthStr","Amount"])
    g = df_x.groupby("MonthN")["Amount"].sum().reset_index()
    g["MonthStr"] = g["MonthN"].astype(str)
    return g.sort_values("MonthN")

m_inc = monthly_agg(inc)
m_exp = monthly_agg(exp)
all_months = sorted(set(m_inc["MonthN"].tolist() + m_exp["MonthN"].tolist()))
month_strs  = [str(m) for m in all_months]

# Align both series to same months
def align(df_m):
    d = dict(zip(df_m["MonthN"], df_m["Amount"]))
    return [d.get(m, 0) for m in all_months]

inc_vals = align(m_inc)
exp_vals = align(m_exp)
net_vals = [i-e for i,e in zip(inc_vals, exp_vals)]

# ── KPIs ──
tot_inc = sum(inc_vals)
tot_exp = sum(exp_vals)
tot_net = tot_inc - tot_exp
sr      = (tot_net/tot_inc*100) if tot_inc>0 else 0
avg_inc = tot_inc/len(month_strs) if month_strs else 0
avg_exp = tot_exp/len(month_strs) if month_strs else 0

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Total Income",  fmt(tot_inc))
k2.metric("Total Expense", fmt(tot_exp))
k3.metric("Net Surplus",   fmt(tot_net), f"{sr:.1f}% savings")
k4.metric("Avg Monthly Income",  fmt(avg_inc))
k5.metric("Avg Monthly Expense", fmt(avg_exp))

st.markdown("---")

# ── Stacked bar chart ──
sh(f"Monthly Income vs Expense — {sel_fy}")
fig_cf = go.Figure()
fig_cf.add_trace(go.Bar(x=month_strs, y=inc_vals, name="Income",
    marker_color=T["green"], marker_line_width=0,
    hovertemplate="<b>Income</b><br>%{x}<br>Rs.%{y:,.0f}<extra></extra>"))
fig_cf.add_trace(go.Bar(x=month_strs, y=[-e for e in exp_vals], name="Expense",
    marker_color=T["red"], marker_line_width=0,
    hovertemplate="<b>Expense</b><br>%{x}<br>Rs.%{y:,.0f}<extra></extra>"))
fig_cf.add_trace(go.Scatter(x=month_strs, y=net_vals, name="Net",
    mode="lines+markers", line=dict(color=T["accent"],width=2.5),
    marker=dict(size=7,color=T["accent"]),
    hovertemplate="<b>Net</b><br>%{x}<br>Rs.%{y:,.0f}<extra></extra>"))
pl = plot_layout()
pl.pop("yaxis", None)   # remove yaxis from plot_layout to avoid conflict
fig_cf.update_layout(**pl, height=340, barmode="relative",
    yaxis=dict(gridcolor=T["pgrid"], zeroline=True, zerolinecolor=T["border"],
               zerolinewidth=2, color=T["ptick"], tickfont=dict(size=11)))
st.plotly_chart(fig_cf, use_container_width=True)

st.markdown("---")
ca, cb = st.columns(2)

with ca:
    sh("Income Breakdown by Category")
    if not inc.empty:
        ic_cat = inc.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount",ascending=False)
        fig_ic = go.Figure(go.Pie(
            labels=ic_cat["Category"], values=ic_cat["Amount"], hole=0.52,
            marker=dict(colors=PIE_COLORS,line=dict(color=T["bg"],width=2)),
            textinfo="percent+label", textfont=dict(size=10)))
        fig_ic.update_layout(**plot_layout(), height=300)
        st.plotly_chart(fig_ic, use_container_width=True)

        rows = ""
        for _,r in ic_cat.iterrows():
            sp = r["Amount"]/tot_inc*100 if tot_inc>0 else 0
            rows += f'<tr><td class="bold">{r["Category"]}</td><td class="mono" style="color:{T["green"]}">{fmt(r["Amount"])}</td><td class="mono" style="color:{T["muted"]}">{sp:.1f}%</td></tr>'
        st.markdown(f'<div class="ft-wrap"><table class="ft"><thead><tr><th>Category</th><th>Amount</th><th>Share</th></tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)

with cb:
    sh("Expense Breakdown by Category")
    if not exp.empty:
        ec_cat = exp.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount",ascending=False)
        fig_ec = go.Figure(go.Pie(
            labels=ec_cat["Category"], values=ec_cat["Amount"], hole=0.52,
            marker=dict(colors=PIE_COLORS,line=dict(color=T["bg"],width=2)),
            textinfo="percent+label", textfont=dict(size=10)))
        fig_ec.update_layout(**plot_layout(), height=300)
        st.plotly_chart(fig_ec, use_container_width=True)

        rows = ""
        for _,r in ec_cat.iterrows():
            sp = r["Amount"]/tot_exp*100 if tot_exp>0 else 0
            rows += f'<tr><td class="bold">{r["Category"]}</td><td class="mono" style="color:{T["red"]}">{fmt(r["Amount"])}</td><td class="mono" style="color:{T["muted"]}">{sp:.1f}%</td></tr>'
        st.markdown(f'<div class="ft-wrap"><table class="ft"><thead><tr><th>Category</th><th>Amount</th><th>Share</th></tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)

st.markdown("---")
sh("Month-by-Month Summary Table")
rows = ""
for i, ms in enumerate(month_strs):
    iv = inc_vals[i]; ev = exp_vals[i]; nv = net_vals[i]
    nc = T["green"] if nv>=0 else T["red"]
    sr_m = (nv/iv*100) if iv>0 else 0
    rows += f"""<tr>
      <td class="bold">{ms}</td>
      <td class="mono" style="color:{T['green']}">{fmt(iv)}</td>
      <td class="mono" style="color:{T['red']}">{fmt(ev)}</td>
      <td class="mono" style="color:{nc};font-weight:700">{"+" if nv>=0 else ""}{fmt(nv)}</td>
      <td><span class="badge" style="background:{nc}22;color:{nc}">{sr_m:.1f}%</span></td>
    </tr>"""
st.markdown(f"""
<div class="ft-wrap"><table class="ft">
  <thead><tr><th>Month</th><th>Income</th><th>Expense</th><th>Net Flow</th><th>Savings %</th></tr></thead>
  <tbody>{rows}</tbody>
</table></div>""", unsafe_allow_html=True)
