import os
import json
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ===== تنظیمات =====
TOKEN = "8844239608:AAHszuQ2AFaAW3T5l2rU8XuHyBFsNq7asPA"
ADMIN_ID = 8844239608  # آیدی عددی خودت
# ===================

app = Flask(__name__)
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# ذخیره‌سازی پیام‌های ناشناس (برای ادمین)
anonymous_messages = []

# ===== دستور شروع =====
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🕵️ به ربات ناشناس خوش اومدی!\n\n"
        "📩 می‌تونی هر پیامی که می‌خوای به ربات بفرستی و ما به مقصد نهایی (گروه یا کاربر) ناشناس می‌فرستیم.\n"
        "🔒 حریم خصوصی‌ات کامل حفظ میشه (فقط ادمین می‌تونه ببینه کی فرستاده!)."
    )

# ===== دریافت پیام از کاربر =====
def handle_message(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = user.id
    username = user.username or "ندارد"
    first_name = user.first_name or "ندارد"
    text = update.message.text
    
    # ذخیره اطلاعات برای ادمین
    anonymous_messages.append({
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "text": text
    })
    
    # ارسال پیام ناشناس به گروه یا کاربر (اینجا مثال: ارسال به خودت)
    bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 پیام ناشناس:\n\n{text}"
    )
    
    # تایید به کاربر
    update.message.reply_text("✅ پیامت ناشناس ارسال شد!")

# ===== دستور ویژه ادمین برای دیدن لیست پیام‌ها =====
def admin_list(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ شما دسترسی ندارید!")
        return
    
    if not anonymous_messages:
        update.message.reply_text("📭 هنوز پیام ناشناسی دریافت نشده.")
        return
    
    # نمایش ۵ پیام آخر
    msg = "📋 لیست پیام‌های ناشناس:\n\n"
    for i, item in enumerate(anonymous_messages[-5:], 1):
        msg += f"{i}. از: {item['first_name']} (@{item['username']}) - آیدی: {item['user_id']}\n"
        msg += f"   متن: {item['text'][:50]}...\n\n"
    
    update.message.reply_text(msg)

# ===== ثبت هندلرها =====
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("admin_list", admin_list))  # دستور ویژه ادمین
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# ===== Webhook =====
@app.route("/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def health():
    return "Bot is running!", 200

if __name__ == "__main__":
    WEBHOOK_URL = "https://m-1-4x8p.onrender.com/"
    bot.set_webhook(WEBHOOK_URL)
    print("🤖 ربات ناشناس روشن شد!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
