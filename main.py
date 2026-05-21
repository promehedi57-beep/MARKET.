import telebot
from telebot import types
import sqlite3
import html 
from flask import Flask
from threading import Thread

# ==========================================
# ⚙️ কনফিগারেশন (নতুন টোকেন ও এডমিন লিস্ট সহ)
# ==========================================
API_TOKEN = '8919105692:AAFjlrpnlcXNHvht3TyP7Mx8ngp1ReJSN1U'
ADMIN_IDS = [7689218221, 6820798198] # উভয় এডমিন আইডি এখানে যুক্ত
ADMIN_USERNAME = "FBSKYSUPPORT" 
BKASH_NUMBER = "01742958563"

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")
user_states = {}

MENU_BUTTONS = ["🛒 𝐁𝐮𝐲 𝐅𝐁 𝐈𝐃", "👤  𝐌𝐲 𝐏𝐫𝐨𝐟𝐢𝐥𝐞", "💳 𝐀𝐝𝐝 𝐌𝐨𝐧𝐞𝐲", "📞 𝐒𝐮𝐩𝐩𝐨𝐫𝐭 & 𝐇𝐞𝐥𝐩", "🛡️ 𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐞𝐥"]

# ==========================================
# 🗄️ ডাটাবেস ম্যানেজমেন্ট 
# ==========================================
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect('fbid_pro_master_final.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)''')
    db_query('''CREATE TABLE IF NOT EXISTS deposits (dep_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, trx_id TEXT, photo_id TEXT, status TEXT DEFAULT 'Pending')''')
    db_query('''CREATE TABLE IF NOT EXISTS custom_orders (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, qty INTEGER, status TEXT DEFAULT 'Pending')''')
    db_query('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    db_query('''INSERT OR IGNORE INTO settings (key, value) VALUES ('id_price', '10.0')''')
    db_query('''INSERT OR IGNORE INTO settings (key, value) VALUES ('min_deposit', '10.0')''') # মিনিমাম ডিপোজিটের ডিফল্ট ভ্যালু
    
    # ডাটাবেস অটো ফিক্স কলাম চেক
    try:
        db_query("ALTER TABLE custom_orders ADD COLUMN user_pass TEXT")
        print("✅ Database Updated: 'user_pass' column verified/added!")
    except sqlite3.OperationalError:
        pass 

init_db()

def get_id_price():
    res = db_query("SELECT value FROM settings WHERE key='id_price'", fetch=True)
    return float(res[0][0]) if res else 10.0

def get_min_deposit():
    res = db_query("SELECT value FROM settings WHERE key='min_deposit'", fetch=True)
    return float(res[0][0]) if res else 10.0

# সকল এডমিনকে একসাথে মেসেজ বা নোটিফিকেশন পাঠানোর ফাংশন
def notify_admins(text, photo_id=None, reply_markup=None):
    for admin in ADMIN_IDS:
        try:
            if photo_id:
                bot.send_photo(admin, photo_id, caption=text, reply_markup=reply_markup)
            else:
                bot.send_message(admin, text, reply_markup=reply_markup)
        except Exception as e:
            print(f"Failed to notify admin {admin}: {e}")

# ==========================================
# 🎨 UI ও প্রধান মেনু
# ==========================================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🛒 𝐁𝐮𝐲 𝐅𝐁 𝐈𝐃"), 
        types.KeyboardButton("👤  𝐌𝐲 𝐏𝐫𝐨𝐟𝐢𝐥𝐞"),
        types.KeyboardButton("💳 𝐀𝐝𝐝 𝐌𝐨𝐧𝐞𝐲"), 
        types.KeyboardButton("📞 𝐒𝐮𝐩𝐩𝐨𝐫𝐭 & 𝐇𝐞𝐥𝐩")
    )
    if user_id in ADMIN_IDS:
        markup.add(types.KeyboardButton("🛡️ 𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐞𝐥"))
    return markup

def admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛠️ 𝐏e𝐧𝐝𝐢𝐧𝐠 𝐂𝐮𝐬𝐭𝐨𝐦 𝐎𝐫𝐝𝐞𝐫𝐬", callback_data="adm_view_custom"),
        types.InlineKeyboardButton("💰 𝐂𝐡𝐚𝐧𝐠𝐞 𝐈𝐃 𝐏𝐫𝐢𝐜𝐞", callback_data="adm_change_price"),
        types.InlineKeyboardButton("💳 𝐂𝐡𝐚𝐧𝐠𝐞 𝐌𝐢𝐧 𝐃e𝐩𝐨𝐬𝐢𝐭", callback_data="adm_change_min_dep"), # নতুন বাটন
        types.InlineKeyboardButton("⏳ 𝐏e𝐧𝐝𝐢𝐧𝐠 𝐃e𝐩𝐨𝐬𝐢𝐭𝐬", callback_data="adm_view_dep")
    )
    return markup

# ==========================================
# 🚀 বেসিক কমান্ডস 
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    user_states.pop(message.from_user.id, None)
    db_query('INSERT OR IGNORE INTO users (id) VALUES (?)', (message.from_user.id,))
    welcome_text = f"🌟 <b>হ্যালো {html.escape(message.from_user.first_name)}!</b>\nসাখাওয়াত ভাইয়ের অফিসিয়াল কাস্টম আইডিশপ বটে আপনাকে 𝐖𝐞𝐥𝐜𝐨𝐦𝐞।\n\n👇 <i>নিচের মেনু থেকে আপনার অপশনটি বেছে নিন:</i>"
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(message.from_user.id))

# ==========================================
# 🎯 মেইন মেনু হ্যান্ডলার
# ==========================================
@bot.message_handler(func=lambda m: m.text == "🛒 𝐁𝐮𝐲 𝐅𝐁 𝐈𝐃")
def buy_id(message):
    user_states.pop(message.from_user.id, None)
    p = get_id_price()
    user_states[message.from_user.id] = {'state': 'BUY_QTY'}
    bot.send_message(message.chat.id, f"🛒 <b>ফেসবুক কাস্টম আইডি অর্ডার</b>\n📌 <b>প্রাইস:</b> {p}৳ / 𝐈𝐃\n\n🔢 আপনি কয়টি আইডি নিতে চাচ্ছেন? (সংখ্যা লিখুন):")

@bot.message_handler(func=lambda m: m.text == "💳 𝐀𝐝𝐝 𝐌𝐨𝐧𝐞𝐲")
def add_money(message):
    user_states.pop(message.from_user.id, None)
    min_dep = get_min_deposit()
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ আমি টাকা পাঠিয়েছি", callback_data="dep_step1"))
    bot.send_message(message.chat.id, f"💳 <b>বিকাশ পেমেন্ট (𝐒𝐞𝐧𝐝 𝐌𝐨𝐧𝐞𝐲)</b>\n━━━━━━━━━━━━━━━━━━━━\n🔹 <b>নাম্বার:</b> <code>{BKASH_NUMBER}</code>\n⚠️ <b>মিনিমাপ ডিপোজিট:</b> {min_dep}৳", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "👤  𝐌𝐲 𝐏𝐫𝐨𝐟𝐢𝐥𝐞")
def profile(message):
    user_states.pop(message.from_user.id, None)
    bal_res = db_query("SELECT balance FROM users WHERE id=?", (message.from_user.id,), fetch=True)
    bal = bal_res[0][0] if bal_res else 0.0
    profile_text = f"👤 <b>আপনার প্রোফাইল</b>\n🆔 <b>একাউন্ট 𝐈𝐃:</b> <code>{message.from_user.id}</code>\n💰 <b>বর্তমান ব্যালেন্স:</b> {bal}৳"
    bot.send_message(message.chat.id, profile_text)

@bot.message_handler(func=lambda m: m.text == "📞 𝐒𝐮𝐩𝐩𝐨𝐫𝐭 & 𝐇𝐞𝐥𝐩")
def support(message):
    user_states.pop(message.from_user.id, None)
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("👑 𝐎𝐖𝐍𝐄𝐑 𝐒𝐔𝐏𝐏𝐎𝐑𝐓", url="https://t.me/SKYSMSOWNER"),
        types.InlineKeyboardButton("👨‍💻 𝐀𝐃𝐌𝐈𝐍 𝐒𝐔𝐏𝐏𝐎𝐑𝐓", url=f"https://t.me/{ADMIN_USERNAME}")
    )
    bot.send_message(message.chat.id, "📞 <b>𝐒𝐮𝐩𝐩𝐨𝐫𝐭 𝐂e𝐧𝐭e𝐫</b>", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🛡️ 𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧e𝐥")
def admin_p(message):
    user_states.pop(message.from_user.id, None)
    if message.from_user.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "🛠️ <b>𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧e𝐥</b>", reply_markup=admin_menu())

# ==========================================
# 💳 ডিপোজিট ফ্লো (মিনিমাম লিমিট চেক সহ)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "dep_step1")
def dep_amt(call):
    bot.answer_callback_query(call.id)
    user_states[call.from_user.id] = {'state': 'AMT'}
    bot.edit_message_text("💰 আপনি <b>কত টাকা</b> পাঠিয়েছেন? (ইংরেজিতে শুধু সংখ্যা লিখুন):", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'AMT' and m.text not in MENU_BUTTONS)
def dep_trx(message):
    try:
        amount = float(message.text)
        min_dep = get_min_deposit()
        
        if amount < min_dep:
            bot.send_message(message.chat.id, f"❌ <b>দুঃখিত, মিনিমাম ডিপোজিট {min_dep}৳।</b>\nদয়া করে এর সমান বা বেশি অ্যামাউন্ট লিখে আবার পাঠান:")
            return 
            
        user_states[message.from_user.id] = {'state': 'TRX', 'amt': amount}
        bot.send_message(message.chat.id, "📝 এবার আপনার পেমেন্টের <b>𝐓𝐫𝐚𝐧𝐬𝐚𝐜𝐭𝐢𝐨𝐧 𝐈𝐃 (𝐓𝐫𝐱𝐈𝐃)</b> দিন:")
    except: 
        bot.send_message(message.chat.id, "❌ দয়া করে শুধুমাত্র সংখ্যা লিখুন।")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'TRX' and m.text not in MENU_BUTTONS)
def dep_photo(message):
    user_states[message.from_user.id].update({'state': 'PHOTO', 'trx': html.escape(message.text)})
    bot.send_message(message.chat.id, "📸 পেমেন্ট প্রমাণের জন্য একটি <b>스크린샷 (𝐒𝐜𝐫𝐞e𝐧𝐬𝐡𝐨𝐭)</b> দিন:")

@bot.message_handler(content_types=['photo'], func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'PHOTO')
def dep_final(message):
    uid, data = message.from_user.id, user_states[message.from_user.id]
    db_query("INSERT INTO deposits (user_id, amount, trx_id, photo_id) VALUES (?, ?, ?, ?)", (uid, data['amt'], data['trx'], message.photo[-1].file_id))
    user_states.pop(uid, None)
    bot.send_message(message.chat.id, "✅ <b>রিকোয়েস্ট সফলভাবে জমা হয়েছে!</b>")

# ==========================================
# 🛒 কাস্টম বাই ফ্লো
# ==========================================
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'BUY_QTY' and m.text not in MENU_BUTTONS)
def buy_qty_received(message):
    uid = message.from_user.id
    try:
        qty = int(message.text)
        if qty <= 0: raise ValueError
        
        user_states[uid] = {'state': 'BUY_PASS', 'qty': qty}
        bot.send_message(message.chat.id, "🔑 <b>আপনার পাসওয়ার্ড দিন:</b>\nআপনি এই আইডিগুলোতে যে পাসওয়ার্ডটি ব্যবহার করতে চান, সেটি টাইপ করে দিন:")
    except:
        bot.send_message(message.chat.id, "❌ দয়া করে সঠিক সংখ্যা লিখুন।")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'BUY_PASS' and m.text not in MENU_BUTTONS)
def buy_pass_received(message):
    uid = message.from_user.id
    user_pass = html.escape(message.text) 
    qty = user_states[uid]['qty']
    cost = qty * get_id_price()
    
    user_states[uid].update({'state': 'BUY_CONFIRM', 'pass': user_pass, 'cost': cost})
    
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("✅ 𝐂𝐨𝐧𝐟𝐢𝐫𝐦", callback_data="confirm_order"),
        types.InlineKeyboardButton("❌ 𝐂𝐚𝐧𝐜e𝐥", callback_data="cancel_order")
    )
    
    confirm_text = f"📊 <b>অর্ডার কনফার্মেশন</b>\n━━━━━━━━━━━━━━━━━━━━\n🔢 <b>আইডির পরিমাণ:</b> {qty} টি\n🔑 <b>আপনার দেওয়া পাসওয়ার্ড:</b> <code>{user_pass}</code>\n💰 <b>মোট খরচ:</b> {cost}৳\n\nআপনি কি এই অর্ডারটি কনফার্ম করতে চান?"
    bot.send_message(message.chat.id, confirm_text, reply_markup=mk)

# ==========================================
# 🛑 Crash Proof Confirm / Cancel Handler
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data in ["confirm_order", "cancel_order"])
def handle_confirmation(call):
    uid = call.from_user.id
    
    try:
        if uid not in user_states or user_states[uid].get('state') != 'BUY_CONFIRM':
            bot.answer_callback_query(call.id, "❌ সেশন শেষ হয়ে গেছে।", show_alert=True)
            return
        
        if call.data == "cancel_order":
            user_states.pop(uid, None)
            bot.answer_callback_query(call.id)
            bot.edit_message_text("❌ <b>অর্ডারটি বাতিল করা হয়েছে।</b>", call.message.chat.id, call.message.message_id)
            return
            
        data = user_states[uid]
        bal_res = db_query("SELECT balance FROM users WHERE id=?", (uid,), fetch=True)
        bal = bal_res[0][0] if bal_res else 0.0
        
        if bal < data['cost']:
            user_states.pop(uid, None)
            bot.answer_callback_query(call.id, "❌ আপনার ব্যালেন্স অপর্যাপ্ত!", show_alert=True)
            bot.edit_message_text(f"❌ <b>আপনার ব্যালেন্স অপর্যাপ্ত!</b>\nটোটাল খরচ {data['cost']}৳, কিন্তু আপনার আছে {bal}৳।", call.message.chat.id, call.message.message_id)
            return
            
        db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (data['cost'], uid))
        db_query("INSERT INTO custom_orders (user_id, qty, user_pass) VALUES (?, ?, ?)", (uid, data['qty'], data['pass']))
        
        bot.answer_callback_query(call.id)
        bot.edit_message_text(f"✅ <b>আপনার অর্ডারটি সফলভাবে সাবমিট হয়েছে!</b>\nএডমিন আইডিগুলো তৈরি করে শীঘ্রই এই চ্যাটে ফাইল পাঠিয়ে দিবে।", call.message.chat.id, call.message.message_id)
        
        admin_alert = f"🔔 <b>নতুন পেন্ডিং কাস্টম অর্ডার এসেছে!</b>\n👤 ইউজার 𝐈𝐃: <code>{uid}</code>\n🔢 পরিমাণ: {data['qty']} টি\n🔑 পাসওয়ার্ড: <code>{data['pass']}</code>"
        notify_admins(admin_alert)
        
        user_states.pop(uid, None)

    except Exception as e:
        print(f"Crash Prevented in Confirm/Cancel: {e}")
        bot.answer_callback_query(call.id, "❌ সাময়িক সমস্যা হয়েছে, আবার চেষ্টা করুন।", show_alert=True)

# ==========================================
# 🛡️ Admin Panel & File Delivery
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def admin_calls(call):
    aid = call.from_user.id
    if aid not in ADMIN_IDS: return
    
    cmd = call.data.split('_')
    
    try:
        if call.data == "adm_change_price":
            bot.answer_callback_query(call.id)
            user_states[aid] = {'state': 'CHANGE_PRICE'}
            bot.send_message(aid, "💰 নতুন দাম লিখে সেন্ড করুন:")

        elif call.data == "adm_change_min_dep":
            bot.answer_callback_query(call.id)
            user_states[aid] = {'state': 'CHANGE_MIN_DEPOSIT'}
            bot.send_message(aid, "💳 নতুন মিনিমাম ডিপোজিট অ্যামাউন্ট লিখে সেন্ড করুন (শুধু সংখ্যা):")

        elif call.data == "adm_view_dep":
            pending = db_query("SELECT dep_id, user_id, amount, trx_id, photo_id FROM deposits WHERE status='Pending'", fetch=True)
            if not pending: return bot.answer_callback_query(call.id, "✅ কোনো পেন্ডিং ডিপোজিট নেই।", show_alert=True)
            bot.answer_callback_query(call.id)
            for dep in pending:
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton("✅ 𝐀𝐩𝐩𝐫𝐨𝐯𝐞", callback_data=f"adm_app_{dep[0]}"), types.InlineKeyboardButton("❌ 𝐑e𝐣e𝐜𝐭", callback_data=f"adm_rej_{dep[0]}"))
                bot.send_photo(aid, dep[4], caption=f"🔔 <b>𝐏e𝐧𝐝𝐢𝐧𝐠 𝐃e𝐩𝐨𝐬𝐢𝐭</b>\n𝐈𝐃: <code>{dep[1]}</code>\n𝐀𝐦𝐨𝐮𝐧𝐭: {dep[2]}৳\n𝐓𝐫𝐱𝐈𝐃: <code>{dep[3]}</code>", reply_markup=mk)

        elif call.data == "adm_view_custom":
            orders = db_query("SELECT order_id, user_id, qty, user_pass FROM custom_orders WHERE status='Pending'", fetch=True)
            if not orders: return bot.answer_callback_query(call.id, "✅ কোনো পেন্ডিং কাস্টম অর্ডার নেই।", show_alert=True)
            bot.answer_callback_query(call.id)
            for o in orders:
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton("📁 𝐔𝐩𝐥𝐨𝐚𝐝 𝐈𝐃𝐬 & 𝐃e𝐥𝐢𝐯e𝐫", callback_data=f"adm_cdeliv_{o[0]}_{o[1]}"))
                order_msg = f"🛠️ <b>𝐏e𝐧𝐝𝐢𝐧𝐠 𝐂𝐮𝐬𝐭𝐨𝐦 𝐎𝐫𝐝e𝐫</b>\n━━━━━━━━━━━━━━━━━━━━\n🔹 <b>𝐎𝐫𝐝e𝐫 𝐈𝐃:</b> {o[0]}\n👤 <b>𝐔𝐬e𝐫 𝐈𝐃:</b> <code>{o[1]}</code>\n🔢 <b>পরিমাণ:</b> {o[2]} টি\n🔑 <b>পাসওয়ার্ড:</b> <code>{o[3]}</code>"
                bot.send_message(aid, order_msg, reply_markup=mk)

        elif cmd[1] == "cdeliv":
            bot.answer_callback_query(call.id)
            o_id, u_id = cmd[2], cmd[3]
            user_states[aid] = {'state': 'SEND_CUSTOM_FILE', 'o_id': o_id, 'u_id': u_id}
            bot.send_message(aid, f"🚀 ইউজার <code>{u_id}</code>-এর জন্য কাস্টম আইডির <b>ফাইলটি (.txt/.csv) দিন</b> অথবা টেক্সট আকারে মেসেজে লিখে পাঠান:")

        elif cmd[1] == "app":
            bot.answer_callback_query(call.id, "ডিপোজিট এপ্রুভ করা হয়েছে!")
            res = db_query("SELECT user_id, amount FROM deposits WHERE dep_id=?", (cmd[2],), fetch=True)
            if res:
                db_query("UPDATE users SET balance = balance + ? WHERE id=?", (res[0][1], res[0][0]))
                db_query("UPDATE deposits SET status='Done' WHERE dep_id=?", (cmd[2],))
                bot.send_message(res[0][0], f"🎉 আপনার <b>{res[0][1]}৳</b> সফলভাবে একাউন্টে এড করা হয়েছে!")
                bot.edit_message_caption("✅ 𝐀𝐩𝐩𝐫𝐨𝐯e𝐝 (𝐃𝐨𝐧e)", call.message.chat.id, call.message.message_id)

        elif cmd[1] == "rej":
            bot.answer_callback_query(call.id, "ডিপোজিট রিজেক্ট করা হয়েছে!")
            db_query("UPDATE deposits SET status='Rejected' WHERE dep_id=?", (cmd[2],))
            bot.edit_message_caption("❌ 𝐑e𝐣e𝐜𝐭e𝐝", call.message.chat.id, call.message.message_id)
            
    except Exception as e:
        print(f"Error in Admin Call: {e}")
        bot.answer_callback_query(call.id, "❌ একটি সমস্যা হয়েছে।")

def is_admin_input_state(m):
    if m.from_user.id not in ADMIN_IDS: return False
    return user_states.get(m.from_user.id, {}).get('state') in ['SEND_CUSTOM_FILE', 'CHANGE_PRICE', 'CHANGE_MIN_DEPOSIT']

@bot.message_handler(content_types=['text', 'document'], func=is_admin_input_state)
def admin_input_handler(message):
    aid = message.from_user.id
    state_data = user_states.get(aid)
    
    try:
        if state_data['state'] == 'CHANGE_PRICE':
            db_query("UPDATE settings SET value=? WHERE key='id_price'", (html.escape(message.text),))
            bot.send_message(aid, "✅ আইডি প্রাইস সফলভাবে আপডেট হয়েছে।")
            user_states.pop(aid, None)

        elif state_data['state'] == 'CHANGE_MIN_DEPOSIT':
            try:
                val = float(message.text)
                db_query("UPDATE settings SET value=? WHERE key='min_deposit'", (str(val),))
                bot.send_message(aid, f"✅ মিনিমাম ডিপোজিট আপডেট হয়ে {val}৳ সেট হয়েছে।")
                user_states.pop(aid, None)
            except:
                bot.send_message(aid, "❌ ভুল ইনপুট। দয়া করে শুধু সংখ্যা লিখুন।")

        elif state_data['state'] == 'SEND_CUSTOM_FILE':
            u_id = state_data['u_id']
            o_id = state_data['o_id']
            
            if message.content_type == 'document':
                bot.send_document(u_id, message.document.file_id, caption="✅ <b>আপনার কাস্টম অর্ডারের ফাইলটি ডেলিভারি করা হয়েছে!</b>\nসাখাওয়াত ভাইয়ের শপ থেকে কেনার জন্য ধন্যবাদ। 🥰")
            else:
                bot.send_message(u_id, f"✅ <b>আপনার কাস্টম অর্ডারের ফেসবুক আইডি ডেলিভারি:</b>\n\n<code>{html.escape(message.text)}</code>\n\nসাখাওয়াত ভাইয়ের শপ থেকে কেনার জন্য ধন্যবাদ। 🥰")
                
            db_query("UPDATE custom_orders SET status='Done' WHERE order_id=?", (o_id,))
            bot.send_message(aid, f"🚀 সফল! ইউজার <code>{u_id}</code>-কে আইডি ডেলিভারি করা হয়েছে এবং অর্ডার ক্লোজ হয়েছে।")
            user_states.pop(aid, None)
            
    except Exception as e:
        bot.send_message(aid, f"❌ ডেলিভারিতে সমস্যা হয়েছে: {str(e)}")

# ==========================================
# 🌐 রেন্ডার কিপ-অ্যালাইভ ওয়েব সার্ভার (নতুন যুক্ত)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "🚀 SAKHAWAT BHAI, YOUR BOT IS LIVE 24/7!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# 🏁 বটের মেইন রানার ব্লক
# ==========================================
if __name__ == "__main__":
    keep_alive() # রেন্ডারের জন্য ওয়েব সার্ভার ব্যাকগ্রাউন্ডে স্টার্ট করবে
    print("🚀 𝐒𝐇𝐀𝐊𝐀𝐘𝐀𝐓𝐇 𝐁𝐇𝐀𝐈, 𝐓𝐖𝐎-𝐀𝐃𝐌𝐈𝐍 & 𝐌𝐈𝐍-𝐃𝐄𝐏𝐎𝐒𝐈𝐓 𝐁𝐎𝐓 𝐈𝐒 𝐑𝐔𝐍𝐍𝐈𝐍𝐆!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
