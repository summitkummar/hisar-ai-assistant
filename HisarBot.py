import telebot
import sqlite3
import feedparser
import schedule
import time
import threading
import os
from flask import Flask

BOT_TOKEN = "8944728010:AAErU94hBY9JnKXqPV-xHQm-IiM54BYAVso"
ADMIN_ID = 6919434196

bot = telebot.TeleBot(BOT_TOKEN)

# Flask वेब सर्वर (Render को जिंदा रखने के लिए)
app = Flask(__name__)
@app.route('/')
def home():
    return "Hisar AI Assistant is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# डेटाबेस सेटअप
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY)''')
conn.commit()

def send_updates():
    print("नौकरी चेक की जा रही है...")
    url = "https://news.google.com/rss/search?q=%22Hisar%22+(Job+OR+Naukri+OR+Bharti+OR+Recruitment)&hl=hi-IN&gl=IN&ceid=IN:hi"
    feed = feedparser.parse(url)
    
    if feed.entries:
        entry = feed.entries[0]
        title = entry.title
        link = entry.link
        
        last_sent_file = "last_job.txt"
        last_link = ""
        if os.path.exists(last_sent_file):
            with open(last_sent_file, "r") as f:
                last_link = f.read().strip()

        if link == last_link:
            print("यह नौकरी पहले ही भेजी जा चुकी है।")
            return

        with open(last_sent_file, "w") as f:
            f.write(link)

        message_text = f"💼 **हिसार में नई नौकरी:**\n\n{title}\n\n🔗 पूरी जानकारी देखें: {link}"
        
        c.execute("SELECT chat_id FROM users")
        users = c.fetchall()
        count = 0
        for user in users:
            try:
                bot.send_message(user[0], message_text, parse_mode='Markdown')
                count += 1
            except:
                pass
        print(f"नौकरी {count} यूज़र्स को भेज दी गई।")

def run_schedule():
    schedule.every(1).hours.do(send_updates)
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    try:
        c.execute("INSERT INTO users (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    bot.reply_to(message, "नमस्ते! मैं Hisar AI Assistant हूँ। 🤖\nमैं आपको हर 1 घंटे में हिसार की ताज़ा नौकरियों की जानकारी भेजूँगा।")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "क्षमा करें, आप इस कमांड का इस्तेमाल नहीं कर सकते।")
        return
    msg_text = message.text.replace('/broadcast', '').strip()
    if not msg_text:
        bot.reply_to(message, "कृपया संदेश लिखें। जैसे: /broadcast आज की नई नौकरी!")
        return
    c.execute("SELECT chat_id FROM users")
    users = c.fetchall()
    for user in users:
        try:
            bot.send_message(user[0], f"📢 अपडेट:\n\n{msg_text}")
        except:
            pass
    bot.reply_to(message, "संदेश सभी यूज़र्स को भेज दिया गया है।")

# शेड्यूलर और वेब सर्वर को अलग-अलग थ्रेड में चलाना
threading.Thread(target=run_schedule, daemon=True).start()
threading.Thread(target=run_web, daemon=True).start()

print("Hisar AI Assistant (24/7) चालू हो गया है...")
bot.polling()
