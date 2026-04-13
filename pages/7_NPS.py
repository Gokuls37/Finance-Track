import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.shared import (
    inject_css, render_sidebar, get_data, get_theme, sh, fmt, fmt_nav, pct,
    plot_layout, info_box, safe_roi, PIE_COLORS, get_fy_list, fy_date_range, current_fy
)

st.set_page_config(page_title="NPS - Finance Track", page_icon="🎖️",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
T = get_theme()
data = get_data()
render_sidebar("NPS")
person = st.session_state.get("sb_person", "Family")

st.title("🎖️ NPS Portfolio")

# ── Load from NPS_Ledger ──
nps_raw = data.get("nps", pd.DataFrame())

if nps_raw is None or nps_raw.empty:
    info_box("No NPS records found in NPS_Ledger. Use Add Investment → NPS Contribution to add entries.")
    st.stop()

nps = nps_raw.copy()
# Normalise columns
for c in ["Amount","NAV","Units","Current_NAV"]:
    if c in nps.columns:
        nps[c] = pd.to_numeric(nps[c], errors="coerce").fillna(0)
    else:
        nps[c] = 0.0

nps["Date"]          = pd.to_datetime(nps.get("Date", pd.Series()), errors="coerce")
nps["Current_Value"] = nps["Units"] * nps["Current_NAV"]
nps["Gain"]          = nps["Current_Value"] - nps["Amount"]

# Person filter
if person != "Family" and "Person" in nps.columns:
    nps = nps[nps["Person"] == person]

if nps.empty:
    info_box(f"No NPS records for {person}.")
    st.stop()

# ── KPIs ──
total_inv = nps["Amount"].sum()
total_val = nps["Current_Value"].sum()
total_gain= total_val - total_inv
roi       = safe_roi(total_gain, total_inv)
total_units = nps["Units"].sum()

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Current Value",  fmt(total_val), pct(roi))
k2.metric("Total Invested", fmt(total_inv))
k3.metric("Total Gain",     fmt(abs(total_gain)), "Profit" if total_gain>=0 else "Loss")
k4.metric("Total Units",    f"{total_units:.4f}")
k5.metric("Contributions",  str(len(nps)))

st.markdown("---")

# ── Group by Fund Manager + Asset Class ──
grp_cols = [c for c in ["Person","Fund_Manager","Asset_Class","Tier"] if c in nps.columns]
tbl = (nps.groupby(grp_cols)
       .agg(Invested=("Amount","sum"), Units=("Units","sum"),
            Current=("Current_Value","sum"))
       .reset_index())
tbl["Gain"] = tbl["Current"] - tbl["Invested"]
tbl["ROI"]  = tbl.apply(lambda r: safe_roi(r["Gain"], r["Invested"]), axis=1)
tbl["Avg_NAV"] = tbl.apply(lambda r: r["Invested"]/r["Units"] if r["Units"]>0 else 0, axis=1)

ca, cb = st.columns([1.2,1])
with ca:
    sh("Invested vs Current Value")
    label_col = "Fund_Manager" if "Fund_Manager" in tbl.columns else grp_cols[0]
    fb = go.Figure()
    fb.add_trace(go.Bar(x=tbl[label_col], y=tbl["Invested"], name="Invested",
                        marker_color=T["accent2"], marker_line_width=0))
    fb.add_trace(go.Bar(x=tbl[label_col], y=tbl["Current"], name="Current",
                        marker_color=T["accent"], marker_line_width=0))
    fb.update_layout(**plot_layout(), height=300, barmode="group", bargap=0.25)
    st.plotly_chart(fb, use_container_width=True)

with cb:
    sh("Allocation by Asset Class")
    if "Asset_Class" in tbl.columns:
        ac_grp = tbl.groupby("Asset_Class")["Current"].sum().reset_index()
        fp = go.Figure(go.Pie(
            labels=ac_grp["Asset_Class"], values=ac_grp["Current"], hole=0.55,
            marker=dict(colors=PIE_COLORS, line=dict(color=T["bg"], width=2)),
            textinfo="percent+label", textfont=dict(size=11)))
        fp.update_layout(**plot_layout(), height=300)
        st.plotly_chart(fp, use_container_width=True)

st.markdown("---")
sh("NPS Holdings Summary")

rows_html = ""
for _, row in tbl.sort_values("ROI", ascending=False).iterrows():
    gc = T["green"] if row["Gain"] >= 0 else T["red"]
    rc = T["green"] if row["ROI"]  >= 0 else T["red"]
    person_badge = f'<span class="badge" style="background:{T["border"]};color:{T["muted"]}">{row.get("Person","")}</span>' if "Person" in row else ""
    tier_badge   = f'<span class="badge" style="background:{T["accent2"]}22;color:{T["accent2"]}">{row.get("Tier","")}</span>' if "Tier" in row else ""
    fm_name      = str(row.get("Fund_Manager", row.get(grp_cols[0],"")))
    ac_name      = str(row.get("Asset_Class",""))
    rows_html += (
        "<tr>"
        + f'<td class="bold">{fm_name}</td>'
        + f'<td>{ac_name}</td>'
        + (f'<td>{tier_badge}</td>' if "Tier" in tbl.columns else "")
        + f'<td class="mono" style="color:{T["accent"]};font-weight:700">{row["Units"]:.4f}</td>'
        + f'<td class="mono" style="color:{T["muted"]}">{fmt_nav(row["Avg_NAV"])}</td>'
        + f'<td class="mono">{fmt(row["Invested"])}</td>'
        + f'<td class="mono" style="font-weight:700">{fmt(row["Current"])}</td>'
        + f'<td class="mono" style="color:{gc};font-weight:700">{"+" if row["Gain"]>=0 else "-"} {fmt(abs(row["Gain"]))}</td>'
        + f'<td><span class="badge" style="background:{rc}22;color:{rc}">{pct(row["ROI"])}</span></td>'
        + "</tr>"
    )

tier_th = "<th>Tier</th>" if "Tier" in tbl.columns else ""
st.markdown(
    f'<div class="ft-wrap"><table class="ft"><thead><tr>'
    f'<th>Fund Manager</th><th>Asset Class</th>{tier_th}'
    f'<th>Units</th><th>Avg NAV</th><th>Invested</th><th>Current</th><th>Gain/Loss</th><th>Returns</th>'
    f'</tr></thead><tbody>{rows_html}</tbody></table></div>',
    unsafe_allow_html=True)

st.markdown("---")
sh("Contribution History")

hist_rows = ""
for _, r in nps.sort_values("Date", ascending=False).iterrows():
    date_str = r["Date"].strftime("%d %b %Y") if pd.notna(r["Date"]) else "—"
    cur_val  = r["Units"] * r["Current_NAV"] if r["Current_NAV"] > 0 else r["Amount"]
    gain     = cur_val - r["Amount"]
    gc       = T["green"] if gain >= 0 else T["red"]
    hist_rows += (
        "<tr>"
        + f'<td style="color:{T["muted"]};font-size:12px">{date_str}</td>'
        + f'<td class="bold">{r.get("Fund_Manager","")}</td>'
        + f'<td style="color:{T["muted"]}">{r.get("Asset_Class","")}</td>'
        + f'<td class="mono" style="color:{T["accent"]};font-weight:700">{r["Units"]:.4f}</td>'
        + f'<td class="mono" style="color:{T["muted"]}">{fmt_nav(r["NAV"])}</td>'
        + f'<td class="mono" style="color:{T["muted"]}">{fmt_nav(r["Current_NAV"])}</td>'
        + f'<td class="mono">{fmt(r["Amount"])}</td>'
        + f'<td class="mono" style="color:{gc};font-weight:700">{"+" if gain>=0 else "-"} {fmt(abs(gain))}</td>'
        + "</tr>"
    )

st.markdown(
    '<div class="ft-wrap"><table class="ft"><thead><tr>'
    '<th>Date</th><th>Fund Manager</th><th>Asset Class</th>'
    '<th>Units</th><th>Purchase NAV</th><th>Current NAV</th><th>Amount</th><th>Gain/Loss</th>'
    f'</tr></thead><tbody>{hist_rows}</tbody></table></div>',
    unsafe_allow_html=True)
