import threading

# ✅ Gedeelde structuur voor trades en WebSocket controle
trade_data = {
    "trades": [],
    "total": 0.0,
    "lock": threading.Lock(),
    "ws_object": None,
    "is_streaming": False
}


