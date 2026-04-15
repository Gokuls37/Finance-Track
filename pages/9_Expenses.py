import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
from utils.shared import (
    inject_css, render_sidebar, get_data, get_theme, sh, fmt, pct,
    plot_layout, save_row, info_box, PIE_COLORS,
    EXPENSE_CATEGORIES, MONTHS_ORDER
)

st.set_page_config(page_title="Expenses – Finance Track", page_icon="💸",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
T = get_theme()
data = get_data()

render_sidebar("Expenses")

# ── Load & prep ──
exp_raw = data["expenses"].copy() if not data["expenses"].empty else pd.DataFrame()
if not exp_raw.empty:
    exp_raw["Date"]   = pd.to_datetime(exp_raw["Date"], errors="coerce")
    exp_raw["Amount"] = pd.to_numeric(exp_raw["Amount"], errors="coerce").fillna(0)
    exp_raw["Month"]  = exp_raw["Date"].dt.strftime("%b %Y")
    exp_raw["MonthN"] = exp_raw["Date"].dt.to_period("M")

st.title("💸 Expense Tracker")

tab1, tab2, tab3 = st.tabs(["📊  Overview", "➕  Add Expense", "📋  Records"])

# ════════════════════════════════════════════════════════
#  TAB 1 — OVERVIEW
# ════════════════════════════════════════════════════════
with tab1:
    if exp_raw.empty:
        info_box("No expense records yet. Use Add Expense tab to get started.")
    else:
        fc1, fc2, fc3 = st.columns(3)
        all_months    = sorted(exp_raw["MonthN"].dropna().unique(), reverse=True)
        month_labels  = [str(m) for m in all_months]
        sel_months    = fc1.multiselect("Filter by Month", month_labels,
                                         default=month_labels[:3],
                                         placeholder="All months")
        all_cats = ["All"] + sorted(exp_raw["Category"].dropna().unique().tolist())
        sel_cat  = fc2.selectbox("Category", all_cats, key="ov_cat")
        sel_per  = fc3.selectbox("Person", ["Family","Gokul","Yamuna","Kavitha"], key="ov_per")

        filt = exp_raw.copy()
        if sel_months:
            filt = filt[filt["MonthN"].astype(str).isin(sel_months)]
        if sel_cat != "All":
            filt = filt[filt["Category"]==sel_cat]
        if sel_per != "Family":
            filt = filt[filt["Person"]==sel_per]

        if filt.empty:
            info_box("No records for selected filters.")
        else:
            total      = filt["Amount"].sum()
            month_sums = filt.groupby("MonthN")["Amount"].sum()
            avg_month  = month_sums.mean() if len(month_sums) > 0 else 0.0
            if pd.isna(avg_month): avg_month = total
            top_cat   = filt.groupby("Category")["Amount"].sum().idxmax()
            top_val   = filt.groupby("Category")["Amount"].sum().max()
            num_txn   = len(filt)

            k1,k2,k3,k4 = st.columns(4)
            k1.metric("Total Spent",   fmt(total))
            k2.metric("Avg / Month",   fmt(avg_month))
            k3.metric("Top Category",  top_cat, fmt(top_val))
            k4.metric("Transactions",  str(num_txn))

            st.markdown("---")
            cl, cr = st.columns([1.5,1])

            with cl:
                sh("Monthly Expenses by Category")
                monthly = (filt.groupby(["MonthN","Category"])["Amount"]
                           .sum().reset_index().sort_values("MonthN"))
                monthly["MonthStr"] = monthly["MonthN"].astype(str)
                cats_list = monthly["Category"].unique()

                fig_bar = go.Figure()
                for i,cat in enumerate(cats_list):
                    sub = monthly[monthly["Category"]==cat]
                    fig_bar.add_trace(go.Bar(
                        x=sub["MonthStr"], y=sub["Amount"],
                        name=cat, marker_color=PIE_COLORS[i%len(PIE_COLORS)],
                        marker_line_width=0,
                        hovertemplate=f"<b>{cat}</b><br>%{{x}}<br>Rs.%{{y:,.0f}}<extra></extra>"))
                fig_bar.update_layout(**plot_layout(), height=320, barmode="stack")
                st.plotly_chart(fig_bar, use_container_width=True)

            with cr:
                sh("Category Split")
                cat_sum = filt.groupby("Category")["Amount"].sum().reset_index()
                fig_pie = go.Figure(go.Pie(
                    labels=cat_sum["Category"], values=cat_sum["Amount"],
                    hole=0.55, marker=dict(colors=PIE_COLORS,
                    line=dict(color=T["bg"],width=2)),
                    textinfo="percent", textfont=dict(size=11),
                    hovertemplate="<b>%{label}</b><br>Rs.%{value:,.0f}<br>%{percent}<extra></extra>"))
                fig_pie.update_layout(**plot_layout(), height=320)
                st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown("---")
            sh("Monthly Spend Trend")
            m_total = (filt.groupby("MonthN")["Amount"].sum()
                       .reset_index().sort_values("MonthN"))
            m_total["MonthStr"] = m_total["MonthN"].astype(str)

            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=m_total["MonthStr"], y=m_total["Amount"],
                mode="lines+markers+text",
                line=dict(color=T["red"],width=2.5),
                marker=dict(size=8, color=T["red"]),
                text=m_total["Amount"].map(fmt),
                textposition="top center",
                textfont=dict(size=10, color=T["muted"]),
                fill="tozeroy",
                fillcolor="rgba(255,77,109,0.07)" if st.session_state.theme=="Dark" else "rgba(220,38,38,0.05)",
            ))
            fig_line.update_layout(**plot_layout(), height=250)
            st.plotly_chart(fig_line, use_container_width=True)

            st.markdown("---")
            sh("Top Spending Categories")
            cat_rank = (filt.groupby("Category")["Amount"].sum()
                        .reset_index().sort_values("Amount",ascending=False).head(10))
            total_spend = cat_rank["Amount"].sum()

            html = ""
            for i,(_,r) in enumerate(cat_rank.iterrows()):
                used  = r["Amount"]/total_spend*100 if total_spend>0 else 0
                color = PIE_COLORS[i%len(PIE_COLORS)]
                html += f"""
                <div style='margin-bottom:13px'>
                  <div style='display:flex;justify-content:space-between;margin-bottom:4px'>
                    <span style='font-size:13px;font-weight:700;color:{T["text"]}'>{r["Category"]}</span>
                    <span style='font-size:12px;color:{T["muted"]}'>{fmt(r["Amount"])}
                      <span style='color:{color};font-weight:700;margin-left:6px'>{used:.1f}%</span>
                    </span>
                  </div>
                  <div style='background:{T["border"]};border-radius:5px;height:7px;overflow:hidden'>
                    <div style='width:{used:.1f}%;height:100%;background:{color};border-radius:5px'></div>
                  </div>
                </div>"""
            st.markdown(html, unsafe_allow_html=True)

            st.markdown("---")
            sh("Person-wise Spend")
            p1, p2 = st.columns(2)
            for col, person in zip([p1,p2], ["Gokul","Yamuna","Kavitha"]):
                psub   = filt[filt["Person"].isin([person,"Family"])]
                ptotal = psub["Amount"].sum()
                pcat   = (psub.groupby("Category")["Amount"].sum()
                          .reset_index().sort_values("Amount",ascending=False).head(6))
                color  = T["accent"] if person=="Gokul" else T["accent2"]
                with col:
                    st.markdown(f"""
                    <div style='background:{T["card"]};border:1px solid {color}33;border-radius:14px;
                                padding:16px 20px;margin-bottom:8px'>
                      <div style='font-size:12px;color:{T["muted"]};margin-bottom:4px'>{person}</div>
                      <div style='font-size:22px;font-weight:800;color:{color}'>{fmt(ptotal)}</div>
                    </div>""", unsafe_allow_html=True)
                    rows = "".join(f"""
                    <tr>
                      <td class="bold">{r["Category"]}</td>
                      <td class="mono" style="color:{T['red']};font-weight:700">{fmt(r["Amount"])}</td>
                    </tr>""" for _,r in pcat.iterrows()) if ptotal>0 else ""
                    st.markdown(f"""
                    <div class="ft-wrap"><table class="ft">
                      <thead><tr><th>Category</th><th>Amount</th></tr></thead>
                      <tbody>{rows}</tbody>
                    </table></div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  TAB 2 — ADD EXPENSE
# ════════════════════════════════════════════════════════
with tab2:
    sh("Add New Expense")

    c1, c2 = st.columns(2)
    exp_person   = c1.selectbox("Person *", ["Family","Gokul","Yamuna","Kavitha"], key="exp_person")
    exp_category = c2.selectbox("Category *", EXPENSE_CATEGORIES, key="exp_cat")

    # Quick amount buttons — set value via session_state BEFORE widget renders
    if "exp_amt_val" not in st.session_state:
        st.session_state["exp_amt_val"] = 0.0

    st.markdown(f'<div style="font-size:11px;color:{T["muted"]};margin-bottom:6px">Quick amounts:</div>',
                unsafe_allow_html=True)
    qa_cols = st.columns(6)
    for i, amt in enumerate([500, 1000, 2000, 5000, 10000, 20000]):
        if qa_cols[i].button(f"₹{amt:,}", key=f"qa_{amt}", use_container_width=True):
            st.session_state["exp_amt_val"] = float(amt)

    c3, c4 = st.columns(2)
    exp_amount = c3.number_input("Amount (Rs.) *", min_value=0.0, step=50.0,
                                  value=st.session_state["exp_amt_val"],
                                  key="exp_amt",
                                  on_change=lambda: st.session_state.update({"exp_amt_val": st.session_state["exp_amt"]}))
    exp_date   = c4.date_input("Date *", value=date.today(), key="exp_date")

    exp_note = st.text_input("Note / Description",
                              placeholder="e.g. BigBasket order, Petrol, Doctor visit",
                              key="exp_note")

    if exp_amount > 0:
        rc = T["red"]
        st.markdown(f"""
        <div style='background:{rc}0f;border:1px solid {rc}33;border-radius:10px;
                    padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin:10px 0'>
          <div>
            <div style='font-size:11px;color:{T["muted"]};text-transform:uppercase;letter-spacing:.07em'>Entry Preview</div>
            <div style='font-size:13px;color:{T["text"]};margin-top:2px'>{exp_person}  ·  {exp_category}  ·  {str(exp_date)}</div>
          </div>
          <div style='font-size:24px;font-weight:800;color:{rc}'>{fmt(exp_amount)}</div>
        </div>""", unsafe_allow_html=True)

    save_exp = st.button("💾 Save Expense", use_container_width=False, key="exp_save")

    if save_exp:
        if exp_amount <= 0:
            st.error("Enter a valid amount.")
        else:
            row = [str(exp_date), exp_person, exp_category, float(exp_amount), exp_note, str(datetime.now())]
            ok = save_row("Expenditure_Ledger", row)
            if ok:
                st.success(f"✅ Saved! **{exp_category}** — {fmt(exp_amount)}")
                st.session_state["exp_amt_val"] = 0.0
                st.rerun()

    st.markdown("---")
    st.markdown(f"""
    <div class="info-box">
      <b>Google Sheet column format for Expenses:</b><br>
      <code>Date | Person | Category | Amount | Note | Timestamp</code><br><br>
      Person can be: Gokul, Yamuna, or Family (shared expense)
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  TAB 3 — RECORDS
# ════════════════════════════════════════════════════════
with tab3:
    if exp_raw.empty:
        info_box("No expense records found.")
    else:
        sc1, sc2, sc3 = st.columns(3)
        ep   = sc1.selectbox("Person", ["All","Gokul","Yamuna","Kavitha","Family"], key="erec_p")
        ec   = sc2.selectbox("Category", ["All"]+sorted(exp_raw["Category"].dropna().unique().tolist()), key="erec_c")
        esrch= sc3.text_input("Search note", key="erec_s")

        eview = exp_raw.copy().sort_values("Date", ascending=False)
        if ep != "All":
            eview = eview[eview["Person"]==ep]
        if ec != "All":
            eview = eview[eview["Category"]==ec]
        if esrch:
            eview = eview[eview["Note"].str.contains(esrch,case=False,na=False)]

        st.caption(f"{len(eview)} records  ·  Total: {fmt(eview['Amount'].sum())}")

        rows = ""
        for _,r in eview.iterrows():
            ds  = r["Date"].strftime("%d %b %Y") if pd.notna(r["Date"]) else ""
            pc  = T["accent"] if r.get("Person","")=="Gokul" else (T["accent2"] if r.get("Person","")=="Yamuna" else T["muted"])
            cat_color = PIE_COLORS[EXPENSE_CATEGORIES.index(r.get("Category","Other")) % len(PIE_COLORS)] if r.get("Category","") in EXPENSE_CATEGORIES else T["muted"]
            rows += f"""
            <tr>
              <td class="mono" style="color:{T['muted']}">{ds}</td>
              <td><span class="badge" style="background:{pc}22;color:{pc}">{r.get("Person","")}</span></td>
              <td><span class="badge" style="background:{cat_color}22;color:{cat_color}">{r.get("Category","")}</span></td>
              <td class="mono" style="font-weight:700;color:{T['red']}">{fmt(r["Amount"])}</td>
              <td style="color:{T['muted']};font-size:12px">{r.get("Note","")}</td>
            </tr>"""
        st.markdown(f"""
        <div class="ft-wrap"><table class="ft">
          <thead><tr><th>Date</th><th>Person</th><th>Category</th><th>Amount</th><th>Note</th></tr></thead>
          <tbody>{rows}</tbody>
        </table></div>""", unsafe_allow_html=True)

        if not data["demo"]:
            st.markdown("---")
            sh("Delete Records")
            eview2 = exp_raw.copy().reset_index()
            selected = []
            for i,r in eview2.iterrows():
                ds  = r["Date"].strftime("%d %b %Y") if pd.notna(r["Date"]) else "No date"
                lbl = f"{ds}  |  {r.get('Person','')}  |  {r.get('Category','')}  |  {fmt(r['Amount'])}"
                if st.checkbox(lbl, key=f"edel_{i}"):
                    selected.append(i+2)
            if selected:
                if st.button(f"Delete {len(selected)} record(s)", type="primary", key="exp_del_btn"):
                    try:
                        from utils.shared import get_sheet
                        ws = get_sheet().worksheet("Expenditure_Ledger")
                        for rn in sorted(selected, reverse=True):
                            ws.delete_rows(rn)
                        st.cache_data.clear()
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")