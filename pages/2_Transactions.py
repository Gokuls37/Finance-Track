import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
import pandas as pd
from utils.shared import inject_css, render_sidebar, get_data, get_theme, sh, fmt, fmt_nav, fmt_units, info_box, build_investment_df, PERSONS_FAM

st.set_page_config(page_title="Transactions – Finance Track", page_icon="📋", layout="wide", initial_sidebar_state="expanded")
inject_css(); T = get_theme(); data = get_data(); render_sidebar("Transactions")
person = st.session_state.get("sb_person","Family")

st.title("📋 Transaction History")
df = build_investment_df(data["inv"], data["prices"], person)
if df.empty:
    info_box("No transactions yet."); st.stop()

# Filters
c1,c2,c3 = st.columns(3)
classes = ["All"] + sorted(df["Asset_Class"].dropna().unique().tolist())
sel_cls = c1.selectbox("Asset Class", classes)
types   = ["All"] + sorted(df["Transaction_Type"].dropna().unique().tolist()) if "Transaction_Type" in df.columns else ["All"]
sel_tt  = c2.selectbox("Type", types)
search  = c3.text_input("Search asset name")

fdf = df.copy()
if sel_cls != "All": fdf = fdf[fdf["Asset_Class"]==sel_cls]
if sel_tt  != "All" and "Transaction_Type" in fdf.columns: fdf = fdf[fdf["Transaction_Type"]==sel_tt]
if search: fdf = fdf[fdf["Asset_Name"].str.contains(search, case=False, na=False)]
fdf = fdf.sort_values("Date", ascending=False)

if fdf.empty:
    info_box("No records match filters."); st.stop()

rows = ""
for _, r in fdf.iterrows():
    ds  = r["Date"].strftime("%d %b %Y") if pd.notna(r["Date"]) else "—"
    pc  = T["accent"] if r.get("Person")=="Gokul" else (T["accent2"] if r.get("Person")=="Yamuna" else T["muted"])
    tc  = T["green"] if str(r.get("Transaction_Type","")).upper() in ("BUY","SIP") else T["red"]
    ac  = str(r.get("Asset_Class",""))
    cc  = {"Equity":T["accent"],"Mutual Fund":T["accent2"],"Gold":T["gold"],"Debt":T["green"]}.get(ac, T["muted"])
    rows += f"""<tr>
      <td style="color:{T['muted']};font-size:12px">{ds}</td>
      <td><span class="badge" style="background:{pc}22;color:{pc}">{r.get("Person","")}</span></td>
      <td><span class="badge" style="background:{cc}22;color:{cc}">{ac}</span></td>
      <td class="bold">{r.get("Asset_Name","")}</td>
      <td><span class="badge" style="background:{tc}22;color:{tc}">{r.get("Transaction_Type","")}</span></td>
      <td class="mono" style="color:{T['accent']}">{fmt_units(r.get("Quantity",0))}</td>
      <td class="mono" style="color:{T['muted']}">{fmt_nav(r.get("Price",0))}</td>
      <td class="mono" style="font-weight:700">{fmt(r["Invested"])}</td>
    </tr>"""

st.markdown(f'<div class="ft-wrap"><table class="ft"><thead><tr><th>Date</th><th>Person</th><th>Class</th><th>Asset</th><th>Type</th><th>Units/Qty</th><th>Price/NAV</th><th>Amount</th></tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)
