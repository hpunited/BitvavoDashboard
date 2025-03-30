import streamlit as st
from streamlit_autorefresh import st_autorefresh
import threading
import websocket
import json
import pandas as pd
import altair as alt
import uuid
from shared_data import trade_data

# ✅ Pagina setup
st.set_page_config(page_title="Bitvavo Live Trades", layout="centered")
st_autorefresh(interval=1000, key="refresh")

st.title("📡 Bitvavo Live Trades")

# 🎯 Unieke sessie-ID (blijft geldig zolang tab open is)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
my_id = st.session_state.session_id

# Coin-selectie per gebruiker
selected_pair = st.selectbox("Kies een coin:", ["BTC-EUR", "ETH-EUR", "SOL-EUR", "ADA-EUR", "XRP-EUR"])

# ✅ WebSocket functie
def start_websocket(pair, session_id):
    def on_message(ws, message):
        data = json.loads(message)
        if "event" in data and data["event"] == "trade":
            timestamp = pd.to_datetime(data["timestamp"], unit="ms")
            price = float(data["price"])
            amount = float(data["amount"])
            side = data["side"]

            with trade_data["lock"]:
                if session_id not in trade_data["sessions"]:
                    trade_data["sessions"][session_id] = {"trades": [], "total": 0.0}

                trades = trade_data["sessions"][session_id]["trades"]
                trades.insert(0, {
                    "Time": timestamp,
                    "Price": price,
                    "Amount": amount,
                    "Side": side
                })
                trade_data["sessions"][session_id]["total"] += amount

                if len(trades) > 500:
                    trade_data["sessions"][session_id]["trades"] = trades[:500]

    def on_open(ws):
        ws.send(json.dumps({
            "action": "subscribe",
            "channels": [{"name": "trades", "markets": [pair]}]
        }))

    ws = websocket.WebSocketApp(
        "wss://ws.bitvavo.com/v2/",
        on_open=on_open,
        on_message=on_message
    )
    ws.run_forever()

# ✅ Start/Stop knoppen
col1, col2 = st.columns(2)

with col1:
    if st.button("▶️ Start Streaming Trades"):
        with trade_data["lock"]:
            if my_id not in trade_data["active_sessions"]:
                if len(trade_data["active_sessions"]) < 3:
                    trade_data["active_sessions"].add(my_id)
                    trade_data["sessions"][my_id] = {"trades": [], "total": 0.0}
                    st.session_state.streaming = True
                    threading.Thread(target=lambda: start_websocket(selected_pair, my_id), daemon=True).start()
                    st.success(f"Streaming gestart voor {selected_pair}")
                else:
                    st.error("❌ Maximum aantal actieve gebruikers bereikt.")
            else:
                st.info("Je bent al verbonden.")

with col2:
    if st.button("⛔ Stop Streaming"):
        with trade_data["lock"]:
            trade_data["active_sessions"].discard(my_id)
            trade_data["sessions"].pop(my_id, None)
        st.session_state.streaming = False
        st.warning("Streaming gestopt.")

# ✅ Data ophalen en tonen
with trade_data["lock"]:
    session_data = trade_data["sessions"].get(my_id, {"trades": [], "total": 0.0})
    trades_copy = session_data["trades"][:]
    total_copy = session_data["total"]

if trades_copy:
    df = pd.DataFrame(trades_copy)
    st.markdown(f"**Totaal verhandeld volume:** {total_copy:.6f}")
    st.markdown("### Laatste 5 trades")
    st.dataframe(df.head(5), use_container_width=True)

    # 📈 Prijs grafiek
    st.markdown("### 📈 Live koers en volume")

    price_chart = alt.Chart(df).mark_line().encode(
        x=alt.X("Time:T", title="Tijd"),
        y=alt.Y("Price:Q", title="Prijs", scale=alt.Scale(zero=False)),
        tooltip=["Time:T", "Price:Q", "Amount:Q"]
    ).properties(height=300)

    # 📊 Volume grafiek
    volume_chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Time:T"),
        y=alt.Y("Amount:Q", title="Volume"),
        color=alt.condition(
            alt.datum.Side == "buy",
            alt.value("green"),
            alt.value("red")
        ),
        tooltip=["Time:T", "Amount:Q", "Side:N"]
    ).properties(height=100)

    combined = alt.vconcat(price_chart, volume_chart).resolve_scale(x="shared")
    st.altair_chart(combined, use_container_width=True)
else:
    if st.session_state.get("streaming", False):
        st.info("Trades worden geladen...")
    else:
        st.info("Nog geen trades ontvangen.")
