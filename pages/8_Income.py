import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
from utils.shared import (
    inject_css, render_sidebar, get_data, get_theme, sh, fmt, pct,
    plot_layout, save_row, info_box, PIE_COLORS,
    INCOME_CATEGORIES, MONTHS_ORDER
)

st.set_page_config(page_title="Income – Finance Track", page_icon="💵",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
T = get_theme()
data = get_data()

render_sidebar("Income")

# ── Load & prep ──
inc_raw = data["income"].copy() if not data["income"].empty else pd.DataFrame()
if not inc_raw.empty:
    inc_raw["Date"]   = pd.to_datetime(inc_raw["Date"], errors="coerce")
    inc_raw["Amount"] = pd.to_numeric(inc_raw["Amount"], errors="coerce").fillna(0)
    inc_raw["Month"]  = inc_raw["Date"].dt.strftime("%b %Y")
    inc_raw["MonthN"] = inc_raw["Date"].dt.to_period("M")

st.title("💵 Income Tracker")

# ════════════════════════════════
#  TAB LAYOUT
# ════════════════════════════════
tab1, tab2, tab3 = st.tabs(["📊  Overview", "➕  Add Income", "📋  Records"])

# ════════════════════════════════════════════════════════
#  TAB 1 — OVERVIEW
# ════════════════════════════════════════════════════════
with tab1:
    if inc_raw.empty:
        info_box("No income records yet. Use the Add Income tab to get started.")
    else:
        # ── Filters ──
        fc1, fc2, fc3 = st.columns(3)
        all_months = sorted(inc_raw["MonthN"].dropna().unique(), reverse=True)
        month_labels = [str(m) for m in all_months]
        sel_months = fc1.multiselect("Filter by Month", month_labels,
                                      default=month_labels[:6],
                                      placeholder="All months")
        all_cats = ["All"] + sorted(inc_raw["Category"].dropna().unique().tolist())
        sel_cat  = fc2.selectbox("Category", all_cats)
        all_persons = ["Family","Gokul","Yamuna","Kavitha"]
        sel_person  = fc3.selectbox("Person", all_persons)

        filt = inc_raw.copy()
        if sel_months:
            filt = filt[filt["MonthN"].astype(str).isin(sel_months)]
        if sel_cat != "All":
            filt = filt[filt["Category"] == sel_cat]
        if sel_person != "Family":
            filt = filt[filt["Person"] == sel_person]

        if filt.empty:
            info_box("No records for selected filters.")
        else:
            total      = filt["Amount"].sum()
            month_sums = filt.groupby("MonthN")["Amount"].sum()
            avg_month  = month_sums.mean() if len(month_sums) > 0 else 0.0
            if pd.isna(avg_month): avg_month = total
            best_cat  = filt.groupby("Category")["Amount"].sum().idxmax()
            best_val  = filt.groupby("Category")["Amount"].sum().max()
            num_txn   = len(filt)

            k1,k2,k3,k4 = st.columns(4)
            k1.metric("Total Income",   fmt(total))
            k2.metric("Avg / Month",    fmt(avg_month))
            k3.metric("Top Category",   best_cat, fmt(best_val))
            k4.metric("Transactions",   str(num_txn))

            st.markdown("---")
            cl, cr = st.columns([1.5,1])

            with cl:
                sh("Monthly Income by Category")
                monthly = (filt.groupby(["MonthN","Category"])["Amount"]
                           .sum().reset_index())
                monthly["MonthStr"] = monthly["MonthN"].astype(str)
                monthly = monthly.sort_values("MonthN")
                cats    = monthly["Category"].unique()

                fig_bar = go.Figure()
                for i,cat in enumerate(cats):
                    sub = monthly[monthly["Category"]==cat]
                    fig_bar.add_trace(go.Bar(
                        x=sub["MonthStr"], y=sub["Amount"],
                        name=cat, marker_color=PIE_COLORS[i%len(PIE_COLORS)],
                        marker_line_width=0,
                        hovertemplate=f"<b>{cat}</b><br>%{{x}}<br>Rs.%{{y:,.0f}}<extra></extra>"))
                fig_bar.update_layout(**plot_layout(), height=310, barmode="stack")
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
                fig_pie.update_layout(**plot_layout(), height=310)
                st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown("---")
            sh("Monthly Totals Trend")
            m_total = (filt.groupby("MonthN")["Amount"].sum()
                       .reset_index().sort_values("MonthN"))
            m_total["MonthStr"] = m_total["MonthN"].astype(str)

            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=m_total["MonthStr"], y=m_total["Amount"],
                mode="lines+markers+text",
                line=dict(color=T["accent"],width=2.5),
                marker=dict(size=8, color=T["accent"]),
                text=m_total["Amount"].map(lambda v: fmt(v)),
                textposition="top center",
                textfont=dict(size=10, color=T["muted"]),
                fill="tozeroy",
                fillcolor="rgba(0,212,255,0.07)" if st.session_state.theme=="Dark" else "rgba(0,119,182,0.07)",
            ))
            fig_line.update_layout(**plot_layout(), height=250)
            st.plotly_chart(fig_line, use_container_width=True)

            st.markdown("---")
            sh("Person-wise Split")
            p1, p2 = st.columns(2)
            for col, person in zip([p1,p2], ["Gokul","Yamuna","Kavitha"]):
                psub = filt[filt["Person"]==person]
                ptotal = psub["Amount"].sum()
                pcat   = psub.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount",ascending=False)
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
                      <td class="mono" style="color:{color};font-weight:700">{fmt(r["Amount"])}</td>
                      <td class="mono" style="color:{T['muted']}">{r["Amount"]/ptotal*100:.1f}%</td>
                    </tr>""" for _,r in pcat.iterrows()) if ptotal>0 else ""
                    st.markdown(f"""
                    <div class="ft-wrap"><table class="ft">
                      <thead><tr><th>Category</th><th>Amount</th><th>Share</th></tr></thead>
                      <tbody>{rows}</tbody>
                    </table></div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  TAB 2 — ADD INCOME
