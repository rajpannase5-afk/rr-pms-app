import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date
from supabase import create_client

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="RR PMS Pvt Ltd | PMS Dashboard",
    page_icon="📊",
    layout="wide"
)

# ================= SUPABASE =================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
hr { background:#222;height:1px;border:none; }
</style>
""", unsafe_allow_html=True)

# ================= DB FUNCTIONS =================
def load_trades():
    data = supabase.table("trades").select("*").order("trade_date").execute()
    return pd.DataFrame(data.data)

def add_trade(d,s,e,x,q,n):
    supabase.table("trades").insert({
        "trade_date": str(d),
        "symbol": s.upper(),
        "entry": e,
        "exit": x,
        "qty": q,
        "note": n
    }).execute()

def update_trade(i,d,s,e,x,q,n):
    supabase.table("trades").update({
        "trade_date": str(d),
        "symbol": s.upper(),
        "entry": e,
        "exit": x,
        "qty": q,
        "note": n
    }).eq("id", i).execute()

def delete_trade(i):
    supabase.table("trades").delete().eq("id", i).execute()

# ================= HEADER =================
st.markdown("""
<div style="background:#161B22;padding:22px;border-radius:16px;">
<h1 style="margin:0;color:#F8FAFC;">RR PMS Pvt Ltd</h1>
<p style="color:#9CA3AF;">Professional Portfolio Management Services</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ================= ADD TRADE =================
with st.expander("➕ Add Trade"):
    with st.form("add"):
        c1,c2,c3 = st.columns(3)
        d = c1.date_input("Date", date.today())
        s = c2.text_input("Symbol")
        q = c3.number_input("Qty",1,step=1)
        e = st.number_input("Entry",0.0)
        x = st.number_input("Exit",0.0)
        n = st.text_area("Trade Note")
        if st.form_submit_button("Add Trade"):
            add_trade(d,s,e,x,q,n)
            st.success("Trade Added")

# ================= LOAD DATA =================
df = load_trades()

if not df.empty:
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["PnL"] = (df["exit"] - df["entry"]) * df["qty"]
    df["Capital"] = abs(df["entry"] * df["qty"])
    df["Return"] = df["PnL"] / df["Capital"]

    initial_capital = df["Capital"].iloc[0]

    # ================= SORTINO =================
    target = 0
    downside = df[df["Return"] < target]["Return"]
    if len(downside) > 0:
        downside_dev = np.sqrt(((downside - target) ** 2).mean())
        sortino = (df["Return"].mean() - target) / downside_dev
    else:
        sortino = np.nan

    tab1,tab2,tab3,tab4 = st.tabs([
        "📊 Overview",
        "📅 Stock-wise",
        "🔥 Risk",
        "📈 Benchmark"
    ])

    # ================= OVERVIEW =================
    with tab1:
        total_pnl = df["PnL"].sum()
        equity = initial_capital + df["PnL"].cumsum()
        drawdown = (equity - equity.cummax()) / equity.cummax() * 100

        c1,c2,c3,c4 = st.columns(4)

        def card(c,t,v):
            c.markdown(
                f"<div class='metric-card'><div class='metric-title'>{t}</div>"
                f"<div class='metric-value'>{v}</div></div>",
                unsafe_allow_html=True
            )

        card(c1,"Total PnL",round(total_pnl,2))
        card(c2,"Max DD %",round(drawdown.min(),2))
        card(c3,"Hit Ratio %",round((df["PnL"]>0).mean()*100,2))
        card(c4,"Sortino Ratio",round(sortino,2))

        st.line_chart(equity)

    # ================= STOCK =================
    with tab2:
        perf = df.groupby("symbol").agg(
            PnL=("PnL","sum"),
            Capital=("Capital","sum")
        )
        perf["Return %"] = perf["PnL"]/perf["Capital"]*100
        st.dataframe(perf.round(2), use_container_width=True)

    # ================= RISK =================
    with tab3:
        st.line_chart(drawdown)

    # ================= BENCHMARK =================
    with tab4:
        try:
            daily = df.groupby("trade_date")["PnL"].sum()
            equity = initial_capital + daily.cumsum()

            nifty = yf.download("^NSEI", start=equity.index.min(),
                                end=equity.index.max(),
                                progress=False)["Close"]

            comp = pd.DataFrame({
                "RR PMS": equity / equity.iloc[0],
                "NIFTY": nifty / nifty.iloc[0]
            }).dropna()

            st.line_chart(comp)
        except:
            st.warning("Benchmark temporarily unavailable")

    # ================= EDIT / DELETE =================
    st.markdown("### ✏️ Edit / Delete Trade")
    trade_id = st.selectbox("Trade ID", df["id"])
    t = df[df["id"] == trade_id].iloc[0]

    with st.form("edit"):
        d = st.date_input("Date", t["trade_date"])
        s = st.text_input("Symbol", t["symbol"])
        q = st.number_input("Qty",1,value=int(t["qty"]))
        e = st.number_input("Entry",value=float(t["entry"]))
        x = st.number_input("Exit",value=float(t["exit"]))
        n = st.text_area("Note", t["note"])
        col1,col2 = st.columns(2)
        if col1.form_submit_button("Update"):
            update_trade(trade_id,d,s,e,x,q,n)
            st.success("Updated")
        if col2.form_submit_button("Delete"):
            delete_trade(trade_id)
            st.warning("Deleted")

else:
    st.info("No trades yet")

st.markdown("""
<hr>
<p style="text-align:center;color:#6B7280;font-size:12px;">
© RR PMS Pvt Ltd | Confidential PMS System
</p>
""", unsafe_allow_html=True)
