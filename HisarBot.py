import telebot
import sqlite3
import feedparser
import schedule
import time
import threading
import os
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8944728010:AAHBZQxdBKEjfGfltkklLdBrv0bZj3MJMjk"
ADMIN_ID = 6919434196

# Flask वेब सर्वर
app = Flask(__name__)
@app.route('/')
def home():
    return "Hisar AI Assistant is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# डेटाबेस सेटअप (रेफरल काउंट के साथ)
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (chat_id INTEGER PRIMARY KEY, referrals INTEGER DEFAULT 0)''')
conn.commit()

bot = telebot.TeleBot(BOT_TOKEN)

def send_updates(chat_id=None):
    url = "https://news.google.com/rss/search?q=%22Hisar%22+(Job+OR+Naukri+OR+Bharti+OR+Recruitment)&hl=hi-IN&gl=IN&ceid=IN:hi"
    feed = feedparser.parse(url)
    if feed.entries:
        entry = feed.entries[0]
        title = entry.title
        link = entry.link
        message_text = f"💼 **हिसार में नई नौकरी:**\n\n{title}\n\n🔗 पूरी जानकारी देखें: {link}"
        
        if chat_id:
            bot.send_message(chat_id, message_text, parse_mode='Markdown')
        else:
            last_sent_file = "last_job.txt"
            last_link = ""
            if os.path.exists(last_sent_file):
                with open(last_sent_file, "r") as f:
                    last_link = f.read().strip()
            if link == last_link:
                return
            with open(last_sent_file, "w") as f:
                f.write(link)
            
            c.execute("SELECT chat_id FROM users")
            users = c.fetchall()
            for user in users:
                try:
                    bot.send_message(user[0], message_text, parse_mode='Markdown')
                except:
                    pass

def run_schedule():
    schedule.every(1).hours.do(send_updates)
    while True:
        schedule.run_pending()
        time.sleep(1)

# रेफरल लिंक बनाने का फंक्शन
def get_referral_link(user_id):
    return f"https://t.me/HisarBot?start={user_id}"

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()

    # रेफरल चेक करें
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id != str(user_id): # खुद को रेफर न कर सके
            try:
                c.execute("INSERT INTO users (chat_id) VALUES (?)", (chat_id,))
                c.execute("UPDATE users SET referrals = referrals + 1 WHERE chat_id = ?", (referrer_id,))
                conn.commit()
                bot.send_message(referrer_id, "🎉 बधाई हो! आपने एक नया दोस्त जोड़ा है।")
            except sqlite3.IntegrityError:
                pass # अगर यूज़र पहले से है, तो कुछ न करें

    try:
        c.execute("INSERT INTO users (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    
    markup = InlineKeyboardMarkup()
    b1 = InlineKeyboardButton("🚀 आज की नौकरी", callback_data="latest_job")
    b2 = InlineKeyboardButton("👥 रेफर करें", callback_data="refer")
    b3 = InlineKeyboardButton("ℹ️ जानकारी", callback_data="about")
    markup.add(b1)
    markup.add(b2, b3)
    
    bot.reply_to(message, "नमस्ते! मैं Hisar AI Assistant हूँ। 🤖\nमैं आपको हर 1 घंटे में हिसार की ताज़ा नौकरियों की जानकारी भेजूँगा।\n\nनीचे दिए गए बटन का इस्तेमाल करें:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "latest_job":
        bot.answer_callback_query(call.id, "नौकरी लोड हो रही है...")
        send_updates(call.message.chat.id)
    elif call.data == "refer":
        bot.answer_callback_query(call.id)
        link = get_referral_link(call.from_user.id)
        c.execute("SELECT referrals FROM users WHERE chat_id = ?", (call.from_user.id,))
        res = c.fetchone()
        count = res[0] if res else 0
        bot.send_message(call.message.chat.id, f"👥 **आपका रेफरल लिंक:**\n{link}\n\nअब तक जोड़े गए दोस्त: {count}\n\n(5 दोस्त जोड़ने पर आपको VIP बैज मिलेगा! 🎖️)")
    elif call.data == "about":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "मुझे Summit Kummar ने बनाया है।\nमैं हिसार की नौकरियों को खोजकर लोगों तक पहुँचाता हूँ। 🚀")

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

def run_bot():
    bot.polling(non_stop=True)

if __name__ == "__main__":
    threading.Thread(target=run_schedule, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    run_web()