# ════════════════════════════════════════════════════════
with tab2:
    st.markdown(f'<div style="max-width:680px">', unsafe_allow_html=True)
    sh("Add New Income Entry")

    c1, c2 = st.columns(2)
    person_add = c1.selectbox("Person *", ["Family","Gokul","Yamuna","Kavitha"], key="inc_person")
    category   = c2.selectbox("Category *", INCOME_CATEGORIES, key="inc_cat")

    c3, c4 = st.columns(2)
    amount    = c3.number_input("Amount (Rs.) *", min_value=0.0, step=100.0, key="inc_amt")
    inc_date  = c4.date_input("Date *", value=date.today(), key="inc_date")

    note = st.text_input("Note / Description", placeholder="e.g. October salary, Client payment", key="inc_note")

    if amount > 0:
        acc = T["accent"]
        st.markdown(f"""
        <div style='background:{acc}0f;border:1px solid {acc}33;border-radius:10px;
                    padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin:10px 0'>
          <div>
            <div style='font-size:11px;color:{T["muted"]};text-transform:uppercase;letter-spacing:.07em'>Entry Preview</div>
            <div style='font-size:13px;color:{T["text"]};margin-top:2px'>{person_add}  ·  {category}  ·  {str(inc_date)}</div>
          </div>
          <div style='font-size:24px;font-weight:800;color:{acc}'>{fmt(amount)}</div>
        </div>""", unsafe_allow_html=True)

    col_btn, col_clr = st.columns([1,3])
    save_clicked = col_btn.button("💾 Save Income", use_container_width=True, key="inc_save")

    if save_clicked:
        if amount <= 0:
            st.error("Enter a valid amount.")
        else:
            row = [str(inc_date), person_add, category, float(amount), note, str(datetime.now())]
            ok = save_row("Income_Ledger", row)
            if ok:
                st.success(f"✅ Saved! **{category}** — {fmt(amount)}")
                st.rerun()

    st.markdown("---")
    st.markdown(f"""
    <div class="info-box">
      <b>Google Sheet column format for Income:</b><br>
      <code>Date | Person | Category | Amount | Note | Timestamp</code><br><br>
      Categories available: {", ".join(INCOME_CATEGORIES)}
    </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  TAB 3 — RECORDS
# ════════════════════════════════════════════════════════
with tab3:
    if inc_raw.empty:
        info_box("No income records found.")
    else:
        sc1, sc2, sc3 = st.columns(3)
        s_person = sc1.selectbox("Person", ["All","Gokul","Yamuna","Kavitha",], key="rec_person")
        s_cat    = sc2.selectbox("Category", ["All"]+sorted(inc_raw["Category"].dropna().unique().tolist()), key="rec_cat")
        s_search = sc3.text_input("Search note", placeholder="keyword...", key="rec_search")

        view = inc_raw.copy().sort_values("Date", ascending=False)
        if s_person != "All":
            view = view[view["Person"]==s_person]
        if s_cat != "All":
            view = view[view["Category"]==s_cat]
        if s_search:
            view = view[view["Note"].str.contains(s_search,case=False,na=False)]

        st.caption(f"{len(view)} records  ·  Total: {fmt(view['Amount'].sum())}")

        rows = ""
        for _,r in view.iterrows():
            ds  = r["Date"].strftime("%d %b %Y") if pd.notna(r["Date"]) else ""
            pc  = T["accent"] if r.get("Person","")=="Gokul" else T["accent2"]
            rows += f"""
            <tr>
              <td class="mono" style="color:{T['muted']}">{ds}</td>
              <td><span class="badge" style="background:{pc}22;color:{pc}">{r.get("Person","")}</span></td>
              <td><span class="badge" style="background:{T['border']};color:{T['muted']}">{r.get("Category","")}</span></td>
              <td class="mono" style="font-weight:700;color:{T['green']}">{fmt(r["Amount"])}</td>
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
            view2 = inc_raw.copy().reset_index()
            selected = []
            for i,r in view2.iterrows():
                ds  = r["Date"].strftime("%d %b %Y") if pd.notna(r["Date"]) else "No date"
                lbl = f"{ds}  |  {r.get('Person','')}  |  {r.get('Category','')}  |  {fmt(r['Amount'])}"
                if st.checkbox(lbl, key=f"idel_{i}"):
                    selected.append(i+2)
            if selected:
                if st.button(f"Delete {len(selected)} record(s)", type="primary"):
                    try:
                        from utils.shared import get_sheet
                        ws = get_sheet().worksheet("Income_Ledger")
                        for rn in sorted(selected, reverse=True):
                            ws.delete_rows(rn)
                        st.cache_data.clear()
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")