import finnhub
import json
import websocket
import os
import sys
import threading
import time

API_KEY = os.getenv("FINNHUB_API_KEY")
if not API_KEY:
    print("❌ Error: FINNHUB_API_KEY not found in environment variables!")

top_coins = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT", "BINANCE:DOGEUSDT"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(SCRIPT_DIR, "crypto.json")

finnhub_client = finnhub.Client(api_key=API_KEY)
dashboard_data = {}

volume_initialized = False

def update_metadata():
    global volume_initialized
    print("[REST] Syncing 24h Stats & News...")
    for symbol in top_coins:
        try:
            quote = finnhub_client.quote(symbol)
            change = quote['dp']
            icon = "▲" if change >= 0 else "▼"
            
            if symbol not in dashboard_data:
                dashboard_data[symbol] = {"raw_volume": float(quote.get('v', 0))}
            
            dashboard_data[symbol].update({
                "price": f"{quote['c']:.2f}" if symbol != "BINANCE:DOGEUSDT" else f"{quote['c']:.4f}",
                "change_24h": f"{icon} {change:.2f}%",
                "day_range": f"L: ${quote['l']:.2f} - H: ${quote['h']:.2f}" if symbol != "BINANCE:DOGEUSDT" \
                    else f"L: ${quote['l']:.4f} - H: ${quote['h']:.4f}",
                "volume_24h": f"{dashboard_data[symbol]['raw_volume']:,.2f}"
            })
        except Exception as e:
            print(f"Price Error: {e}")

    try:
        news = finnhub_client.general_news('crypto', min_id=0)
        dashboard_data["news_ticker"] = [n['headline'] for n in news[:10]]
    except Exception as e:
        print(f"News Error: {e}")

def save_json():
    temp_file = SAVE_FILE + ".tmp"
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=4, ensure_ascii=False)
        os.replace(temp_file, SAVE_FILE)
    except Exception as e:
        pass

def on_message(ws, message):
    data = json.loads(message)
    if data.get('type') == 'trade':
        for trade in data['data']:
            symbol, new_price, trade_vol = trade['s'], trade['p'], trade['v']
            
            if symbol in dashboard_data:
                dashboard_data[symbol]["raw_volume"] += trade_vol
                dashboard_data[symbol]["volume_24h"] = f"{dashboard_data[symbol]['raw_volume']:,.2f}"
                dashboard_data[symbol]["price"] = f"{new_price:.5f}"
        save_json()

def on_open(ws):
    print("✅ WebSocket Connected! Sending Subscriptions...")
    for s in top_coins:
        msg = f'{{"type":"subscribe","symbol":"{s}"}}'
        ws.send(msg)
        print(f"   - Subscribed to {s}")

def run_websocket():
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={API_KEY}",
        on_open=on_open,
        on_message=on_message,
        on_error=lambda ws, e: print(f"❌ WS Error: {e}"),
        on_close=lambda ws, c, m: print(f"⚠️ Connection Closed: {m}")
    )
    ws.run_forever(ping_interval=20, ping_timeout=10)

if __name__ == "__main__":
    update_metadata()
    
    if "--once" in sys.argv:
        print("Running one-time update for GitHub...")
        save_json()
        print("Done!")
        sys.exit(0)
    else:
        threading.Thread(target=run_websocket, daemon=True).start()
        while True:
            time.sleep(60)
            update_metadata()
