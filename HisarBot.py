import telebot
import sqlite3
import feedparser
import schedule
import time
import threading
import os
import requests
import google.generativeai as genai
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8944728010:AAHBZQxdBKEjfGfltkklLdBrv0bZj3MJMjk"
ADMIN_ID = 6919434196

# AI Keys
GEMINI_KEY = "AQ.Ab8RN6I8DNHtzLTLUaLiSFtoc79ylbuTLFhOEidTYYAtYIp1ew"
OPENROUTER_KEY = "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"
GROQ_KEY = "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"
SARVAM_KEY = "sk_d5d5pu7z_h212zXqzExwXyveusw3BxX8y"

genai.configure(api_key=GEMINI_KEY)

app = Flask(__name__)
@app.route('/')
def home():
    return "Hisar Super App is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (chat_id INTEGER PRIMARY KEY, referrals INTEGER DEFAULT 0)''')
conn.commit()

bot = telebot.TeleBot(BOT_TOKEN)

# ================= MULTI-AI FALLBACK SYSTEM =================
def get_ai_response(prompt):
    # 1. Groq (सबसे तेज और भरोसेमंद)
    try:
        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
        data = {"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}]}
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=20)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Groq failed: {e}")

    # 2. OpenRouter
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
        data = {"model": "mistralai/mistral-7b-instruct:free", "messages": [{"role": "user", "content": prompt}]}
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=20)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"OpenRouter failed: {e}")

    # 3. Gemini (Google)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(prompt)
        return res.text
    except Exception as e:
        print(f"Gemini failed: {e}")

    # 4. Sarvam AI
    try:
        headers = {"Authorization": f"Bearer {SARVAM_KEY}", "Content-Type": "application/json"}
        data = {"model": "sarvam-m", "messages": [{"role": "user", "content": prompt}]}
        r = requests.post("https://api.sarvam.ai/v1/chat/completions", headers=headers, json=data, timeout=20)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Sarvam failed: {e}")

    return "माफ़ करें, अभी AI सर्वर व्यस्त हैं। कृपया थोड़ी देर बाद प्रयास करें।"

# ================= WEATHER (Hisar) =================
def get_weather():
    try:
        r = requests.get("https://wttr.in/Hisar?format=%C+%t+%w+%h&m", timeout=10)
        return f"🌤️ **हिसार का मौसम:**\n{r.text.strip()}"
    except:
        return "मौसम की जानकारी अभी उपलब्ध नहीं है।"

# ================= AQI / POLLUTION (Hisar) =================
def get_aqi():
    try:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=29.1492&longitude=75.7217&current=pm10,pm2_5"
        r = requests.get(url, timeout=10).json()
        pm25 = r['current']['pm2_5']
        pm10 = r['current']['pm10']
        if pm25 < 30: level = "🟢 अच्छा"
        elif pm25 < 60: level = "🟡 मध्यम"
        elif pm25 < 90: level = "🟠 खराब"
        else: level = "🔴 बहुत खराब"
        return f"🌫️ **हिसार का AQI:**\nPM2.5: {pm25}\nPM10: {pm10}\nस्तर: {level}"
    except:
        return "AQI की जानकारी अभी उपलब्ध नहीं है।"

# ================= NEWS (Hisar) =================
def get_news():
    try:
        feed = feedparser.parse("https://news.google.com/rss/search?q=hisar&hl=hi-IN&gl=IN&ceid=IN:hi")
        if feed.entries:
            e = feed.entries[0]
            return f"📰 **हिसार की ताज़ा खबर:**\n\n{e.title}\n\n🔗 {e.link}"
    except:
        pass
    return "खबरें अभी उपलब्ध नहीं हैं।"

# ================= JOB (Hisar) =================
def get_job():
    try:
        feed = feedparser.parse("https://news.google.com/rss/search?q=%22Hisar%22+(Job+OR+Naukri+OR+Bharti+OR+Recruitment)&hl=hi-IN&gl=IN&ceid=IN:hi")
        if feed.entries:
            e = feed.entries[0]
            return f"💼 **हिसार में नई नौकरी:**\n\n{e.title}\n\n🔗 {e.link}"
    except:
        pass
    return "नौकरी अभी उपलब्ध नहीं है।"

def send_updates(chat_id=None):
    url = "https://news.google.com/rss/search?q=%22Hisar%22+(Job+OR+Naukri+OR+Bharti+OR+Recruitment)&hl=hi-IN&gl=IN&ceid=IN:hi"
    feed = feedparser.parse(url)
    if feed.entries:
        entry = feed.entries[0]
        msg = f"💼 **हिसार में नई नौकरी:**\n\n{entry.title}\n\n🔗 {entry.link}"
        if chat_id:
            bot.send_message(chat_id, msg, parse_mode='Markdown')
        else:
            last = ""
            if os.path.exists("last_job.txt"):
                with open("last_job.txt") as f: last = f.read().strip()
            if entry.link == last: return
            with open("last_job.txt", "w") as f: f.write(entry.link)
            c.execute("SELECT chat_id FROM users")
            for u in c.fetchall():
                try: bot.send_message(u[0], msg, parse_mode='Markdown')
                except: pass

def run_schedule():
    schedule.every(1).hours.do(send_updates)
    while True:
        schedule.run_pending()
        time.sleep(1)

# ================= KEYBOARDS =================
def main_menu():
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("💼 नौकरी", callback_data="job"),
          InlineKeyboardButton("📰 खबरें", callback_data="news"))
    m.add(InlineKeyboardButton("🌤️ मौसम", callback_data="weather"),
          InlineKeyboardButton("🌫️ AQI", callback_data="aqi"))
    m.add(InlineKeyboardButton("🍔 खाना ऑर्डर", callback_data="food"),
          InlineKeyboardButton("🚕 कैब बुक", callback_data="cab"))
    m.add(InlineKeyboardButton("🎬 मूवी टिकट", callback_data="movie"),
          InlineKeyboardButton("🚆 ट्रेन", callback_data="train"))
    m.add(InlineKeyboardButton("👥 रेफर करें", callback_data="refer"),
          InlineKeyboardButton("ℹ️ जानकारी", callback_data="about"))
    return m

