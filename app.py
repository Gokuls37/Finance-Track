import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from utils.shared import (
    inject_css, render_sidebar, get_data, build_investment_df,
    get_theme, sh, fmt, pct, safe_roi, plot_layout,
    PIE_COLORS, CLASS_COLORS, get_fy_list, fy_date_range, current_fy,
    compute_tax_summary, LTCG_EXEMPTION
)

st.set_page_config(page_title="Finance Track", page_icon="💼",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
T = get_theme()
data = get_data()
inv_raw = data["inv"]; prices_raw = data["prices"]

render_sidebar("Dashboard")
with st.sidebar:
    if data["demo"]:
        st.markdown(f'<div class="info-box" style="border-left-color:{T["gold"]}">🟡 Demo — add credentials.json</div>',
                    unsafe_allow_html=True)
    nw_df = build_investment_df(inv_raw, prices_raw, "Family")
    if not nw_df.empty:
        nw = nw_df["Current_Value"].sum(); ti2 = nw_df["Invested"].sum()
        r2 = safe_roi(nw-ti2, ti2); fc = T["green"] if r2>=0 else T["red"]
        st.markdown(f"""<div class="nw-widget">
          <div style='font-size:10px;color:{T["muted"]};text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px'>Family Net Worth</div>
          <div style='font-size:20px;font-weight:800;color:{T["accent"]}'>{fmt(nw)}</div>
          <div style='font-size:12px;color:{fc};margin-top:4px;font-weight:700'>{"+" if r2>=0 else ""}{r2:.2f}% overall</div>
        </div>""", unsafe_allow_html=True)

person = st.session_state.get("sb_person","Family")
df_all = build_investment_df(inv_raw, prices_raw, person)

ct, cf = st.columns([3,1])
with ct:
    st.title("📊 Family Finance Dashboard")
    st.caption(f"Viewing: **{person}**  ·  {datetime.now().strftime('%d %b %Y, %H:%M')}")
with cf:
    yrs = df_all["Date"].dt.year.dropna().unique().astype(int) if not df_all.empty and df_all["Date"].notna().any() else []
    fy_opts = ["All Time"] + get_fy_list(yrs) if len(yrs) else ["All Time", current_fy()]
    cfy = current_fy()
    sel_fy = st.selectbox("Financial Year", fy_opts,
                           index=fy_opts.index(cfy) if cfy in fy_opts else 0, key="dash_fy")

df = df_all.copy()
if sel_fy != "All Time" and not df.empty:
    fy_s, fy_e = fy_date_range(sel_fy)
    df = df[df["Date"].between(fy_s, fy_e)]
if df.empty:
    st.info(f"No data for {sel_fy}. Showing all-time data.")
    df = df_all.copy()
if df.empty:
    st.info("No investment data yet. Add via Add Investment page."); st.stop()

ti = df["Invested"].sum(); tv = df["Current_Value"].sum()
gn = tv - ti; roi = safe_roi(gn, ti)

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Net Worth",      fmt(tv),      f"{'+'if roi>=0 else ''}{roi:.2f}%")
k2.metric("Total Invested", fmt(ti))
k3.metric("Total Gain",     fmt(abs(gn)), "Profit" if gn>=0 else "Loss")
k4.metric("Overall ROI",    pct(roi))
k5.metric("Holdings",       str(df["Asset_Name"].nunique()))

if sel_fy != "All Time":
    fy_s, fy_e = fy_date_range(sel_fy)
    st.markdown(f"""<div style='background:{T["card"]};border:1px solid {T["border"]};border-left:4px solid {T["accent"]};
      border-radius:10px;padding:8px 16px;margin:4px 0 10px;display:flex;justify-content:space-between;align-items:center;'>
      <span style='font-size:12px;font-weight:700;color:{T["accent"]}'>{sel_fy}</span>
      <span style='font-size:11px;color:{T["muted"]}'>1 Apr {fy_s.year} → 31 Mar {fy_e.year}</span>
    </div>""", unsafe_allow_html=True)

st.markdown("---")
ca, cb = st.columns([1,1.4])
with ca:
    sh("Asset Allocation")
    alloc = df.groupby("Asset_Class")["Current_Value"].sum().reset_index()
    fig_p = go.Figure(go.Pie(labels=alloc["Asset_Class"], values=alloc["Current_Value"], hole=0.62,
        marker=dict(colors=PIE_COLORS, line=dict(color=T["bg"],width=2)),
        textinfo="percent+label", textfont=dict(size=11)))
    fig_p.update_layout(**plot_layout(), height=290,
        annotations=[dict(text=f"<b>{fmt(tv)}</b>",x=0.5,y=0.5,
                          font=dict(size=12,color=T["text"]),showarrow=False)])
    st.plotly_chart(fig_p, use_container_width=True)
    for _, row in alloc.sort_values("Current_Value",ascending=False).iterrows():
        p = row["Current_Value"]/tv if tv>0 else 0
        cinv = df[df["Asset_Class"]==row["Asset_Class"]]["Invested"].sum()
        croi = safe_roi(row["Current_Value"]-cinv, cinv)
        color = CLASS_COLORS.get(row["Asset_Class"],"#00d4ff")
        fc2 = T["green"] if croi>=0 else T["red"]
        st.markdown(f"""<div style='margin-bottom:10px'>
          <div style='display:flex;justify-content:space-between;margin-bottom:4px'>
            <span style='font-size:13px;font-weight:700;color:{T["text"]}'>{row["Asset_Class"]}</span>
            <span style='font-size:12px;color:{T["muted"]}'>{fmt(row["Current_Value"])}
              &nbsp;<span style='color:{fc2};font-weight:700'>{"+" if croi>=0 else ""}{croi:.1f}%</span></span>
          </div>
          <div style='background:{T["border"]};border-radius:5px;height:6px;overflow:hidden'>
            <div style='width:{p*100:.1f}%;height:100%;background:{color};border-radius:5px'></div>
          </div></div>""", unsafe_allow_html=True)

with cb:
    sh("Class Performance")
    summary = (df.groupby("Asset_Class").agg(Invested=("Invested","sum"),Current=("Current_Value","sum")).reset_index())
    summary["Gain"] = summary["Current"]-summary["Invested"]
    summary["ROI"]  = summary.apply(lambda r: safe_roi(r["Gain"],r["Invested"]),axis=1)
    fig_b = go.Figure()
    fig_b.add_trace(go.Bar(x=summary["Asset_Class"],y=summary["Invested"],name="Invested",marker_color=T["accent2"],marker_line_width=0))
    fig_b.add_trace(go.Bar(x=summary["Asset_Class"],y=summary["Current"],name="Current",marker_color=T["accent"],marker_line_width=0))
    fig_b.update_layout(**plot_layout(),height=250,barmode="group",bargap=0.25)
    st.plotly_chart(fig_b, use_container_width=True)
    cs = st.columns(2)
    for i, (_,r) in enumerate(summary.iterrows()):
        cs[i%2].metric(r["Asset_Class"], fmt(r["Current"]), pct(r["ROI"]))

st.markdown("---")
sh("Portfolio Growth Timeline")
if not df.empty and df["Date"].notna().any():
    growth = (df.sort_values("Date").groupby("Date")[["Invested","Current_Value"]].sum().cumsum().reset_index().rename(columns={"Current_Value":"Value"}))
else:
    growth = pd.DataFrame({"Date":pd.date_range("2024-01-01",periods=6,freq="ME"),
                            "Invested":[100000,200000,300000,400000,500000,600000],
                            "Value":   [105000,215000,330000,445000,560000,690000]})
fillc = "rgba(0,212,255,0.08)" if st.session_state.theme=="Dark" else "rgba(0,119,182,0.08)"
fig_g = go.Figure()
fig_g.add_trace(go.Scatter(x=growth["Date"],y=growth["Value"],name="Portfolio Value",fill="tozeroy",mode="lines",line=dict(color=T["accent"],width=2.5),fillcolor=fillc))
fig_g.add_trace(go.Scatter(x=growth["Date"],y=growth["Invested"],name="Invested",mode="lines",line=dict(color=T["accent2"],width=2,dash="dot")))
fig_g.update_layout(**plot_layout(),height=260)
st.plotly_chart(fig_g, use_container_width=True)

st.markdown("---")
sh("Holdings by Asset Class")
class_sum = (df.groupby("Asset_Class").agg(Invested=("Invested","sum"),Current=("Current_Value","sum"),Holdings=("Asset_Name","nunique")).reset_index())
class_sum["Gain"] = class_sum["Current"]-class_sum["Invested"]
class_sum["ROI"]  = class_sum.apply(lambda r: safe_roi(r["Gain"],r["Invested"]),axis=1)
rows_h = ""
for _,r in class_sum.sort_values("Current",ascending=False).iterrows():
    cc = CLASS_COLORS.get(r["Asset_Class"],T["accent"])
    gc = T["green"] if r["Gain"]>=0 else T["red"]
    rc = T["green"] if r["ROI"]>=0  else T["red"]
    rows_h += f"""<tr>
      <td><span class="badge" style="background:{cc}22;color:{cc};font-size:13px;padding:4px 12px">{r["Asset_Class"]}</span></td>
      <td class="mono">{int(r["Holdings"])}</td><td class="mono">{fmt(r["Invested"])}</td>
      <td class="mono" style="font-weight:700">{fmt(r["Current"])}</td>
      <td class="mono" style="color:{gc};font-weight:700">{"+" if r["Gain"]>=0 else "-"} {fmt(abs(r["Gain"]))}</td>
      <td><span class="badge" style="background:{rc}22;color:{rc}">{pct(r["ROI"])}</span></td></tr>"""
st.markdown(f'<div class="ft-wrap"><table class="ft"><thead><tr><th>Asset Class</th><th>Holdings</th><th>Invested</th><th>Current Value</th><th>Gain/Loss</th><th>ROI %</th></tr></thead><tbody>{rows_h}</tbody></table></div>',unsafe_allow_html=True)

# ── FY Tax Summary ──
if sel_fy != "All Time":
    st.markdown("---")
    sh(f"💰 Tax Estimate — {sel_fy}")
    tax = compute_tax_summary(df, sel_fy)
    if tax:
        unreal = tax.get("unreal",{}); tax_d = tax.get("tax",{})
        t1,t2,t3,t4 = st.columns(4)
        t1.metric("Est. Tax Liability", fmt(tax_d.get("total",0)))
        t2.metric("Unrealized STCG",    fmt(unreal.get("stcg_eq",0)+unreal.get("stcg_gold",0)))
        t3.metric("Unrealized LTCG",    fmt(unreal.get("ltcg_eq",0)+unreal.get("ltcg_gold",0)))
        remaining = LTCG_EXEMPTION - tax.get("ltcg_exemption_used",0)
        t4.metric("LTCG Exemption Left", fmt(remaining), f"of {fmt(LTCG_EXEMPTION)}")
        if remaining > 0 and unreal.get("ltcg_eq",0) > 0:
            st.markdown(f'<div style="background:{T["green"]}0f;border:1px solid {T["green"]}33;border-left:4px solid {T["green"]};border-radius:10px;padding:12px 16px;font-size:13px">✅ <b>Tax Harvesting:</b> You have <b>{fmt(remaining)}</b> LTCG exemption left. Book profits up to this limit — completely tax-free!</div>',unsafe_allow_html=True)
