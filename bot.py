import os
import asyncio
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters, MessageHandler, CallbackContext
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest
import sqlite3

# ===== تنظیمات =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_IDS = [8518256437]
# ===================

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# ===== دیتابیس =====
conn = sqlite3.connect('userbot.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS sessions
             (user_id INTEGER PRIMARY KEY, session_string TEXT, is_active INTEGER)''')
conn.commit()

# ===== کلاینت Telethon =====
user_clients = {}  # {user_id: client}

# ===== منوی اصلی =====
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        update.message.reply_text("❌ شما دسترسی ندارید!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📲 ورود با شماره", callback_data="login")],
        [InlineKeyboardButton("🔄 تغییر اسم", callback_data="change_name")],
        [InlineKeyboardButton("📊 وضعیت سلف", callback_data="status")],
        [InlineKeyboardButton("⏹ غیرفعال کردن", callback_data="stop")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "🤖 **پنل مدیریت سلف‌بات**\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ===== ورود با شماره =====
def login(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    context.user_data['mode'] = 'login_phone'
    query.edit_message_text(
        "📲 **ورود به اکانت تلگرام**\n\n"
        "لطفاً شماره تلفن خود را با کد کشور وارد کنید:\n"
        "مثال: `+989123456789`\n\n"
        "برای لغو، /cancel را بزنید.",
        parse_mode='Markdown'
    )

# ===== تغییر اسم =====
async def change_name(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    
    if user_id not in user_clients:
        query.edit_message_text("❌ ابتدا وارد اکانت شوید!")
        return
    
    context.user_data['mode'] = 'change_name'
    query.edit_message_text(
        "🔄 **تغییر اسم**\n\n"
        "لطفاً اسم جدید را وارد کنید:",
        parse_mode='Markdown'
    )

# ===== وضعیت سلف =====
def status(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    
    if user_id in user_clients:
        query.edit_message_text("✅ سلف‌بات فعال است و به اکانت متصل است.")
    else:
        query.edit_message_text("❌ سلف‌بات غیرفعال است.")

# ===== غیرفعال کردن =====
def stop_userbot(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    
    if user_id in user_clients:
        client = user_clients[user_id]
        client.disconnect()
        del user_clients[user_id]
        query.edit_message_text("⏹ سلف‌بات با موفقیت غیرفعال شد!")
    else:
        query.edit_message_text("❌ سلف‌بات در حال حاضر غیرفعال است.")

# ===== پردازش پیام‌ها =====
def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    mode = context.user_data.get('mode')
    
    if mode == 'login_phone':
        context.user_data['phone'] = text
        context.user_data['mode'] = 'login_code'
        update.message.reply_text("📲 کد تایید به شماره شما ارسال شد. لطفاً کد را وارد کنید:")
        
        # شروع فرآیند ورود
        asyncio.create_task(send_code(user_id, text))
    
    elif mode == 'login_code':
        code = text
        phone = context.user_data.get('phone')
        if not phone:
            update.message.reply_text("❌ خطا! لطفاً دوباره با /start شروع کنید.")
            return
        
        asyncio.create_task(complete_login(user_id, phone, code))
        context.user_data['mode'] = None
    
    elif mode == 'change_name':
        new_name = text
        asyncio.create_task(change_name_task(user_id, new_name))
        context.user_data['mode'] = None
    
    else:
        update.message.reply_text("👈 لطفاً از منوی اصلی استفاده کنید یا /start را بزنید.")

# ===== توابع Async =====
async def send_code(user_id, phone):
    try:
        # ایجاد کلاینت با تنظیمات پیش‌فرض (API داخلی)
        client = TelegramClient(f'session_{user_id}', 2040, 'b18441a1ff607e10a989891a5462e627')
        await client.start(phone=phone)
        user_clients[user_id] = client
        await bot.send_message(chat_id=user_id, text="✅ کد تایید ارسال شد! لطفاً کد را وارد کنید.")
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال کد: {str(e)}")

async def complete_login(user_id, phone, code):
    try:
        client = TelegramClient(f'session_{user_id}', 2040, 'b18441a1ff607e10a989891a5462e627')
        await client.start(phone=phone, code_callback=lambda: code)
        
        # ذخیره جلسه
        session_string = client.session.save()
        c.execute("INSERT OR REPLACE INTO sessions (user_id, session_string, is_active) VALUES (?, ?, ?)",
                  (user_id, session_string, 1))
        conn.commit()
        
        user_clients[user_id] = client
        await bot.send_message(chat_id=user_id, text="✅ ورود با موفقیت انجام شد!")
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=f"❌ خطا در ورود: {str(e)}")

async def change_name_task(user_id, new_name):
    try:
        if user_id not in user_clients:
            await bot.send_message(chat_id=user_id, text="❌ ابتدا وارد اکانت شوید!")
            return
        
        client = user_clients[user_id]
        await client(UpdateProfileRequest(first_name=new_name))
        await bot.send_message(chat_id=user_id, text=f"✅ اسم با موفقیت به '{new_name}' تغییر کرد!")
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=f"❌ خطا: {str(e)}")

# ===== ثبت هندلرها =====
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(login, pattern="login"))
dispatcher.add_handler(CallbackQueryHandler(change_name, pattern="change_name"))
dispatcher.add_handler(CallbackQueryHandler(status, pattern="status"))
dispatcher.add_handler(CallbackQueryHandler(stop_userbot, pattern="stop"))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# ===== Webhook =====
@app.route("/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def health():
    return "🤖 SELF-BOT is running!", 200

if __name__ == "__main__":
    WEBHOOK_URL = "https://m-2-87zo.onrender.com/"
    bot.set_webhook(WEBHOOK_URL)
    print("🤖 سلف‌بات روشن شد!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
