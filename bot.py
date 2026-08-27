import os
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from huggingface_hub import InferenceClient

# ===== تنظیمات (همه چیز از متغیرهای محیطی) =====
TOKEN = os.environ.get("BOT_TOKEN")  # توکن ربات از Render
ADMIN_IDS = [8518256437]  # آیدی ادمین‌ها (همون خودت)
HF_TOKEN = os.environ.get("HF_TOKEN")  # توکن Hugging Face از Render
# ===================

app = Flask(__name__)
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher
client = InferenceClient(token=HF_TOKEN)

# ===== دیتابیس ساده (در حافظه) =====
users_data = {}  # {user_id: {'first_seen': date, 'requests': 0, 'banned': False}}
user_requests = {}  # {user_id: {'chat': 5, 'summarize': 3, ...}}
banned_users = set()

# ===== منوی اصلی =====
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # ثبت کاربر جدید
    if user_id not in users_data:
        users_data[user_id] = {
            'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'requests': 0,
            'banned': False
        }
    
    # چک کردن بن
    if user_id in banned_users:
        update.message.reply_text("🚫 شما توسط ادمین بن شده‌اید!")
        return
    
    keyboard = [
        [InlineKeyboardButton("💬 چت با هوش مصنوعی", callback_data="chat")],
        [InlineKeyboardButton("📝 خلاصه‌سازی متن", callback_data="summarize")],
        [InlineKeyboardButton("🎨 تولید عکس با AI", callback_data="image")],
        [InlineKeyboardButton("🌐 ترجمه آنی", callback_data="translate")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    
    # دکمه‌های ادمین (فقط برای ادمین‌ها)
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ پنل ادمین", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "✨ **به ربات هوشمند خوش آمدی!** ✨\n\n"
        "🤖 من یک ربات با هوش مصنوعی هستم که می‌توانم:\n"
        "• با تو گفتگو کنم\n"
        "• متن‌های طولانی را خلاصه کنم\n"
        "• عکس‌های زیبا بسازم\n"
        "• متون را ترجمه کنم\n\n"
        "📌 لطفاً یکی از گزینه‌های زیر را انتخاب کن:"
    )
    
    update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# ===== پنل ادمین =====
def admin_panel(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        update.callback_query.answer("❌ شما دسترسی ندارید!", show_alert=True)
        return
    
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_stats")],
        [InlineKeyboardButton("📜 مشاهده لاگ", callback_data="admin_log")],
        [InlineKeyboardButton("🚫 بن کردن کاربر", callback_data="admin_ban")],
        [InlineKeyboardButton("✅ رفع بن کاربر", callback_data="admin_unban")],
        [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "⚙️ **پنل مدیریت ربات**\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# ===== آمار کاربران =====
def admin_stats(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    total_users = len(users_data)
    banned_count = len(banned_users)
    total_requests = sum(u['requests'] for u in users_data.values())
    
    stats_text = (
        "📊 **آمار ربات**\n\n"
        f"👥 تعداد کل کاربران: {total_users}\n"
        f"🚫 کاربران بن شده: {banned_count}\n"
        f"📨 مجموع درخواست‌ها: {total_requests}\n"
        f"🕐 آخرین به‌روزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# ===== مشاهده لاگ =====
def admin_log(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    # ۱۰ کاربر آخر
    recent_users = list(users_data.keys())[-10:]
    log_text = "📜 **۱۰ کاربر آخر:**\n\n"
    
    for i, user_id in enumerate(recent_users, 1):
        user_data = users_data.get(user_id, {})
        log_text += f"{i}. آیدی: `{user_id}`\n"
        log_text += f"   اولین بازدید: {user_data.get('first_seen', 'نامشخص')}\n"
        log_text += f"   تعداد درخواست: {user_data.get('requests', 0)}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if len(log_text) > 4000:
        log_text = log_text[:4000] + "..."
    
    query.edit_message_text(log_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# ===== بن کردن کاربر =====
def admin_ban(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    context.user_data['admin_action'] = 'ban'
    query.edit_message_text(
        "🚫 **بن کردن کاربر**\n\n"
        "لطفاً آیدی عددی کاربر مورد نظر را بفرستید:\n"
        "مثال: `123456789`",
        parse_mode=ParseMode.MARKDOWN
    )

# ===== رفع بن کاربر =====
def admin_unban(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    context.user_data['admin_action'] = 'unban'
    query.edit_message_text(
        "✅ **رفع بن کاربر**\n\n"
        "لطفاً آیدی عددی کاربر مورد نظر را بفرستید:",
        parse_mode=ParseMode.MARKDOWN
    )

# ===== ارسال پیام همگانی =====
def admin_broadcast(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    context.user_data['admin_action'] = 'broadcast'
    query.edit_message_text(
        "📢 **ارسال پیام همگانی**\n\n"
        "لطفاً پیام مورد نظر را بفرستید:",
        parse_mode=ParseMode.MARKDOWN
    )

# ===== پردازش دکمه‌ها =====
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    
    if user_id in banned_users:
        query.edit_message_text("🚫 شما توسط ادمین بن شده‌اید!")
        return
    
    if query.data == "back_to_menu":
        start(update, context)
        return
    
    if query.data == "admin_panel":
        admin_panel(update, context)
        return
    
    if query.data.startswith("admin_"):
        admin_actions = {
            "admin_stats": admin_stats,
            "admin_log": admin_log,
            "admin_ban": admin_ban,
            "admin_unban": admin_unban,
            "admin_broadcast": admin_broadcast
        }
        if query.data in admin_actions:
            admin_actions[query.data](update, context)
        return
    
    # حالت‌های معمولی
    messages = {
        'chat': "💬 **حالت گفتگو**\n\nلطفاً سوالت را بفرست:",
        'summarize': "📝 **حالت خلاصه‌سازی**\n\nمتن طولانی را بفرست تا خلاصه کنم:",
        'image': "🎨 **حالت تولید عکس**\n\nتوضیحاتی برای عکس مورد نظرت بفرست:",
        'translate': "🌐 **حالت ترجمه**\n\nمتن را بفرست تا به فارسی/انگلیسی ترجمه کنم:",
        'help': (
            "ℹ️ **راهنمای ربات**\n\n"
            "🤖 این ربات با هوش مصنوعی Hugging Face کار می‌کند.\n\n"
            "**قابلیت‌ها:**\n"
            "• چت آزاد با هوش مصنوعی\n"
            "• خلاصه‌سازی متون طولانی\n"
            "• تولید عکس با توضیحات\n"
            "• ترجمه بین فارسی و انگلیسی\n\n"
            "**نکته:** برای بازگشت به منوی اصلی، دستور /start را بزن."
        )
    }
    
    query.edit_message_text(
        messages.get(query.data, "❌ گزینه نامعتبر!"),
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['mode'] = query.data

# ===== پردازش پیام‌ها (با مدیریت ادمین) =====
def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    
    # چک کردن بن
    if user_id in banned_users:
        update.message.reply_text("🚫 شما توسط ادمین بن شده‌اید!")
        return
    
    # ثبت درخواست کاربر
    if user_id not in users_data:
        users_data[user_id] = {'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M"), 'requests': 0, 'banned': False}
    users_data[user_id]['requests'] += 1
    
    # پردازش اقدامات ادمین
    admin_action = context.user_data.get('admin_action')
    if user_id in ADMIN_IDS and admin_action:
        if admin_action == 'ban':
            try:
                target_id = int(text)
                if target_id not in ADMIN_IDS:
                    banned_users.add(target_id)
                    update.message.reply_text(f"✅ کاربر با آیدی `{target_id}` بن شد!")
                else:
                    update.message.reply_text("❌ نمی‌توانید ادمین را بن کنید!")
            except:
                update.message.reply_text("❌ لطفاً یک آیدی عددی معتبر بفرستید!")
            context.user_data['admin_action'] = None
            return
            
        elif admin_action == 'unban':
            try:
                target_id = int(text)
                if target_id in banned_users:
                    banned_users.remove(target_id)
                    update.message.reply_text(f"✅ بن کاربر `{target_id}` برداشته شد!")
                else:
                    update.message.reply_text(f"❌ کاربر `{target_id}` در لیست بن نیست!")
            except:
                update.message.reply_text("❌ لطفاً یک آیدی عددی معتبر بفرستید!")
            context.user_data['admin_action'] = None
            return
            
        elif admin_action == 'broadcast':
            # ارسال پیام به همه کاربران
            count = 0
            for uid in users_data.keys():
                try:
                    bot.send_message(chat_id=uid, text=f"📢 **پیام از طرف ادمین:**\n\n{text}", parse_mode=ParseMode.MARKDOWN)
                    count += 1
                except:
                    pass
            update.message.reply_text(f"✅ پیام به {count} کاربر ارسال شد!")
            context.user_data['admin_action'] = None
            return
    
    # پردازش معمولی پیام‌ها
    mode = context.user_data.get('mode', 'chat')
    processing_msg = update.message.reply_text("⏳ **در حال پردازش...**", parse_mode=ParseMode.MARKDOWN)
    
    try:
        if mode == 'chat':
            response = client.text_generation(
                prompt=f"User: {text}\nAI:",
                model="microsoft/DialoGPT-medium",
                max_new_tokens=250
            )
            result = f"🤖 **پاسخ:**\n{response.generated_text.strip()}"
            
        elif mode == 'summarize':
            response = client.text_generation(
                prompt=f"Summarize this text concisely in Persian: {text}",
                model="facebook/bart-large-cnn",
                max_new_tokens=200
            )
            result = f"📝 **خلاصه:**\n{response.generated_text.strip()}"
            
        elif mode == 'image':
            response = client.text_to_image(
                prompt=text,
                model="black-forest-labs/FLUX.1-schnell"
            )
            bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=response,
                caption=f"🎨 **عکس ساخته شده:**\n{text}"
            )
            processing_msg.delete()
            return
            
        elif mode == 'translate':
            response = client.text_generation(
                prompt=f"Translate this to Persian (if English) or to English (if Persian): {text}",
                model="Helsinki-NLP/opus-mt-en-fa",
                max_new_tokens=200
            )
            result = f"🌐 **ترجمه:**\n{response.generated_text.strip()}"
            
        else:
            result = "❌ حالت نامعتبر! لطفاً از منوی اصلی انتخاب کن."
        
        processing_msg.edit_text(result, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        processing_msg.edit_text(f"❌ **خطا:**\n{str(e)}", parse_mode=ParseMode.MARKDOWN)

# ===== ثبت هندلرها =====
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(button_handler))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# ===== Webhook =====
@app.route("/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def health():
    return "🤖 Bot is running!", 200

if __name__ == "__main__":
    WEBHOOK_URL = "https://m-1-4x8p.onrender.com/"
    bot.set_webhook(WEBHOOK_URL)
    print("🤖 ربات هوشمند با پنل ادمین روشن شد!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
