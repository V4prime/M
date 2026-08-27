import os
import asyncio
import uuid
import threading
import time
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ===== تنظیمات =====
TOKEN = "8844239608:AAHszuQ2AFaAW3T5l2rU8XuHyBFsNq7asPA"
ADMIN_IDS = [8518256437]
# ===================

app = Flask(__name__)
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

file_storage = {}

# ===== دستورات ربات =====
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🎬 سلام! ربات آپلودر اختصاصی.\n"
        "📤 فقط ادمین‌ها می‌تونن آپلود کنن.\n"
        "🔗 بعد آپلود لینک می‌گیری که ۱۰ ثانیه بعد پاک میشه."
    )

def handle_file(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    
    if update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    else:
        update.message.reply_text("❌ ویدیو یا فایل بفرست!")
        return
    
    code = str(uuid.uuid4())[:8]
    file_storage[code] = {"file_id": file_id, "file_type": file_type}
    
    bot_username = context.bot.get_me().username
    link = f"https://t.me/{bot_username}?start={code}"
    
    update.message.reply_text(f"✅ لینک:\n{link}\n\n⏰ ۱۰ ثانیه بعد پاک میشه!")

def handle_start_with_code(update: Update, context: CallbackContext):
    code = context.args[0] if context.args else None
    if not code or code not in file_storage:
        update.message.reply_text("❌ لینک نامعتبر!")
        return
    
    info = file_storage[code]
    msg = update.message.reply_video(
        video=info["file_id"],
        caption="🎬 سیو کن! ۱۰ ثانیه پاک میشه..."
    )
    
    def delete_after():
        time.sleep(10)
        try:
            bot.delete_message(chat_id=update.effective_chat.id, message_id=msg.message_id)
            bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass
    threading.Thread(target=delete_after).start()

# ===== ثبت هندلرها =====
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("start", handle_start_with_code))
dispatcher.add_handler(MessageHandler(Filters.video | Filters.document | Filters.photo, handle_file))

# ===== Webhook =====
@app.route("/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def health():
    return "Bot is running!", 200

# ===== اجرا =====
if __name__ == "__main__":
    WEBHOOK_URL = "https://your-bot.onrender.com/"
    bot.set_webhook(WEBHOOK_URL)
    print("🤖 ربات روشن شد!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
