import streamlit as st
from streamlit_autorefresh import st_autorefresh
import threading
import websocket
import json
import pandas as pd
import altair as alt
from shared_data import trade_data

# ✅ Pagina setup
st.set_page_config(page_title="Bitvavo Live Trades", layout="centered")
st_autorefresh(interval=1000, key="refresh")

st.title("📡 Bitvavo Live Trades")

# Coin selectie
selected_pair = st.selectbox("Kies een coin:", ["BTC-EUR", "ETH-EUR", "SOL-EUR", "ADA-EUR", "XRP-EUR"])

# ✅ WebSocket functie (bovenaan zetten!)
def start_websocket(pair):
    def on_message(ws, message):
        if not trade_data["is_streaming"]:
            print("🛑 Streaming gestopt — WebSocket sluit")
            ws.close()
            return

        data = json.loads(message)
        if "event" in data and data["event"] == "trade":
            timestamp = pd.to_datetime(data["timestamp"], unit="ms")
            price = float(data["price"])
            amount = float(data["amount"])
            side = data["side"]

            with trade_data["lock"]:
                trade_data["trades"].insert(0, {
                    "Time": timestamp,
                    "Price": price,
                    "Amount": amount,
                    "Side": side
                })
                trade_data["total"] += amount
                if len(trade_data["trades"]) > 500:
                    trade_data["trades"] = trade_data["trades"][:500]

    def on_open(ws):
        print("✅ WebSocket verbonden!")
        ws.send(json.dumps({
            "action": "subscribe",
            "channels": [{"name": "trades", "markets": [pair]}]
        }))
        print(f"📡 Geabonneerd op: {pair}")

    ws = websocket.WebSocketApp(
        "wss://ws.bitvavo.com/v2/",
        on_open=on_open,
        on_message=on_message
    )

    trade_data["ws_object"] = ws
    trade_data["is_streaming"] = True

    ws.run_forever()

# ✅ Start/Stop knoppen
col1, col2 = st.columns(2)

with col1:
    if st.button("▶️ Start Streaming Trades"):
        if not trade_data["is_streaming"]:
            threading.Thread(target=lambda: start_websocket(selected_pair), daemon=True).start()
            st.success(f"Streaming gestart voor {selected_pair}")
        else:
            st.info("WebSocket draait al")

with col2:
    if st.button("⛔ Stop Streaming"):
        if trade_data["is_streaming"]:
            trade_data["is_streaming"] = False
            with trade_data["lock"]:
                trade_data["trades"] = []
                trade_data["total"] = 0.0
            st.warning("Streaming gestopt en trades gewist.")

# ✅ Data ophalen
with trade_data["lock"]:
    trades_copy = trade_data["trades"][:]
    total_copy = trade_data["total"]

st.markdown(f"**Totaal verhandeld volume:** {total_copy:.6f}")

# ✅ Weergave
if trades_copy:
    df = pd.DataFrame(trades_copy)
    table_df = df.head(5)
    st.markdown("### Laatste 5 trades")
    st.dataframe(table_df, use_container_width=True)

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
    st.info("Nog geen trades ontvangen...")

