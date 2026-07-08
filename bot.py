import telebot
import sqlite3
import json
import os
import time
from threading import Thread, RLock
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from flask import Flask, send_from_directory, make_response

# --- UYG'OTKICH VA REYTING TARQATUVCHI ---
app = Flask(__name__)

@app.route('/')
def main():
    return "LootTap Bot Serveri V6.0 (KAZINO & KASSA) 100% Jangovar Holatda!"

@app.route('/channels.json')
def serve_channels():
    if not os.path.exists('channels.json'):
        save_channels(DEFAULT_CHANNELS)
    response = make_response(send_from_directory('.', 'channels.json'))
    response.headers['Access-Control-Allow-Origin'] = '*' 
    return response

@app.route('/<path:path>')
def serve_file(path):
    if not os.path.exists(path):
        update_rating_json()
    response = make_response(send_from_directory('.', path))
    response.headers['Access-Control-Allow-Origin'] = '*' 
    return response

def run():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    server = Thread(target=run, daemon=True)
    server.start()

# --- SOZLAMALAR ---
TOKEN = '8610358967:AAEa0hxqrnKA8z6xfwS5oVF5yXc8l7VwSj4'
bot = telebot.TeleBot(TOKEN, threaded=True)

WEB_APP_URL = "https://sherbekcreator.github.io/lootdrop.uz/"


# SIZNING UZCARD / HUMO RAQAMINGIZ (KASSA UCHUN)
UZCARD_NUMBER = "8600 1234 5678 9012"
CARD_OWNER = "Sherbek Shavkatov"
ADMIN_USERNAME = "@sherbeklich"

ADMIN_IDS = [8361233416, 942670016] 

DEFAULT_CHANNELS = [
    {"id": "@loftbedsuz", "name": "LOFTBEDS UZ", "url": "https://t.me/loftbedsuz"}
]
OTHER_CHANNELS = []

