import threading

# Gedeelde data voor meerdere sessies
trade_data = {
    "sessions": {},  # Per sessie-ID: {"trades": [...], "total": float}
    "active_sessions": set(),
    "lock": threading.Lock()
}


