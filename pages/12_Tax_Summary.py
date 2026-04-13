import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.shared import (
    inject_css, render_sidebar, get_data, get_theme, sh, fmt, pct,
    build_investment_df, plot_layout, info_box,
    compute_tax_summary, get_fy_list, fy_date_range, current_fy, LTCG_EXEMPTION
)

st.set_page_config(page_title="Tax Summary – Finance Track", page_icon="🧾",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
T = get_theme()
data = get_data()
render_sidebar("Tax Summary")

st.title("🧾 Tax Summary")
st.caption("Based on Indian tax rules (post-July 2024 budget). Estimates only — consult a CA for filing.")

person = st.session_state.get("sb_person","Family")

inv_raw    = data["inv"]
prices_raw = data["prices"]
df_inv     = build_investment_df(inv_raw, prices_raw, person)

if df_inv.empty:
    info_box("No investment data found.")
    st.stop()

# ── FY selector ──
years = df_inv["Date"].dt.year.dropna().unique().astype(int).tolist()
fy_opts = get_fy_list(years)
cfy     = current_fy()
def_idx = fy_opts.index(cfy) if cfy in fy_opts else 0
sel_fy  = st.selectbox("Select Financial Year", fy_opts, index=def_idx)

tax = compute_tax_summary(df_inv, sel_fy)
if not tax:
    info_box("Could not compute tax data.")
    st.stop()

unreal = tax["unreal"]
t      = tax["tax"]
fy_s, fy_e = fy_date_range(sel_fy)

# ── Banner ──
st.markdown(f"""
<div style='background:{T["card"]};border:1px solid {T["accent"]}44;border-left:4px solid {T["accent"]};
            border-radius:12px;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;margin-bottom:16px'>
  <div>
    <div style='font-size:13px;font-weight:800;color:{T["accent"]}'>{sel_fy}</div>
    <div style='font-size:11px;color:{T["muted"]}'>1 Apr {fy_s.year} → 31 Mar {fy_e.year} &nbsp;·&nbsp; Viewing: {person}</div>
  </div>
  <div style='text-align:right'>
    <div style='font-size:11px;color:{T["muted"]};margin-bottom:2px'>Total Estimated Tax</div>
    <div style='font-size:22px;font-weight:800;color:{T["red"]}'>{fmt(t["total"])}</div>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown("---")

# ── 2-col layout ──
ca, cb = st.columns(2)

with ca:
    sh("Unrealized Gains (Current Holdings)")
    st.markdown(f"""
    <div style='background:{T["card"]};border:1px solid {T["border"]};border-radius:12px;padding:16px 20px;margin-bottom:12px'>
      <div style='font-size:12px;font-weight:700;color:{T["accent"]};margin-bottom:12px;text-transform:uppercase;letter-spacing:.06em'>Equity & Equity Mutual Funds</div>
      <div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {T["border"]}44'>
        <span style='font-size:12px;color:{T["muted"]}'>STCG (&lt;12 months) @ 20%</span>
        <div style='text-align:right'>
          <span style='font-size:12px;font-weight:700;color:{T["text"]}'>{fmt(unreal["stcg_eq"])}</span>
          <span style='font-size:11px;color:{T["red"]};margin-left:8px'>Tax: {fmt(t["stcg_eq"])}</span>
        </div>
      </div>
      <div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {T["border"]}44'>
        <span style='font-size:12px;color:{T["muted"]}'>LTCG (≥12 months) @ 12.5%</span>
        <div style='text-align:right'>
          <span style='font-size:12px;font-weight:700;color:{T["text"]}'>{fmt(unreal["ltcg_eq"])}</span>
          <span style='font-size:11px;color:{T["red"]};margin-left:8px'>Tax: {fmt(t["ltcg_eq"])}</span>
        </div>
      </div>
      <div style='padding:6px 0;background:{T["card2"]};border-radius:6px;padding:6px 10px;margin-top:4px'>
        <span style='font-size:11px;color:{T["gold"]}'>✦ LTCG exemption used: {fmt(tax["ltcg_exemption_used"])} of Rs.1.25L</span><br>
        <span style='font-size:11px;color:{T["muted"]}'>Taxable LTCG after exemption: {fmt(tax["ltcg_eq_taxable"])}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='background:{T["card"]};border:1px solid {T["border"]};border-radius:12px;padding:16px 20px;margin-bottom:12px'>
      <div style='font-size:12px;font-weight:700;color:{T["gold"]};margin-bottom:12px;text-transform:uppercase;letter-spacing:.06em'>Gold</div>
      <div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {T["border"]}44'>
        <span style='font-size:12px;color:{T["muted"]}'>STCG (&lt;24 months) @ 30% slab</span>
        <div style='text-align:right'>
          <span style='font-size:12px;font-weight:700;color:{T["text"]}'>{fmt(unreal["stcg_gold"])}</span>
          <span style='font-size:11px;color:{T["red"]};margin-left:8px'>Tax: {fmt(t["stcg_gold"])}</span>
        </div>
      </div>
      <div style='display:flex;justify-content:space-between;padding:6px 0'>
        <span style='font-size:12px;color:{T["muted"]}'>LTCG (≥24 months) @ 12.5%</span>
        <div style='text-align:right'>
          <span style='font-size:12px;font-weight:700;color:{T["text"]}'>{fmt(unreal["ltcg_gold"])}</span>
          <span style='font-size:11px;color:{T["red"]};margin-left:8px'>Tax: {fmt(t["ltcg_gold"])}</span>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='background:{T["card"]};border:1px solid {T["border"]};border-radius:12px;padding:16px 20px;margin-bottom:12px'>
      <div style='font-size:12px;font-weight:700;color:{T["green"]};margin-bottom:12px;text-transform:uppercase;letter-spacing:.06em'>Debt / Debt MF / NPS</div>
      <div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {T["border"]}44'>
        <span style='font-size:12px;color:{T["muted"]}'>STCG (&lt;36 months) @ slab ~30%</span>
        <div style='text-align:right'>
          <span style='font-size:12px;font-weight:700;color:{T["text"]}'>{fmt(unreal["stcg_debt"])}</span>
        </div>
      </div>
      <div style='display:flex;justify-content:space-between;padding:6px 0'>
        <span style='font-size:12px;color:{T["muted"]}'>LTCG (≥36 months) @ slab ~30%</span>
        <div style='text-align:right'>
          <span style='font-size:12px;font-weight:700;color:{T["text"]}'>{fmt(unreal["ltcg_debt"])}</span>
        </div>
      </div>
      <div style='padding:6px 10px;background:{T["card2"]};border-radius:6px;margin-top:4px'>
        <span style='font-size:11px;color:{T["red"]}'>Combined debt tax estimate: {fmt(t["debt"])}</span>
      </div>
    </div>""", unsafe_allow_html=True)

with cb:
    sh("Tax Estimate Breakdown")
    tax_labels = ["STCG Equity","LTCG Equity","STCG Gold","LTCG Gold","Debt/NPS"]
    tax_vals   = [t["stcg_eq"],t["ltcg_eq"],t["stcg_gold"],t["ltcg_gold"],t["debt"]]
    colors     = ["#00d4ff","#7c3aed","#f59e0b","#f97316","#00e5a0"]

    non_zero = [(l,v,c) for l,v,c in zip(tax_labels,tax_vals,colors) if v>0]
    if non_zero:
        fig_t = go.Figure(go.Pie(
            labels=[x[0] for x in non_zero],
            values=[x[1] for x in non_zero],
            hole=0.6,
            marker=dict(colors=[x[2] for x in non_zero],line=dict(color=T["bg"],width=2)),
            textinfo="percent+label", textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>Rs.%{value:,.0f}<br>%{percent}<extra></extra>"))
        fig_t.update_layout(**plot_layout(), height=280,
            annotations=[dict(text=f"<b>{fmt(t['total'])}</b>",x=0.5,y=0.5,
                              font=dict(size=11,color=T["text"]),showarrow=False)])
        st.plotly_chart(fig_t, use_container_width=True)
    else:
        st.markdown(f'<div style="padding:40px;text-align:center;color:{T["muted"]}">No taxable gains yet</div>', unsafe_allow_html=True)

    # Summary card
    st.markdown(f"""
    <div style='background:{T["card"]};border:1px solid {T["border"]};border-radius:12px;padding:16px 20px;'>
      <div style='font-size:12px;font-weight:700;color:{T["text"]};margin-bottom:12px'>Estimated Tax Summary</div>
      {''.join(f"""
      <div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid {T["border"]}33'>
        <span style='font-size:12px;color:{T["muted"]}'>{lbl}</span>
        <span style='font-size:12px;font-weight:700;color:{T["red"]}'>{fmt(val)}</span>
      </div>""" for lbl, val in zip(tax_labels, tax_vals) if val > 0)}
      <div style='display:flex;justify-content:space-between;padding:8px 0 4px;margin-top:4px;border-top:2px solid {T["border"]}'>
        <span style='font-size:13px;font-weight:800;color:{T["text"]}'>Total Estimated Tax</span>
        <span style='font-size:14px;font-weight:800;color:{T["red"]}'>{fmt(t["total"])}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # Tax rules reference
    st.markdown(f"""
    <div class="info-box" style="margin-top:12px">
      <b>Indian Tax Rules (post-Jul 2024)</b><br>
      <span style='color:{T["accent"]}'>Equity / Equity MF:</span> STCG &lt;12m = <b>20%</b>; LTCG ≥12m = <b>12.5%</b> (Rs.1.25L exempt)<br>
      <span style='color:{T["gold"]}'>Gold:</span> STCG &lt;24m = <b>slab rate</b>; LTCG ≥24m = <b>12.5%</b><br>
      <span style='color:{T["green"]}'>Debt MF / NPS:</span> Added to income, taxed at <b>slab rate</b> (~30% estimated)<br>
      <span style='color:{T["muted"]}'>Surcharge & cess not included. Consult a CA before filing.</span>
    </div>""", unsafe_allow_html=True)

st.markdown("---")
sh("Position-wise Tax Detail")
detail_rows = tax.get("detail_rows", [])
if detail_rows:
    ddf = pd.DataFrame(detail_rows)
    ddf = ddf.sort_values("Gain", ascending=False)

    # Filter controls
    fc1, fc2 = st.columns(2)
    ftype = fc1.selectbox("Filter", ["All","STCG only","LTCG only","Gains only","Losses only"])
    fclass= fc2.selectbox("Asset Class", ["All"] + sorted(ddf["Class"].unique().tolist()))

    fd = ddf.copy()
    if ftype == "STCG only":   fd = fd[fd["Type"]=="STCG"]
    if ftype == "LTCG only":   fd = fd[fd["Type"]=="LTCG"]
    if ftype == "Gains only":  fd = fd[fd["Gain"]>0]
    if ftype == "Losses only": fd = fd[fd["Gain"]<0]
    if fclass != "All":        fd = fd[fd["Class"]==fclass]

    rows_html = ""
    for _, r in fd.iterrows():
        gc   = T["green"]  if r["Gain"]>=0   else T["red"]
        tc   = T["accent"] if r["Type"]=="LTCG" else T["gold"]
        garr = "+" if r["Gain"]>=0 else "-"
        rows_html += f"""<tr>
          <td class="bold" style="max-width:180px;overflow:hidden;text-overflow:ellipsis">{r["Asset"]}</td>
          <td><span class="badge" style="background:{tc}22;color:{tc}">{r["Type"]}</span></td>
          <td class="mono" style="color:{T['muted']}">{r["Hold_Mo"]:.0f}m</td>
          <td class="mono">{fmt(r["Invested"])}</td>
          <td class="mono" style="font-weight:700">{fmt(r["Current"])}</td>
          <td class="mono" style="color:{gc};font-weight:700">{garr} {fmt(abs(r["Gain"]))}</td>
          <td class="mono" style="color:{T['muted']}">{r["Tax_Rate"]}</td>
          <td class="mono" style="color:{T['red']};font-weight:700">{fmt(r["Est_Tax"])}</td>
        </tr>"""
    st.markdown(f"""
    <div class="ft-wrap"><table class="ft">
      <thead><tr><th>Asset</th><th>Type</th><th>Held</th><th>Invested</th>
      <th>Current</th><th>Gain/Loss</th><th>Rate</th><th>Est. Tax</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>""", unsafe_allow_html=True)
    st.caption(f"Showing {len(fd)} positions · Total est. tax on filtered positions: {fmt(fd['Est_Tax'].sum())}")
else:
    info_box("No position detail available.")

st.markdown("---")
st.markdown(f"""
<div class="info-box">
  <b>⚠️ Disclaimer:</b> These are rough estimates for planning purposes only. Actual tax liability depends on your income slab,
  exact purchase lots (FIFO), indexation where applicable, 80C deductions, and other factors.
  Always consult a qualified Chartered Accountant for accurate tax computation and ITR filing.
</div>""", unsafe_allow_html=True)
