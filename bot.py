import os
import asyncio
import uuid
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== تنظیمات =====
TOKEN = "8844239608:AAHszuQ2AFaAW3T5l2rU8XuHyBFsNq7asPA"
ADMIN_IDS = [8518256437]
# ===================

app = Flask(__name__)
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()

file_storage = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 سلام! ربات آپلودر اختصاصی.\n"
        "📤 فقط ادمین‌ها می‌تونن آپلود کنن.\n"
        "🔗 بعد آپلود لینک می‌گیری که ۱۰ ثانیه بعد پاک میشه."
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ فقط ادمین‌ها!")
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
        await update.message.reply_text("❌ ویدیو یا فایل بفرست!")
        return
    
    code = str(uuid.uuid4())[:8]
    file_storage[code] = {"file_id": file_id, "file_type": file_type}
    
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={code}"
    
    await update.message.reply_text(f"✅ لینک:\n{link}\n\n⏰ ۱۰ ثانیه بعد پاک میشه!")

async def handle_start_with_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = context.args[0] if context.args else None
    if not code or code not in file_storage:
        await update.message.reply_text("❌ لینک نامعتبر!")
        return
    
    info = file_storage[code]
    msg = await update.message.reply_video(
        video=info["file_id"],
        caption="🎬 سیو کن! ۱۰ ثانیه پاک میشه..."
    )
    
    await asyncio.sleep(10)
    try:
        await msg.delete()
        await update.message.delete()
    except:
        pass

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("start", handle_start_with_code))
application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL | filters.PHOTO, handle_file))

@app.route("/", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(), bot)
    await application.process_update(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def health():
    return "Bot is running!", 200

if __name__ == "__main__":
    WEBHOOK_URL = "https://your-bot.onrender.com/"
    bot.set_webhook(WEBHOOK_URL)
    print("🤖 ربات روشن شد!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
