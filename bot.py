import os
import json
import requests
from datetime import datetime
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from huggingface_hub import InferenceClient

# ===== تنظیمات =====
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_IDS = [8518256437]
HF_TOKEN = os.environ.get("HF_TOKEN")
# ===================

app = Flask(__name__)
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher
client = InferenceClient(token=HF_TOKEN)

# ===== دیتابیس =====
users_data = {}
banned_users = set()

# ===== منوی اصلی =====
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if user_id not in users_data:
        users_data[user_id] = {
            'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'requests': 0
        }
    
    if user_id in banned_users:
        update.message.reply_text("🚫 شما توسط ادمین بن شده‌اید!")
        return
    
    keyboard = [
        [InlineKeyboardButton("💬 چت با AI", callback_data="chat")],
        [InlineKeyboardButton("📝 خلاصه‌سازی", callback_data="summarize")],
        [InlineKeyboardButton("🎨 تولید عکس", callback_data="image")],
        [InlineKeyboardButton("🌐 ترجمه", callback_data="translate")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ پنل ادمین", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "✨ **به ربات هوشمند خوش آمدی!** ✨\n\n"
        "🤖 من یک ربات با هوش مصنوعی هستم.\n"
        "📌 لطفاً یکی از گزینه‌ها را انتخاب کن:"
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
        [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")],
        [InlineKeyboardButton("📜 لاگ", callback_data="admin_log")],
        [InlineKeyboardButton("🚫 بن", callback_data="admin_ban")],
        [InlineKeyboardButton("✅ رفع بن", callback_data="admin_unban")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "⚙️ **پنل مدیریت**",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# ===== آمار =====
def admin_stats(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    total_users = len(users_data)
    banned_count = len(banned_users)
    total_requests = sum(u['requests'] for u in users_data.values())
    
    stats_text = (
        "📊 **آمار ربات**\n\n"
        f"👥 کاربران: {total_users}\n"
        f"🚫 بن شده: {banned_count}\n"
        f"📨 درخواست‌ها: {total_requests}"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# ===== لاگ =====
def admin_log(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    recent_users = list(users_data.keys())[-5:]
    log_text = "📜 **۵ کاربر آخر:**\n\n"
    
    for i, user_id in enumerate(recent_users, 1):
        user_data = users_data.get(user_id, {})
        log_text += f"{i}. آیدی: `{user_id}`\n"
        log_text += f"   تاریخ: {user_data.get('first_seen', 'نامشخص')}\n"
        log_text += f"   درخواست: {user_data.get('requests', 0)}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(log_text[:4000], reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# ===== بن =====
def admin_ban(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    context.user_data['admin_action'] = 'ban'
    query.edit_message_text("🚫 آیدی کاربر را بفرست:", parse_mode=ParseMode.MARKDOWN)

# ===== رفع بن =====
def admin_unban(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    context.user_data['admin_action'] = 'unban'
    query.edit_message_text("✅ آیدی کاربر را بفرست:", parse_mode=ParseMode.MARKDOWN)

# ===== پیام همگانی =====
def admin_broadcast(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    context.user_data['admin_action'] = 'broadcast'
    query.edit_message_text("📢 پیام را بفرست:", parse_mode=ParseMode.MARKDOWN)

# ===== پردازش دکمه‌ها =====
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    
    if user_id in banned_users:
        query.edit_message_text("🚫 شما بن شده‌اید!")
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
    
    messages = {
        'chat': "💬 سوالت را بفرست:",
        'summarize': "📝 متن را بفرست:",
        'image': "🎨 توضیحات عکس را بفرست:",
        'translate': "🌐 متن را بفرست:",
        'help': "ℹ️ راهنما: این ربات با هوش مصنوعی کار می‌کند."
    }
    
    query.edit_message_text(messages.get(query.data, "❌"), parse_mode=ParseMode.MARKDOWN)
    context.user_data['mode'] = query.data

# ===== پردازش پیام‌ها =====
def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id in banned_users:
        update.message.reply_text("🚫 شما بن شده‌اید!")
        return
    
    if user_id not in users_data:
        users_data[user_id] = {'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M"), 'requests': 0}
    users_data[user_id]['requests'] += 1
    
    # اقدامات ادمین
    admin_action = context.user_data.get('admin_action')
    if user_id in ADMIN_IDS and admin_action:
        if admin_action == 'ban':
            try:
                target_id = int(text)
                if target_id not in ADMIN_IDS:
                    banned_users.add(target_id)
                    update.message.reply_text(f"✅ کاربر {target_id} بن شد!")
                else:
                    update.message.reply_text("❌ نمی‌توانید ادمین را بن کنید!")
            except:
                update.message.reply_text("❌ آیدی نامعتبر!")
            context.user_data['admin_action'] = None
            return
            
        elif admin_action == 'unban':
            try:
                target_id = int(text)
                if target_id in banned_users:
                    banned_users.remove(target_id)
                    update.message.reply_text(f"✅ بن {target_id} برداشته شد!")
                else:
                    update.message.reply_text(f"❌ کاربر {target_id} بن نیست!")
            except:
                update.message.reply_text("❌ آیدی نامعتبر!")
            context.user_data['admin_action'] = None
            return
            
        elif admin_action == 'broadcast':
            count = 0
            for uid in users_data.keys():
                try:
                    bot.send_message(chat_id=uid, text=f"📢 پیام از ادمین:\n\n{text}")
                    count += 1
                except:
                    pass
            update.message.reply_text(f"✅ پیام به {count} کاربر ارسال شد!")
            context.user_data['admin_action'] = None
            return
    
    # پردازش معمولی
    mode = context.user_data.get('mode', 'chat')
    processing_msg = update.message.reply_text("⏳ در حال پردازش...")
    
    try:
        if mode == 'chat':
            response = client.text_generation(
                prompt=f"User: {text}\nAI:",
                model="microsoft/DialoGPT-medium",
                max_new_tokens=150
            )
            result = f"🤖 {response.generated_text.strip()}"
            
        elif mode == 'summarize':
            response = client.text_generation(
                prompt=f"Summarize: {text}",
                model="facebook/bart-large-cnn",
                max_new_tokens=150
            )
            result = f"📝 {response.generated_text.strip()}"
            
        elif mode == 'image':
            response = client.text_to_image(
                prompt=text,
                model="black-forest-labs/FLUX.1-schnell"
            )
            bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=response,
                caption=f"🎨 {text}"
            )
            processing_msg.delete()
            return
            
        elif mode == 'translate':
            response = client.text_generation(
                prompt=f"Translate to Persian: {text}",
                model="Helsinki-NLP/opus-mt-en-fa",
                max_new_tokens=150
            )
            result = f"🌐 {response.generated_text.strip()}"
            
        else:
            result = "❌ حالت نامعتبر!"
        
        processing_msg.edit_text(result)
        
    except Exception as e:
        processing_msg.edit_text(f"❌ خطا: {str(e)[:100]}")

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
    WEBHOOK_URL = "https://m-2-87zo.onrender.com/"
    bot.set_webhook(WEBHOOK_URL)
    print("🤖 ربات هوشمند روشن شد!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
