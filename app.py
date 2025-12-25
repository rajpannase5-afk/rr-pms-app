import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="RR PMS Pvt Ltd | PMS Dashboard",
    page_icon="📊",
    layout="wide"
)

# ================= CSS =================
st.markdown("""
<style>
body { background-color:#0E1117; }
.block-container { padding-top:1rem; }
.metric-card {
    background:#161B22;
    padding:18px;
    border-radius:14px;
    text-align:center;
}
.metric-title { color:#9CA3AF;font-size:13px; }
.metric-value { font-size:26px;font-weight:700;color:#22C55E; }
</style>
""", unsafe_allow_html=True)

# ================= DATABASE =================
conn = sqlite3.connect("trades.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT,
    symbol TEXT,
    entry REAL,
    exit REAL,
    qty INTEGER,
    note TEXT
)
""")
conn.commit()

def load_data():
    return pd.read_sql("SELECT * FROM trades ORDER BY trade_date", conn)

def add_trade(d,s,e,x,q,n):
    c.execute(
        "INSERT INTO trades (trade_date,symbol,entry,exit,qty,note) VALUES (?,?,?,?,?,?)",
        (d,s.upper(),e,x,q,n)
    )
    conn.commit()

def update_trade(i,d,s,e,x,q,n):
    c.execute("""
        UPDATE trades SET trade_date=?, symbol=?, entry=?, exit=?, qty=?, note=?
        WHERE id=?
    """,(d,s.upper(),e,x,q,n,i))
    conn.commit()

def delete_trade(i):
    c.execute("DELETE FROM trades WHERE id=?", (i,))
    conn.commit()

# ================= HEADER =================
st.markdown("""
<div style="background:#161B22;padding:22px;border-radius:16px;">
<h1 style="margin:0;color:#F8FAFC;">RR PMS Pvt Ltd</h1>
<p style="color:#9CA3AF;">Professional Portfolio Management Services</p>
</div>
""", unsafe_allow_html=True)

# ================= ADD TRADE =================
with st.expander("➕ Add Trade"):
    with st.form("add"):
        d = st.date_input("Date", date.today())
        s = st.text_input("Symbol")
        q = st.number_input("Qty",1,step=1)
        e = st.number_input("Entry",0.0)
        x = st.number_input("Exit",0.0)
        n = st.text_area("Trade Note")
        if st.form_submit_button("Add Trade"):
            add_trade(str(d),s,e,x,q,n)
            st.success("Trade Added")

# ================= LOAD DATA =================
df = load_data()

if df.empty:
    st.info("No trades yet. Please add trades.")
    st.stop()

df["trade_date"] = pd.to_datetime(df["trade_date"])
df["PnL"] = (df["exit"] - df["entry"]) * df["qty"]
df["Capital"] = abs(df["entry"] * df["qty"])
df["Return"] = np.where(df["Capital"] != 0, df["PnL"]/df["Capital"], 0)

initial_capital = df["Capital"].iloc[0]

# ================= SORTINO =================
returns = df["Return"]
downside = returns[returns < 0]
sortino = returns.mean() / downside.std() if len(downside)>0 else 0

# ================= OVERVIEW =================
total_pnl = df["PnL"].sum()
equity = initial_capital + df["PnL"].cumsum()
drawdown = (equity - equity.cummax()) / equity.cummax() * 100

c1,c2,c3,c4,c5 = st.columns(5)

def card(c,t,v):
    c.markdown(
        f"<div class='metric-card'><div class='metric-title'>{t}</div>"
        f"<div class='metric-value'>{v}</div></div>",
        unsafe_allow_html=True
    )

card(c1,"Total PnL",f"₹ {round(total_pnl,2)}")
card(c2,"Return %",round((total_pnl/initial_capital)*100,2))
card(c3,"Max Drawdown %",round(drawdown.min(),2))
card(c4,"Hit Ratio %",round((df['PnL']>0).mean()*100,2))
card(c5,"Sortino Ratio",round(sortino,2))

st.line_chart(equity)
# =============== BENCHMARK (SAFE) =================
start, end = equity.index.min(), equity.index.max()

nifty = yf.download("^NSEI", start=start, end=end, progress=False)

if nifty.empty or len(equity) == 0:
    st.warning("Benchmark comparison not available yet")
else:
    nifty_close = nifty["Close"].dropna()

    if len(nifty_close) > 0:
        pms_norm = equity / equity.iloc[0]
        nifty_norm = nifty_close / nifty_close.iloc[0]

        pms_norm = pms_norm.reindex(nifty_norm.index, method="ffill")

        comp = pd.DataFrame({
            "RR PMS": pms_norm,
            "NIFTY 50": nifty_norm
        }).dropna()

        st.line_chart(comp)
