import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Portfolio Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- STYLE ---------- #

st.markdown("""
<style>
[data-testid="stSidebar"] * {
    color: black !important;
    font-weight: 700;
}
h1, h2, h3 {
    color: #000000;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ---------- GOOGLE SHEETS CONNECTION ---------- #

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "credentials.json",
    scopes=scope
)

client = gspread.authorize(creds)
sheet = client.open("Family Portfolio System")

@st.cache_data
def load_data():
    investment = pd.DataFrame(
        sheet.worksheet("Investment_Ledger").get_all_records()
    )

    prices = pd.DataFrame(
        sheet.worksheet("Current_Prices").get_all_records()
    )

    return investment, prices


with st.spinner("Loading portfolio data..."):
    investment, prices = load_data()


# ---------- CREATE MAIN DATAFRAME ---------- #

if not investment.empty and not prices.empty:

    df = investment.merge(prices, on="Asset_Name", how="left")

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["Current_Price"] = pd.to_numeric(df["Current_Price"], errors="coerce")

    df["Invested"] = df["Quantity"] * df["Price"]
    df["Current_Value"] = df["Quantity"] * df["Current_Price"]

else:
    df = pd.DataFrame()


# ---------- SIDEBAR ---------- #

st.sidebar.title("Finance Dashboard")

page = st.sidebar.selectbox(
    "Navigate",
    ["Dashboard","Add Investment","Equity","Mutual Funds","Gold","Debt","NPS","Income","Expenses","Goals"]
)


# ---------- DASHBOARD ---------- #

if page == "Dashboard":

    st.title("📊 Personal Finance Dashboard")

    if df.empty:
        st.warning("No investment data available")
        st.stop()

    total_invested = df["Invested"].sum()
    portfolio_value = df["Current_Value"].sum()
    gain = portfolio_value - total_invested

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Net Worth", f"₹{portfolio_value:,.0f}")
    col2.metric("Portfolio Value", f"₹{portfolio_value:,.0f}")
    col3.metric("Total Invested", f"₹{total_invested:,.0f}")
    col4.metric("Total Gain", f"₹{gain:,.0f}")

    

    # ---------- ASSET ALLOCATION ---------- #

    colA, colB = st.columns(2)

    with colA:

        st.subheader("Asset Allocation")

        allocation = (
            df.groupby("Asset_Class")["Current_Value"]
            .sum()
            .reset_index()
        )

        fig = px.pie(
            allocation,
            names="Asset_Class",
            values="Current_Value",
            hole=0.5
        )

        st.plotly_chart(fig, use_container_width=True)

    with colB:

        st.subheader("Portfolio Summary")

        summary = (
            df.groupby("Asset_Class")
            .agg(
                Invested_Value=("Invested","sum"),
                Current_Value=("Current_Value","sum")
            )
            .reset_index()
        )

        summary["ROI %"] = (
            (summary["Current_Value"] - summary["Invested_Value"])
            / summary["Invested_Value"]
        ) * 100

        summary["ROI %"] = summary["ROI %"].round(2)

        st.dataframe(summary, use_container_width=True)

    # ---------- CATEGORY HOLDINGS ---------- #

    st.subheader("Category Holdings")

    category = st.selectbox(
        "Select Category",
        sorted(df["Asset_Class"].unique())
    )

    filtered = df[df["Asset_Class"] == category]

    table = (
        filtered.groupby("Asset_Name")
        .agg(
            Invested=("Invested","sum"),
            Current_Value=("Current_Value","sum")
        )
        .reset_index()
    )

    table["ROI %"] = (
        (table["Current_Value"] - table["Invested"])
        / table["Invested"]
    ) * 100

    table["ROI %"] = table["ROI %"].round(2)

    st.dataframe(table, use_container_width=True)
# ---------- PORTFOLIO GROWTH ---------- #

    st.subheader("Portfolio Growth")

    try:
        df["Date"] = pd.to_datetime(df["Date"])

        growth = (
            df.sort_values("Date")
            .groupby("Date")["Invested"]
            .sum()
            .cumsum()
            .reset_index()
        )

        fig_growth = px.line(
            growth,
            x="Date",
            y="Invested",
            markers=True
        )

        st.plotly_chart(fig_growth, use_container_width=True)

    except:
        st.info("Add valid Date column to see growth chart")

elif page == "Add Investment":

    st.title("Add Investment")

    date = st.date_input("Date")

    asset_class = st.selectbox(
        "Asset Class",
        ["Equity","Mutual Fund","Gold","Debt","NPS"]
    )

    category = st.text_input("Category")

    asset_name = st.text_input("Asset Name")

    quantity = st.number_input("Quantity", min_value=0.0)

    price = st.number_input("Purchase Price", min_value=0.0)

    if st.button("Save Investment"):

        new_row = [
            str(date),
            asset_class,
            category,
            asset_name,
            quantity,
            price
        ]

        sheet.worksheet("Investment_Ledger").append_row(new_row)

        st.success("Investment added successfully")

# ---------- EQUITY PAGE ---------- #

elif page == "Equity":

    st.title("Equity Portfolio")

    equity = df[df["Asset_Class"] == "Equity"]

    st.dataframe(equity, use_container_width=True)

    st.metric("Total Equity Value", f"₹{equity['Current_Value'].sum():,.0f}")


# ---------- MUTUAL FUNDS ---------- #

elif page == "Mutual Funds":

    st.title("Mutual Fund Portfolio")

    mf = df[df["Asset_Class"] == "Mutual Fund"]

    st.dataframe(mf, use_container_width=True)

    st.metric("Total MF Value", f"₹{mf['Current_Value'].sum():,.0f}")


# ---------- GOLD ---------- #

elif page == "Gold":

    st.title("Gold Holdings")

    gold = df[df["Asset_Class"] == "Gold"]

    st.dataframe(gold, use_container_width=True)

    st.metric("Total Gold Value", f"₹{gold['Current_Value'].sum():,.0f}")


# ---------- DEBT ---------- #

elif page == "Debt":

    st.title("Debt Instruments")

    debt = df[df["Asset_Class"] == "Debt"]

    st.dataframe(debt, use_container_width=True)

    st.metric("Total Debt Value", f"₹{debt['Current_Value'].sum():,.0f}")


# ---------- NPS ---------- #

elif page == "NPS":

    st.title("NPS Portfolio")

    try:
        nps = pd.DataFrame(
            sheet.worksheet("NPS_Ledger").get_all_records()
        )

        st.dataframe(nps, use_container_width=True)

    except:
        st.warning("NPS sheet not found")


# ---------- INCOME ---------- #

elif page == "Income":

    st.title("Income Tracker")

    try:
        income = pd.DataFrame(
            sheet.worksheet("Income_Ledger").get_all_records()
        )

        st.dataframe(income, use_container_width=True)

    except:
        st.warning("Income sheet not found")


# ---------- EXPENSES ---------- #

elif page == "Expenses":

    st.title("Expense Tracker")

    try:
        expenses = pd.DataFrame(
            sheet.worksheet("Expenditure_Ledger").get_all_records()
        )

        st.dataframe(expenses, use_container_width=True)

    except:
        st.warning("Expense sheet not found")


# ---------- GOALS ---------- #

elif page == "Goals":

    st.title("Financial Goals")

    try:
        goals = pd.DataFrame(
            sheet.worksheet("Goals").get_all_records()
        )

        st.dataframe(goals, use_container_width=True)

    except:
        st.warning("Goals sheet not found")