def load_channels():
    if not os.path.exists("channels.json"):
        with open("channels.json", "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CHANNELS, f, ensure_ascii=False)
        return DEFAULT_CHANNELS
    with open("channels.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_channels(channels_list):
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(channels_list, f, ensure_ascii=False)

CURRENT_STREAM_URL = ""
CLAIMED_STREAM = set()

# --- MA'LUMOTLAR BAZASI VA YANGI JADVALLAR ---
db_lock = RLock()
conn = sqlite3.connect('loottap.db', check_same_thread=False, isolation_level=None)

with db_lock:
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, score INTEGER DEFAULT 0, energy INTEGER DEFAULT 1000, referrals INTEGER DEFAULT 0, unlocked_ref INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS used_accounts (user_id INTEGER, game_id TEXT, game_nick TEXT)''')
    
    # YANGI QO'SHILGAN BAZALAR (Xavfsizlik va Kassa)
    cursor.execute('''CREATE TABLE IF NOT EXISTS promocodes (code TEXT PRIMARY KEY, uses INTEGER, reward INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS used_promos (user_id INTEGER, code TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transfers (user_id INTEGER, date TEXT)''')
    
    try: cursor.execute("ALTER TABLE users ADD COLUMN upg_tap INTEGER DEFAULT 0")
    except Exception: pass 
    try: cursor.execute("ALTER TABLE users ADD COLUMN upg_energy INTEGER DEFAULT 0")
    except Exception: pass
    try: cursor.execute("ALTER TABLE users ADD COLUMN upg_regen INTEGER DEFAULT 0")
    except Exception: pass
    try: cursor.execute("ALTER TABLE users ADD COLUMN daily_limit INTEGER DEFAULT 15000")
    except Exception: pass
    try: cursor.execute("ALTER TABLE users ADD COLUMN is_referred INTEGER DEFAULT 0")
    except Exception: pass
    try: cursor.execute("ALTER TABLE users ADD COLUMN special_task INTEGER DEFAULT 0")
    except Exception: pass

def update_rating_json():
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT first_name, score FROM users WHERE is_banned = 0 ORDER BY score DESC LIMIT 100")
        top_users = [{"username": row[0] if row[0] else "Unknown", "loot": row[1]} for row in cur.fetchall()]
        with open("rating.json", "w", encoding="utf-8") as f: json.dump(top_users, f)

        cur.execute("SELECT first_name, referrals FROM users WHERE referrals > 0 AND is_banned = 0 ORDER BY referrals DESC LIMIT 100")
        top_refs = [{"username": row[0] if row[0] else "Unknown", "refs": row[1]} for row in cur.fetchall()]
        with open("ref_rating.json", "w", encoding="utf-8") as f: json.dump(top_refs, f)

def rating_auto_updater():
    while True:
        try: update_rating_json()
        except Exception: pass
        time.sleep(300)

def main_menu_markup(user_id):
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT score, energy, upg_tap, upg_energy, upg_regen, daily_limit, referrals FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        
    if row: score, energy, upg_tap, upg_energy, upg_regen, daily_limit, refs = row
    else: score, energy, upg_tap, upg_energy, upg_regen, daily_limit, refs = (0, 1000, 0, 0, 0, 15000, 0)

    markup = InlineKeyboardMarkup()
    full_url = f"{WEB_APP_URL}?userid={user_id}&score={score}&energy={energy}&tap={upg_tap}&eng={upg_energy}&reg={upg_regen}&limit={daily_limit}&refs={refs}"
    webapp = WebAppInfo(url=full_url)
    markup.add(InlineKeyboardButton(text="🎰 > O'YINGA KIRISH <", web_app=webapp))
    return markup

def check_all_subs(user_id):
    req_channels = load_channels()
    for ch in req_channels:
        try:
            member = bot.get_chat_member(ch["id"], user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except Exception: return False
    return True

def sub_menu_markup(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for i, ch in enumerate(load_channels(), 1):
        btn_text = f"[{i}] {ch['name']}"
        try:
            member = bot.get_chat_member(ch['id'], user_id)
            if member.status in ['member', 'administrator', 'creator']: btn_text = f"✅ {ch['name']}"
        except Exception: pass
        buttons.append(InlineKeyboardButton(text=btn_text, url=ch['url']))
        
    markup.add(*buttons)
    markup.add(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
    return markup

def get_welcome_text(first_name):
    return (f"👋 Xush kelibsiz, {first_name}!\n"
            f"🎮 PUBG UC va Qimmatbaho Qurollar yutish markazi!\n"
            f"Bot orqali Loot to'plang va ularni UC ga almashtiring 💎\n\n"
            f"🔥 Qanday ishlaydi?\n"
            f"• 🎡 Barabanni aylantiring va Loot oling\n"
            f"• 👥 Do'stlarni taklif qilib, balansingizni oshiring\n"
            f"• 📦 Keys oching va Mifik qurollar yutib oling!\n\n"
            f"⚡️ O'yinni boshlash uchun tugmani bosing!")

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    text = message.text

    with db_lock:
        cur = conn.cursor()
        cur.execute('INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)', (user_id, first_name))
        cur.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
        user_status = cur.fetchone()
        
    if user_status and user_status[0] == 1:
        try: bot.send_message(message.chat.id, "🚫 **XAVFSIZLIK TIZIMI:**\n\nSiz firibgarlik sababli botdan umrbod **bloklangansiz!**", parse_mode='Markdown')
        except Exception: pass
        return

    if len(text.split()) > 1:
        param = text.split()[1]
        
        # --- DO'STLAR VA REF MANTIG'I ---
        if param.startswith('ref_'):
            try:
                inviter_id = int(param.split('_')[1])
                if inviter_id != user_id:
                    with db_lock:
                        cur = conn.cursor()
                        cur.execute("SELECT is_referred FROM users WHERE user_id = ?", (user_id,))
                        ref_status = cur.fetchone()
                        if ref_status and ref_status[0] == 0:
                            cur.execute("UPDATE users SET is_referred = 1 WHERE user_id = ?", (user_id,))
                            cur.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (inviter_id,))
                            update_rating_json()
                            try: bot.send_message(inviter_id, f"🎉 Tabriklaymiz! Sizning taklifingiz bilan do'stingiz botga qo'shildi!")
                            except Exception: pass
            except Exception: pass

        # --- YANGI: PROMOKOD MANTIG'I ---
        elif param.startswith('promo_'):
            try:
                code = param.split('_')[1].upper()
                with db_lock:
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM used_promos WHERE user_id = ? AND code = ?", (user_id, code))
                    if cur.fetchone():
                        bot.send_message(user_id, "❌ Siz bu promokodni allaqachon ishlatgansiz!")
                        return
                    
                    cur.execute("SELECT uses, reward FROM promocodes WHERE code = ?", (code,))
                    promo = cur.fetchone()
                    if not promo:
                        bot.send_message(user_id, "❌ Promokod xato yoki mavjud emas!")
                        return
                    
                    uses_left, reward = promo
                    if uses_left <= 0:
                        bot.send_message(user_id, "❌ Afsus! Bu promokodning limiti (soni) tugagan!")
                        return
                    
                    # Faollashtirish
                    cur.execute("UPDATE promocodes SET uses = uses - 1 WHERE code = ?", (code,))
                    cur.execute("INSERT INTO used_promos (user_id, code) VALUES (?, ?)", (user_id, code))
                    cur.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (reward, user_id))
                    
                update_rating_json()
                bot.send_message(user_id, f"🎉 **Tabriklaymiz!**\n\nSiz `{code}` promokodini faollashtirdingiz va hisobingizga **{reward:,} Loot** qo'shildi!", parse_mode="Markdown")
            except Exception:
                bot.send_message(user_id, "❌ Promokod xatosi.")
            return

        # --- YANGI: O'TKAZMALAR MANTIG'I ---
        elif param.startswith('transfer_'):
            try:
                parts = param.split('_')
                target_id = int(parts[1])
                amount = int(parts[2])
                today = time.strftime("%Y-%m-%d")
                
                with db_lock:
                    cur = conn.cursor()
                    # Kunlik cheklovni nazorat qilish
                    cur.execute("SELECT date FROM transfers WHERE user_id = ? AND date = ?", (user_id, today))
                    if cur.fetchone():
                        bot.send_message(user_id, "❌ Siz bugun o'tkazma limitidan foydalangansiz! Kunda faqat 1 marta mumkin.")
                        return
                    
                    # Hisobni tekshirish
                    cur.execute("SELECT score FROM users WHERE user_id = ?", (user_id,))
                    user_score = cur.fetchone()
                    if not user_score or user_score[0] < amount:
                        bot.send_message(user_id, "❌ Hisobingizda yetarli Loot mavjud emas!")
                        return
                    
                    # Targetni tekshirish
                    cur.execute("SELECT first_name FROM users WHERE user_id = ?", (target_id,))
                    if not cur.fetchone():
                        bot.send_message(user_id, "❌ Qabul qiluvchi botdan ro'yxatdan o'tmagan! (ID xato)")
                        return
                    
                    # Tranzaksiyani amalga oshirish
                    cur.execute("UPDATE users SET score = score - ? WHERE user_id = ?", (amount, user_id))
                    cur.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (amount, target_id))
                    cur.execute("INSERT INTO transfers (user_id, date) VALUES (?, ?)", (user_id, today))
                    
                update_rating_json()
                bot.send_message(user_id, f"✅ **Muvaffaqiyatli!**\nSiz `{target_id}` ID egasiga **{amount:,} Loot** yubordingiz.", parse_mode="Markdown")
                try: bot.send_message(target_id, f"💸 **Sizga Loot keldi!**\n\n🆔 Yuboruvchi ID: `{user_id}`\n💰 Miqdor: **{amount:,} Loot**", parse_mode="Markdown")
                except Exception: pass
            except Exception:
                bot.send_message(user_id, "❌ O'tkazmada xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
            return

        # --- YANGI: KASSA VA UZS TO'LOV MANTIG'I ---
        elif param.startswith('buy_'):
            try:
                package_price = param.split('_')[1]
                prices = {
                    "5000": "5,000,000 Loot",
                    "10000": "12,000,000 Loot",
                    "50000": "70,000,000 Loot"
                }
                
                if package_price in prices:
                    msg = (f"💳 **Balansni to'ldirish bo'limi!**\n\n"
                           f"Siz **{prices[package_price]}** sotib olmoqchisiz.\n\n"
                           f"📝 To'lov summasi: **{int(package_price):,} UZS**\n\n"
                           f"🏦 **Uzcard / Humo raqami:**\n"
                           f"`{UZCARD_NUMBER}`\n"
                           f"👤 Qabul qiluvchi: **{CARD_OWNER}**\n\n"
                           f"⚠️ **DIQQAT:** To'lovni amalga oshirgach, to'lov chekini (skrinshot) va quyidagi ID raqamingizni adminimizga yuboring:\n\n"
                           f"Sizning ID raqamingiz: `{user_id}`\n\n"
                           f"👉 Admin: {ADMIN_USERNAME}")
                    bot.send_message(user_id, msg, parse_mode="Markdown")
                else:
                    bot.send_message(user_id, "❌ Bunday paket mavjud emas!")
            except Exception: pass
            return

        # --- HTML DAN MA'LUMOT SAQLASH ---
        elif param.startswith('save_'):
            try:
                parts = param.split('_')
                if len(parts) >= 7:
                    new_score, new_energy, new_tap, new_eng, new_reg, new_limit = map(int, parts[1:7])
                    webapp_refs = int(parts[7]) if len(parts) >= 8 else 0

                    with db_lock:
                        cur = conn.cursor()
                        cur.execute('INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)', (user_id, first_name))
                        cur.execute("SELECT score, referrals FROM users WHERE user_id = ?", (user_id,))
                        db_data = cur.fetchone()
                        db_score, db_refs = (db_data[0], db_data[1]) if db_data else (0, 0)
                        
                        if new_score - db_score > 5000000:
                            cur.execute("UPDATE users SET is_banned = 1, score = 0 WHERE user_id = ?", (user_id,))
                            try: bot.send_message(user_id, "🚫 **ANTI-NAKRUTKA TIZIMI!**\n\nUmrbod BLOKLANDINGIZ!")
                            except Exception: pass
                            return

                        final_refs = max(webapp_refs, db_refs)
                        cur.execute('''UPDATE users SET score=?, energy=?, upg_tap=?, upg_energy=?, upg_regen=?, daily_limit=?, referrals=? WHERE user_id=?''',
                                       (new_score, new_energy, new_tap, new_eng, new_reg, new_limit, final_refs, user_id))
            except Exception: pass
            return

        # --- DO'KON XARIDLARI (UC VA BOSHQA) ---
        elif param.startswith('withdraw_'):
            try:
                parts = param.split('_')
                w_type, price, new_score = parts[1].upper(), int(parts[2]), int(parts[3])
                game_id = parts[4] if len(parts) > 4 else "Noma'lum"
                game_nick = parts[5] if len(parts) > 5 else "Noma'lum"

                with db_lock:
                    cur = conn.cursor()
                    cur.execute("SELECT user_id FROM used_accounts WHERE (game_id = ? OR game_nick = ?) AND user_id != ?", (game_id, game_nick, user_id))
                    if cur.fetchone():
                        cur.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
                        return
                    cur.execute("INSERT INTO used_accounts (user_id, game_id, game_nick) VALUES (?, ?, ?)", (user_id, game_id, game_nick))
                    cur.execute("UPDATE users SET score = ? WHERE user_id = ?", (new_score, user_id))
                    
                update_rating_json()
                admin_msg = (f"🔔 **Yangi UC Xarid so'rovi!**\n\n👤 O'yinchi: {first_name} ({username})\n🆔 ID: `{user_id}`\n\n🛒 Olish turi: **{w_type}**\n🎮 O'yin ID: `{game_id}`\n🥷 O'yin NIK: {game_nick}\n\n💰 Sarflandi: {price:,} loot\n\n⚠️ Admin, so'rovni ko'rib chiqing!")
                try: bot.send_message(ADMIN_IDS[0], admin_msg, parse_mode='Markdown')
                except Exception: pass
                
                try: bot.send_message(message.chat.id, f"🎉 So'rovingiz qabul qilindi!\n\n💳 Xarid: {w_type}\n🎮 O'yin ID: {game_id}\n✅ 24 soat ichida hisobingizga tushadi!", reply_markup=main_menu_markup(user_id))
                except Exception: pass
            except Exception: pass
            return

        elif param.startswith('refwithdraw_'):
            try:
                parts = param.split('_')
                w_type, req_friends, prize_amount = parts[1].upper(), int(parts[2]), int(parts[3])

                with db_lock:
                    cur = conn.cursor()
                    cur.execute("SELECT referrals, score FROM users WHERE user_id = ?", (user_id,))
                    user_data = cur.fetchone()

                    if user_data:
                        refs, current_score = user_data[0], user_data[1]
                        
                        if current_score < 5000000:
                            try: bot.send_message(message.chat.id, "❌ **Xatolik! Ruxsat yo'q!**\n\nQoidaga muvofiq, kamida 5 mln loot yig'ishingiz shart.", reply_markup=main_menu_markup(user_id))
                            except Exception: pass
                            return

                        if refs < req_friends:
                            try: bot.send_message(message.chat.id, f"❌ **Xatolik!** Yetarli do'stlar yo'q!", reply_markup=main_menu_markup(user_id))
                            except Exception: pass
                            return

                        # Yutuqni beramiz
                        cur.execute("UPDATE users SET referrals = referrals - ?, score = score + ? WHERE user_id = ?", (req_friends, prize_amount, user_id))
                        
                update_rating_json()
                msg = (f"🎉 Do'stlaringiz uchun Loot yutuqni oldingiz!\n\n🎁 Qo'shildi: {prize_amount:,} Loot\n👥 Sarflandi: {req_friends} ta do'st")
                try: bot.send_message(message.chat.id, msg, reply_markup=main_menu_markup(user_id))
                except Exception: pass
            except Exception: pass
            return

    if not check_all_subs(user_id):
        caption_text = "⚠️ Majburiy obuna talab qilinadi!\n\nDavom etish uchun kanallarga obuna bo'ling! 👇"
        try: bot.send_photo(message.chat.id, photo=START_IMAGE_URL, caption=caption_text, reply_markup=sub_menu_markup(user_id))
        except Exception: pass
        return

    msg_text = get_welcome_text(first_name)
    try: bot.send_photo(message.chat.id, photo=START_IMAGE_URL, caption=msg_text, reply_markup=main_menu_markup(user_id))
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data == 'check_sub')
def check_sub_callback(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name

    with db_lock:
        cur = conn.cursor()
        cur.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
        user_status = cur.fetchone()
        
    if user_status and user_status[0] == 1:
        try: bot.answer_callback_query(call.id, "🚫 Siz bloklangansiz!", show_alert=True)
        except Exception: pass
        return
    
    if check_all_subs(user_id):
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        msg_text = f"🎉 Obuna tasdiqlandi!\n\n" + get_welcome_text(first_name)
        try: bot.send_photo(call.message.chat.id, photo=START_IMAGE_URL, caption=msg_text, reply_markup=main_menu_markup(user_id))
        except Exception: pass
    else:
        try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=sub_menu_markup(user_id))
        except Exception: pass 
        try: bot.answer_callback_query(call.id, "❌ Hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
        except Exception: pass

# --- ADMIN BUYRUQLARI ---

# YANGI: PROMOKOD YARATISH BUYRUG'I
@bot.message_handler(commands=['makepromo'])
def make_promo_cmd(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        code = args[1].upper()
        uses = int(args[2])
        reward = int(args[3])
        with db_lock:
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO promocodes (code, uses, reward) VALUES (?, ?, ?)", (code, uses, reward))
        bot.reply_to(message, f"✅ **Promokod yaratildi va Baza ga yozildi!**\n\n🎟 Kod: `{code}`\n👥 Limit: {uses} kishi\n💰 Yutuq: {reward:,} Loot", parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "⚠️ Xato format!\nTo'g'ri usul: /makepromo KOD LIMIT YUTUQ\nMasalan: /makepromo UZC2026 50 1000000")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS: return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"))
    markup.add(InlineKeyboardButton("📨 Hammaga xabar yuborish", callback_data="admin_broadcast"))
    try: bot.send_message(message.chat.id, "🛡 **Admin Panelga xush kelibsiz!**", reply_markup=markup, parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callbacks(call):
    if call.from_user.id not in ADMIN_IDS: return
    try: bot.answer_callback_query(call.id)
    except Exception: pass

    if call.data == "admin_stats":
        with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(user_id) FROM users")
            total_users = cur.fetchone()[0]
        try: bot.send_message(call.message.chat.id, f"📊 **Umumiy Statistika:**\n👥 Botdagi foydalanuvchilar: {total_users} ta", parse_mode="Markdown")
        except Exception: pass
    elif call.data == "admin_broadcast":
        try:
            msg = bot.send_message(call.message.chat.id, "📨 Yubormoqchi bo'lgan xabaringizni yozing.\nBekor qilish uchun /cancel")
            bot.register_next_step_handler(msg, process_broadcast)
        except Exception: pass

def process_broadcast(message):
    if message.text == '/cancel':
        try: bot.send_message(message.chat.id, "❌ Rassilka bekor qilindi.")
        except Exception: pass
        return
    try: bot.send_message(message.chat.id, "⏳ Xabar orqa fonda tarqatilmoqda...")
    except Exception: pass
    Thread(target=run_broadcast, args=(message,), daemon=True).start()

def run_broadcast(message):
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        users = cur.fetchall()
    success, fail = 0, 0
    for user in users:
        try:
            bot.copy_message(user[0], message.chat.id, message.message_id)
            success += 1
            time.sleep(0.05)
        except Exception: fail += 1
    try: bot.send_message(message.chat.id, f"✅ **Rassilka yakunlandi!**\n\n🟢 Yetib bordi: {success} ta\n🔴 Bloklaganlar: {fail} ta", parse_mode="Markdown")
    except Exception: pass

@bot.message_handler(commands=['setloot'])
def set_loot_admin(message):
    if message.from_user.id not in ADMIN_IDS: return 
    try:
        args = message.text.split()
        target_id, amount = int(args[1]), int(args[2])
        with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT score FROM users WHERE user_id=?", (target_id,))
            if cur.fetchone():
                cur.execute("UPDATE users SET score=? WHERE user_id=?", (amount, target_id))
                update_rating_json()
                bot.reply_to(message, f"✅ Muvaffaqiyatli!\n🆔 {target_id} hisobi {amount} loot qilib belgilandi.")
            else: bot.reply_to(message, "❌ Foydalanuvchi bazadan topilmadi!")
    except Exception: bot.reply_to(message, "⚠️ Xato format! /setloot ID MIQDOR")

@bot.message_handler(commands=['give'])
def give_loot_admin(message):
    if message.from_user.id not in ADMIN_IDS: return 
    try:
        args = message.text.split()
        target_id, amount = int(args[1]), int(args[2])
        with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT score FROM users WHERE user_id=?", (target_id,))
            result = cur.fetchone()
            if result:
                new_score = result[0] + amount
                cur.execute("UPDATE users SET score=? WHERE user_id=?", (new_score, target_id))
                update_rating_json()
                bot.reply_to(message, f"✅ {target_id} egasiga {amount} loot qo'shildi.")
            else: bot.reply_to(message, "❌ Topilmadi!")
    except Exception: bot.reply_to(message, "⚠️ Xato! /give ID MIQDOR")

@bot.message_handler(commands=['giveref'])
def give_ref_admin(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        target_id, amount = int(message.text.split()[1]), int(message.text.split()[2])
        with db_lock:
            cur = conn.cursor()
            cur.execute("UPDATE users SET referrals = referrals + ? WHERE user_id = ?", (amount, target_id))
        update_rating_json()
        bot.reply_to(message, f"✅ {target_id} ga {amount} ta do'st qo'shildi!")
    except Exception: bot.reply_to(message, "⚠️ Xato! /giveref ID SONI")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        target_id = int(message.text.split()[1])
        with db_lock:
            cur = conn.cursor()
            cur.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target_id,))
        bot.reply_to(message, f"🚫 Bloklandi! ID: {target_id}")
    except Exception: bot.reply_to(message, "To'g'ri usul: /ban ID raqami")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        target_id = int(message.text.split()[1])
        with db_lock:
            cur = conn.cursor()
            cur.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target_id,))
        bot.reply_to(message, f"✅ Blokdan yechildi! ID: {target_id}")
    except Exception: bot.reply_to(message, "To'g'ri usul: /unban ID raqami")

update_rating_json()
print("💎 LootTap Bot V6.0 ishga tushdi! Baza va Kassa tizimi ulandi...")

Thread(target=rating_auto_updater, daemon=True).start()
keep_alive()

try:
    bot.remove_webhook()
    time.sleep(1)
except Exception: pass

bot.infinity_polling(skip_pending=True)
