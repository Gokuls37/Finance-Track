import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from datetime import date, datetime
from utils.shared import (
    inject_css, render_sidebar, get_data, get_theme, sh, fmt, fmt_nav,
    save_row, info_box, INVESTMENT_CATS, get_sheet
)

st.set_page_config(page_title="Add Investment – Finance Track", page_icon="➕",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
T = get_theme()
data = get_data()
render_sidebar("Add Investment")

st.title("➕ Add Investment / NPS")

# ── Tab: Investment vs NPS ──
tab_inv, tab_nps, tab_div = st.tabs(["📈  Investment / MF / Gold / Debt", "🎖️  NPS Contribution", "💰  Dividend Income"])

# ══════════════════════════════════════════════════════
#  TAB 1 — REGULAR INVESTMENT
# ══════════════════════════════════════════════════════
with tab_inv:
    sh("New Investment Transaction")

    c1, c2 = st.columns(2)
    # Filter out NPS from this tab (NPS has its own tab)
    inv_cats = {k:v for k,v in INVESTMENT_CATS.items() if k != "NPS"}
    person    = c1.selectbox("Person *", ["Gokul","Yamuna","Kavitha"], key="ai_p")
    asset_cls = c2.selectbox("Asset Class *", list(inv_cats.keys()), key="ai_ac")

    with st.form("add_inv_form", clear_on_submit=True):
        c3, c4 = st.columns(2)
        cat = c3.selectbox("Category *",    inv_cats[asset_cls], key="ai_cat")
        tt  = c4.selectbox("Transaction *", ["BUY","SELL","SIP","SWITCH"], key="ai_tt")

        aname = st.text_input("Asset Name *", placeholder="e.g. HDFC Bank, EDELWEISS NLM250", key="ai_name")

        c_tag, c_tick = st.columns(2)
        tag    = c_tag.text_input("Tag", placeholder="e.g. Large Cap, IT", key="ai_tag")
        ticker = c_tick.text_input(
            "Ticker / ISIN (for auto price)",
            placeholder="e.g. HDFCBANK  or  INF754K01NR9",
            help="NSE symbol (HDFCBANK), ISIN (INF754K01NR9), or mfapi scheme code (119551). Leave blank for auto-mapping.",
            key="ai_tick"
        )

        c5, c6, c7 = st.columns(3)
        qty   = c5.number_input("Quantity / Units *", min_value=0.0, step=0.001, format="%.6f", key="ai_qty")
        price = c6.number_input("Price / NAV *",      min_value=0.0, step=0.01,  format="%.4f", key="ai_price")
        idate = c7.date_input("Date *", value=date.today(), key="ai_date")
        notes = st.text_area("Notes", height=70, key="ai_notes")

        total = qty * price
        if total > 0:
            acc = T["accent"]
            st.markdown(f"""
            <div style='background:{acc}0f;border:1px solid {acc}33;border-radius:10px;
                        padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin:8px 0'>
              <div>
                <div style='font-size:11px;color:{T["muted"]};text-transform:uppercase'>Total Value</div>
                <div style='font-size:12px;color:{T["muted"]};margin-top:2px'>{person} · {asset_cls} · {cat} · {tt}</div>
              </div>
              <div style='font-size:26px;font-weight:800;color:{acc}'>{fmt(total)}</div>
            </div>""", unsafe_allow_html=True)

        sub = st.form_submit_button("💾 Save to Investment_Ledger", use_container_width=True)

    if sub:
        if not aname or qty == 0 or price == 0:
            st.error("Asset Name, Quantity and Price / NAV are required.")
        else:
            row = [person, asset_cls, cat, aname, tag, ticker, tt,
                   qty, price, str(idate), notes, str(datetime.now())]
            ok = save_row("Investment_Ledger", row)
            if ok:
                st.success(f"✅ Saved to Investment_Ledger! **{aname}** · {fmt(total)}")
                st.balloons()

    st.markdown(f"""
    <div class="info-box" style="margin-top:16px">
      <b>Investment_Ledger columns:</b>
      <code>Person | Asset_Class | Category | Asset_Name | Tag | Ticker | Transaction_Type | Quantity | Price | Date | Notes | Timestamp</code><br><br>
      <b>🔄 Current Prices:</b> Add a <b>Current_Prices</b> sheet with <code>Asset_Name | Current_Price</code>.
      For NSE stocks use Google Finance formula in Current_Price column:<br>
      <code>=GOOGLEFINANCE("NSE:HDFCBANK","price")</code><br>
      For MF NAV: <code>=GOOGLEFINANCE("MUTF_IN:EDEL_NIF_LAR_MID_250_IDFG","nav")</code>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
#  TAB 2 — NPS CONTRIBUTION
# ══════════════════════════════════════════════════════
with tab_nps:
    sh("NPS Contribution Entry")

    st.markdown(f"""
    <div class="info-box">
      Saves to <b>NPS_Ledger</b> sheet with columns:
      <code>Date | Person | Tier | Fund_Manager | Asset_Class | Amount | NAV | Units | Current_NAV | Timestamp</code><br>
      <b>Current_NAV</b> is auto-filled using Google Finance formula in the sheet.
    </div>""", unsafe_allow_html=True)

    with st.form("add_nps_form", clear_on_submit=True):
        n1, n2 = st.columns(2)
        nps_person  = n1.selectbox("Person *", ["Gokul","Yamuna","Kavitha"], key="nps_p")
        nps_tier    = n2.selectbox("Tier *",   ["Tier I","Tier II"], key="nps_tier")

        n3, n4 = st.columns(2)
        nps_fm = n3.selectbox("Fund Manager *", [
            "SBI Pension","LIC Pension","UTI Retirement","HDFC Pension",
            "ICICI Pru Pension","Kotak Pension","Aditya Birla Sun Life Pension","Axis Pension"
        ], key="nps_fm")
        nps_ac = n4.selectbox("Asset Class *", [
            "Equity (E)","Corporate Bond (C)","Government Securities (G)","Alternative Assets (A)"
        ], key="nps_ac")

        n5, n6, n7 = st.columns(3)
        nps_amount = n5.number_input("Amount (Rs.) *", min_value=0.0, step=100.0, key="nps_amt")
        nps_nav    = n6.number_input("NAV at Purchase *", min_value=0.0, step=0.01, format="%.4f", key="nps_nav")
        nps_date   = n7.date_input("Date *", value=date.today(), key="nps_date")

        # Calculate units
        nps_units = nps_amount / nps_nav if nps_nav > 0 else 0.0

        if nps_amount > 0 and nps_nav > 0:
            st.markdown(f"""
            <div style='background:{T["accent2"]}0f;border:1px solid {T["accent2"]}33;border-radius:10px;
                        padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin:8px 0'>
              <div>
                <div style='font-size:11px;color:{T["muted"]};text-transform:uppercase'>Units Allotted</div>
                <div style='font-size:12px;color:{T["muted"]};margin-top:2px'>{nps_person} · {nps_tier} · {nps_fm} · {nps_ac}</div>
              </div>
              <div>
                <div style='font-size:22px;font-weight:800;color:{T["accent2"]}'>{nps_units:.4f} units</div>
                <div style='font-size:13px;color:{T["muted"]};text-align:right'>@ NAV {fmt_nav(nps_nav)}</div>
              </div>
            </div>""", unsafe_allow_html=True)

        nps_submit = st.form_submit_button("💾 Save to NPS_Ledger", use_container_width=True)

    if nps_submit:
        if nps_amount == 0 or nps_nav == 0:
            st.error("Amount and NAV are required.")
        else:
            # Current_NAV column: save empty — Google Finance formula fills it in sheet
            nps_row = [
                str(nps_date), nps_person, nps_tier, nps_fm, nps_ac,
                float(nps_amount), float(nps_nav), round(nps_units, 6),
                "",   # Current_NAV — filled by GOOGLEFINANCE formula in sheet
                str(datetime.now())
            ]
            ok = save_row("NPS_Ledger", nps_row)
            if ok:
                st.success(f"✅ Saved to NPS_Ledger! {nps_units:.4f} units @ {fmt_nav(nps_nav)}")
                st.info("💡 Add a GOOGLEFINANCE formula in the Current_NAV column of your NPS_Ledger sheet to auto-update NAV.")

    st.markdown("---")
    sh("Google Finance Formula for NPS Current NAV")
    st.markdown(f"""
    <div class="info-box">
      In your <b>NPS_Ledger</b> sheet, add this formula in the <b>Current_NAV column (I2)</b> and drag down:<br><br>
      <b>SBI Pension Equity:</b> NAV is published daily on NSDL/NPSTRUST website — no direct Google Finance support.<br>
      Use this workaround — import NAV from NPSTRUST:<br>
      <code>=IMPORTXML("https://www.npstrust.org.in/content/pension-fund-regulatory-and-development-authority","//table")</code><br><br>
      <b>Simpler approach:</b> Keep a manual <code>Current_NAV</code> column and update it weekly from
      <a href="https://www.npstrust.org.in" target="_blank">npstrust.org.in</a> or your NPS app.
      The dashboard reads whatever value you put there.
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
#  TAB 3 — DIVIDEND
# ══════════════════════════════════════════════════════
with tab_div:
    sh("Log Dividend / Interest Received")

    st.markdown(f"""
    <div class="info-box">
      Saves to <b>Dividend_Ledger</b> sheet with columns:
      <code>Date | Person | Asset_Name | Asset_Class | Dividend_Type | Amount | Tax_Deducted | Net_Amount | Note | Timestamp</code>
    </div>""", unsafe_allow_html=True)

    with st.form("add_div_form", clear_on_submit=True):
        d1, d2 = st.columns(2)
        div_person  = d1.selectbox("Person *", ["Gokul","Yamuna","Kavitha","Family"], key="div_p")
        div_asset   = d2.text_input("Asset Name *", placeholder="e.g. COAL INDIA, HDFC Bank FD", key="div_asset")

        d3, d4 = st.columns(2)
        div_class = d3.selectbox("Asset Class *", ["Equity","Mutual Fund","Debt","NPS","Other"], key="div_cls")
        div_type  = d4.selectbox("Dividend Type *", [
            "Equity Dividend","Mutual Fund Dividend","FD Interest",
            "Bond Interest","NPS Partial Withdrawal","SGB Interest","Other"
        ], key="div_type")

        d5, d6, d7 = st.columns(3)
        div_gross = d5.number_input("Gross Amount (Rs.) *", min_value=0.0, step=10.0, key="div_gross")
        div_tds   = d6.number_input("TDS Deducted (Rs.)",   min_value=0.0, step=1.0,  key="div_tds")
        div_date  = d7.date_input("Date *", value=date.today(), key="div_date")
        div_note  = st.text_input("Note", placeholder="e.g. Q3 interim dividend, FD maturity", key="div_note")

        div_net = div_gross - div_tds
        if div_gross > 0:
            st.markdown(f"""
            <div style='background:{T["green"]}0f;border:1px solid {T["green"]}33;border-radius:10px;
                        padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin:8px 0'>
              <div>
                <div style='font-size:11px;color:{T["muted"]};text-transform:uppercase'>Net Dividend</div>
                <div style='font-size:12px;color:{T["muted"]};margin-top:2px'>{div_asset} · {div_type} · TDS {fmt(div_tds)}</div>
              </div>
              <div style='font-size:26px;font-weight:800;color:{T["green"]}'>{fmt(div_net)}</div>
            </div>""", unsafe_allow_html=True)

        div_submit = st.form_submit_button("💾 Save to Dividend_Ledger", use_container_width=True)

    if div_submit:
        if div_gross == 0 or not div_asset:
            st.error("Asset Name and Amount are required.")
        else:
            div_row = [
                str(div_date), div_person, div_asset, div_class, div_type,
                float(div_gross), float(div_tds), float(div_net),
                div_note, str(datetime.now())
            ]
            ok = save_row("Dividend_Ledger", div_row)
            if ok:
                st.success(f"✅ Saved! {div_asset} dividend — Net {fmt(div_net)}")
