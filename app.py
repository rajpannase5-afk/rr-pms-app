import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from supabase import create_client
import yfinance as yf

# ================== CONFIG ==================
st.set_page_config(page_title="RR PMS Dashboard", layout="wide")

# ================== SUPABASE ==================

SUPABASE_URL = "https://ywbtpcfhwritehcyli.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...."
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================== HELPERS ==================
def fetch_table(name):
    res = supabase.table(name).select("*").execute()
    return pd.DataFrame(res.data)

def insert_row(table, data):
    supabase.table(table).insert(data).execute()

def update_row(table, row_id, data):
    supabase.table(table).update(data).eq("id", row_id).execute()

def delete_row(table, row_id):
    supabase.table(table).delete().eq("id", row_id).execute()

# ================== TITLE ==================
st.title("📊 RR PMS – Performance Dashboard")

# ================== ADD TRADE ==================
st.subheader("➕ Add Trade")

with st.form("add_trade"):
    col1, col2, col3 = st.columns(3)
    with col1:
        date = st.date_input("Date")
        symbol = st.text_input("Symbol")
    with col2:
        qty = st.number_input("Quantity", min_value=1)
        entry = st.number_input("Entry Price", min_value=0.0)
    with col3:
        exit_price = st.number_input("Exit Price", min_value=0.0)
        fees = st.number_input("Charges", min_value=0.0)

    submitted = st.form_submit_button("Add Trade")

    if submitted:
        pnl = (exit_price - entry) * qty - fees
        insert_row("trades", {
            "date": str(date),
            "symbol": symbol,
            "qty": qty,
            "entry": entry,
            "exit": exit_price,
            "fees": fees,
            "pnl": pnl
        })
        st.success("Trade Added Successfully")

# ================== LOAD TRADES ==================
st.subheader("📋 Trades")

trades = fetch_table("trades")

if trades.empty:
    st.info("No trades yet")
    st.stop()

trades["date"] = pd.to_datetime(trades["date"])
trades = trades.sort_values("date")

st.dataframe(trades, use_container_width=True)

# ================== EDIT / DELETE ==================
st.subheader("✏️ Edit / ❌ Delete Trade")

trade_ids = trades["id"].tolist()
selected_id = st.selectbox("Select Trade ID", trade_ids)

selected_trade = trades[trades["id"] == selected_id].iloc[0]

with st.form("edit_trade"):
    col1, col2, col3 = st.columns(3)
    with col1:
        e_qty = st.number_input("Quantity", value=int(selected_trade.qty))
        e_entry = st.number_input("Entry", value=float(selected_trade.entry))
    with col2:
        e_exit = st.number_input("Exit", value=float(selected_trade.exit))
        e_fees = st.number_input("Fees", value=float(selected_trade.fees))
    with col3:
        action = st.radio("Action", ["Update", "Delete"])

    confirm = st.form_submit_button("Confirm")

    if confirm:
        if action == "Update":
            pnl = (e_exit - e_entry) * e_qty - e_fees
            update_row("trades", selected_id, {
                "qty": e_qty,
                "entry": e_entry,
                "exit": e_exit,
                "fees": e_fees,
                "pnl": pnl
            })
            st.success("Trade Updated")
        else:
            delete_row("trades", selected_id)
            st.warning("Trade Deleted")

# ================== METRICS ==================
st.subheader("📈 Performance Metrics")

trades["cum_pnl"] = trades["pnl"].cumsum()
equity = trades["cum_pnl"]

total_pnl = trades["pnl"].sum()
win_rate = (trades["pnl"] > 0).mean() * 100
max_dd = (equity - equity.cummax()).min()

returns = trades["pnl"]
sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() != 0 else 0
downside = returns[returns < 0]
sortino = returns.mean() / downside.std() * np.sqrt(252) if downside.std() != 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total PnL", f"₹{total_pnl:,.0f}")
col2.metric("Win Rate", f"{win_rate:.2f}%")
col3.metric("Max Drawdown", f"₹{max_dd:,.0f}")
col4.metric("Sharpe", f"{sharpe:.2f}")
col5.metric("Sortino", f"{sortino:.2f}")

# ================== EQUITY CURVE ==================
st.subheader("📉 Equity Curve")
st.line_chart(equity)

# ================== BENCHMARK ==================
st.subheader("📊 Benchmark Comparison (NIFTY)")

try:
    start = trades["date"].min()
    end = trades["date"].max()

    nifty = yf.download("^NSEI", start=start, end=end, progress=False)

    if nifty.empty:
        st.warning("Benchmark temporarily unavailable")
    else:
        nifty = nifty["Close"]
        pms_norm = equity / equity.iloc[0]
        nifty_norm = nifty / nifty.iloc[0]
        pms_norm = pms_norm.reindex(nifty_norm.index, method="ffill")

        st.line_chart(pd.DataFrame({
            "RR PMS": pms_norm,
            "NIFTY": nifty_norm
        }))

except Exception:
    st.warning("Benchmark temporarily unavailable")

# ================== FOOTER ==================
st.caption("Data stored permanently in Supabase • Trade Edit/Delete SAFE • RLS Enabled")

