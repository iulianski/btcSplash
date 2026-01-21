import ccxt
import asyncio
import os
from datetime import datetime
from collections import deque
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

# Load credentials
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise RuntimeError("Missing TELEGRAM_TOKEN or CHAT_ID in .env")

# Initialize Bybit exchange
exchange = ccxt.bybit()

# Price history storage
price_history = deque(maxlen=5)  # Keep last 5 prices (5 minutes)

def calculate_change(current_price, old_price):
    """Calculate percentage change"""
    if old_price == 0:
        return 0
    return ((current_price - old_price) / old_price) * 100

async def monitor_price():
    bot = Bot(TELEGRAM_TOKEN)
    
    print("🟢 Bot started — monitoring BTC on Bybit")
    print("📊 Alert triggers:")
    print("   • 1min change ≥ 0.3%")
    print("   • 5min change ≥ 1.0%")
    print("   🟢 Green = Long signal (price rising)")
    print("   🔴 Red = Short signal (price falling)")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            # Fetch current BTC price from Bybit
            ticker = exchange.fetch_ticker('BTC/USDT')
            current_price = ticker['last']
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Add to history
            price_history.append({
                'price': current_price,
                'time': timestamp
            })
            
            alerts = []
            signal_indicator = ""
            
            # Check 1-minute change (last price vs current)
            if len(price_history) >= 2:
                price_1min_ago = price_history[-2]['price']
                time_1min_ago = price_history[-2]['time']
                change_1min = calculate_change(current_price, price_1min_ago)
                
                if abs(change_1min) >= 0.3:
                    if change_1min > 0:
                        signal_indicator = "🟢"
                        direction = "📈 LONG"
                    else:
                        signal_indicator = "🔴"
                        direction = "📉 SHORT"
                    
                    alerts.append(
                        f"{direction} | 1min: {change_1min:+.2f}%\n"
                        f"   From: ${price_1min_ago:,.2f} ({time_1min_ago})"
                    )
            
            # Check 5-minute change (oldest price vs current)
            if len(price_history) == 5:
                price_5min_ago = price_history[0]['price']
                time_5min_ago = price_history[0]['time']
                change_5min = calculate_change(current_price, price_5min_ago)
                
                if abs(change_5min) >= 1.0:
                    if change_5min > 0:
                        if not signal_indicator:
                            signal_indicator = "🟢"
                        direction = "🚀 STRONG LONG"
                    else:
                        signal_indicator = "🔴"
                        direction = "💥 STRONG SHORT"
                    
                    alerts.append(
                        f"{direction} | 5min: {change_5min:+.2f}%\n"
                        f"   From: ${price_5min_ago:,.2f} ({time_5min_ago})"
                    )
            
            # Send alert if any condition met
            if alerts:
                message = (
                    f"{signal_indicator} BTC/USDT Alert\n"
                    f"💰 Now: ${current_price:,.2f}\n"
                    f"\n"
                    f"{chr(10).join(alerts)}\n"
                    f"\n"
                    f"🕐 {timestamp}"
                )
                
                await bot.send_message(chat_id=CHAT_ID, text=message)
                print(f"🚨 ALERT: ${current_price:,.2f} | {', '.join([a.split('|')[0].strip() for a in alerts])}")
            else:
                print(f"✓ ${current_price:,.2f} at {timestamp} — no significant change")
            
        except ccxt.NetworkError as e:
            print(f"❌ Network error: {e}")
        except ccxt.ExchangeError as e:
            print(f"❌ Exchange error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        # Wait 60 seconds before next check
        await asyncio.sleep(60)

# Run the bot
if __name__ == "__main__":
    asyncio.run(monitor_price())