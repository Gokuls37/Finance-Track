import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
import plotly.graph_objects as go
from utils.shared import inject_css, render_sidebar, get_data, get_theme, sh, fmt, fmt_nav, fmt_units, pct, build_investment_df, plot_layout, info_box, safe_roi, PIE_COLORS, PERSONS_FAM

st.set_page_config(page_title="Debt - Finance Track", page_icon="🏛️", layout="wide", initial_sidebar_state="expanded")
inject_css(); T = get_theme(); data = get_data(); render_sidebar("Debt")
person = st.session_state.get("sb_person","Family")
df = build_investment_df(data["inv"], data["prices"], person)
sub = df[df["Asset_Class"]=="Debt"].copy() if not df.empty else __import__("pandas").DataFrame()
st.title("🏛️ Debt Portfolio")

# Person filter
import pandas as pd
if not sub.empty and "Person" in sub.columns:
    plist = ["Family"] + sorted(sub["Person"].dropna().unique().tolist())
    sel_p = st.selectbox("View by Person", plist, key="Debt_pf")
    if sel_p != "Family": sub = sub[sub["Person"]==sel_p]

if sub.empty: info_box("No Debt investments found."); st.stop()

ti=sub["Invested"].sum(); tv=sub["Current_Value"].sum(); tg=tv-ti; tr=safe_roi(tg,ti)
k1,k2,k3,k4 = st.columns(4)
k1.metric("Total Value",fmt(tv),pct(tr)); k2.metric("Total Invested",fmt(ti))
k3.metric("Total Gain",fmt(abs(tg)),"Profit" if tg>=0 else "Loss"); k4.metric("Holdings",str(sub["Asset_Name"].nunique()))
st.markdown("---")

tbl=(sub.groupby("Asset_Name").agg(Invested=("Invested","sum"),Current=("Current_Value","sum"),Quantity=("Quantity","sum")).reset_index())
tbl["Gain"]=tbl["Current"]-tbl["Invested"]
tbl["ROI"]=tbl.apply(lambda r:safe_roi(r["Gain"],r["Invested"]),axis=1)
tbl["Avg_Cost"]=tbl.apply(lambda r:r["Invested"]/r["Quantity"] if r["Quantity"]>0 else 0,axis=1)
tbl["Cur_Price"]=tbl["Asset_Name"].map(sub.groupby("Asset_Name")["Current_Price"].last())

ca,cb=st.columns([1.2,1])
with ca:
    sh("Invested vs Current"); fb=go.Figure()
    fb.add_trace(go.Bar(x=tbl["Asset_Name"].str[:20],y=tbl["Invested"],name="Invested",marker_color=T["accent2"],marker_line_width=0))
    fb.add_trace(go.Bar(x=tbl["Asset_Name"].str[:20],y=tbl["Current"],name="Current",marker_color=T["accent"],marker_line_width=0))
    fb.update_layout(**plot_layout(),height=300,barmode="group",bargap=0.25); st.plotly_chart(fb,use_container_width=True)
with cb:
    sh("Allocation"); fp=go.Figure(go.Pie(labels=tbl["Asset_Name"].str[:18],values=tbl["Current"],hole=0.55,
        marker=dict(colors=PIE_COLORS,line=dict(color=T["bg"],width=2)),textinfo="percent",textfont=dict(size=11)))
    fp.update_layout(**plot_layout(),height=300); st.plotly_chart(fp,use_container_width=True)

st.markdown("---"); sh("Debt Holdings")
rows_h=""
for _,row in tbl.sort_values("ROI",ascending=False).iterrows():
    gc=T["green"] if row["Gain"]>=0 else T["red"]; rc=T["green"] if row["ROI"]>=0 else T["red"]
    rows_h+=("<tr>"
        +f'<td class="bold">{row["Asset_Name"]}</td>'
        +f'<td class="mono" style="color:{T["accent"]};font-weight:700">{fmt_units(row["Quantity"])}</td>'
        +f'<td class="mono" style="color:{T["muted"]}">{fmt_nav(row["Avg_Cost"])}</td>'
        +f'<td class="mono">{fmt_nav(row["Cur_Price"])}</td>'
        +f'<td class="mono">{fmt(row["Invested"])}</td>'
        +f'<td class="mono" style="font-weight:700">{fmt(row["Current"])}</td>'
        +f'<td class="mono" style="color:{gc};font-weight:700">{"+" if row["Gain"]>=0 else "-"} {fmt(abs(row["Gain"]))}</td>'
        +f'<td><span class="badge" style="background:{rc}22;color:{rc}">{pct(row["ROI"])}</span></td>'
        +"</tr>")
st.markdown(f'<div class="ft-wrap"><table class="ft"><thead><tr><th>Asset</th><th>Units/Qty</th><th>Avg Cost</th><th>Cur Price</th><th>Invested</th><th>Current</th><th>Gain/Loss</th><th>ROI</th></tr></thead><tbody>{rows_h}</tbody></table></div>',unsafe_allow_html=True)