def food_menu():
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("Zomato", url="https://www.zomato.com/hisar"),
          InlineKeyboardButton("Swiggy", url="https://www.swiggy.com/city/hisar"))
    m.add(InlineKeyboardButton("⬅️ वापस", callback_data="back"))
    return m

def cab_menu():
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("Ola", url="https://book.olacabs.com/"),
          InlineKeyboardButton("Uber", url="https://m.uber.com/"))
    m.add(InlineKeyboardButton("Rapido", url="https://onelink.to/rapido"),
          InlineKeyboardButton("⬅️ वापस", callback_data="back"))
    return m

def movie_menu():
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("BookMyShow", url="https://in.bookmyshow.com/hisar"),
          InlineKeyboardButton("PVR", url="https://www.pvrcinemas.com/"))
    m.add(InlineKeyboardButton("⬅️ वापस", callback_data="back"))
    return m

def train_menu():
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("IRCTC", url="https://www.irctc.co.in/"),
          InlineKeyboardButton("ट्रेन स्टेटस", url="https://enquiry.indianrail.gov.in/"))
    m.add(InlineKeyboardButton("✈️ फ्लाइट", url="https://www.makemytrip.com/flights/"))
    m.add(InlineKeyboardButton("⬅️ वापस", callback_data="back"))
    return m

# ================= HANDLERS =================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) > 1:
        ref = args[1]
        if ref != str(user_id):
            try:
                c.execute("INSERT INTO users (chat_id) VALUES (?)", (chat_id,))
                c.execute("UPDATE users SET referrals = referrals + 1 WHERE chat_id = ?", (ref,))
                conn.commit()
                bot.send_message(ref, "🎉 बधाई हो! आपने एक नया दोस्त जोड़ा है।")
            except sqlite3.IntegrityError:
                pass

    try:
        c.execute("INSERT INTO users (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass

    bot.reply_to(message,
        "नमस्ते! मैं **Hisar Super App** हूँ। 🤖\n\n"
        "मैं आपको हिसार की हर जानकारी दूँगा — नौकरी, खबरें, मौसम, AQI, खाना, कैब, मूवी, ट्रेन।\n\n"
        "कोई भी सवाल पूछें, मैं AI की तरह जवाब दूँगा।\n\n"
        "नीचे दिए बटन का इस्तेमाल करें:",
        reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    bot.answer_callback_query(call.id)
    cid = call.message.chat.id

    if call.data == "job":
        bot.send_message(cid, get_job(), parse_mode='Markdown', disable_web_page_preview=False)
    elif call.data == "news":
        bot.send_message(cid, get_news(), parse_mode='Markdown')
    elif call.data == "weather":
        bot.send_message(cid, get_weather(), parse_mode='Markdown')
    elif call.data == "aqi":
        bot.send_message(cid, get_aqi(), parse_mode='Markdown')
    elif call.data == "food":
        bot.send_message(cid, "🍔 कहाँ से खाना ऑर्डर करना है?", reply_markup=food_menu())
    elif call.data == "cab":
        bot.send_message(cid, "🚕 कौन सी कैब बुक करनी है?", reply_markup=cab_menu())
    elif call.data == "movie":
        bot.send_message(cid, "🎬 मूवी टिकट बुक करें:", reply_markup=movie_menu())
    elif call.data == "train":
        bot.send_message(cid, "🚆 ट्रेन/फ्लाइट बुकिंग:", reply_markup=train_menu())
    elif call.data == "refer":
        link = f"https://t.me/HisarBot?start={call.from_user.id}"
        c.execute("SELECT referrals FROM users WHERE chat_id = ?", (call.from_user.id,))
        r = c.fetchone()
        count = r[0] if r else 0
        bot.send_message(cid, f"👥 **आपका रेफरल लिंक:**\n{link}\n\nजोड़े गए दोस्त: {count}\n\n(5 दोस्त = VIP बैज 🎖️)")
    elif call.data == "about":
        bot.send_message(cid,
            "🤖 **Hisar Super App**\n"
            "बनाने वाले: Summit Kummar\n\n"
            "फीचर्स: नौकरी, खबरें, मौसम, AQI, खाना, कैब, मूवी, ट्रेन, AI चैट।")
    elif call.data == "back":
        bot.send_message(cid, "मुख्य मेनू:", reply_markup=main_menu())

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "क्षमा करें, यह कमांड सिर्फ एडमिन के लिए है।")
        return
    txt = message.text.replace('/broadcast', '').strip()
    if not txt:
        bot.reply_to(message, "संदेश लिखें। जैसे: /broadcast आज मेला है!")
        return
    c.execute("SELECT chat_id FROM users")
    n = 0
    for u in c.fetchall():
        try: bot.send_message(u[0], f"📢 अपडेट:\n\n{txt}"); n += 1
        except: pass
    bot.reply_to(message, f"संदेश {n} यूज़र्स को भेज दिया गया।")

# AI चैट (हर नॉर्मल मैसेज के लिए)
@bot.message_handler(func=lambda m: True)
def ai_chat(message):
    if message.text.startswith('/'): return
    bot.send_chat_action(message.chat.id, 'typing')
    reply = get_ai_response(message.text)
    bot.reply_to(message, reply)

def run_bot():
    bot.polling(non_stop=True)

if __name__ == "__main__":
    threading.Thread(target=run_schedule, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    run_web()
