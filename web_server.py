import subprocess
import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    # Render কে জানানোর জন্য যে সার্ভিসটি চালু আছে
    return "Bot is alive and running!"

def run_flask():
    # Render স্বয়ংক্রিয়ভাবে PORT ভেরিয়েবল সেট করে
    port = int(os.environ.get('PORT', 10000))
    # 0.0.0.0 হোস্টে রান করা আবশ্যিক
    app.run(host='0.0.0.0', port=port)

def run_bot():
    # আপনার মূল বট স্ক্রিপ্টটি চালু করে
    print("Starting the Telegram bot...")
    try:
        subprocess.run(["python", "VJ_Bots.py"])
    except Exception as e:
        print(f"Bot failed to start: {e}")

if __name__ == "__main__":
    # Flask সার্ভারটি একটি আলাদা থ্রেডে (background) চালু করুন
    print("Starting Flask server in a thread...")
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # মূল থ্রেডে (foreground) বটটি চালু করুন
    run_bot()
