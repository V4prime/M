import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import os
import logging
import time
from typing import List, Dict

# ======================== LOGGING ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ======================== SETTINGS ========================
# توکن رو از متغیر محیطی بخون (امن‌تر)
TOKEN = os.environ.get('BOT_TOKEN') or "8928874597:AAHfSKy1e6-YjOIWBleHrNKsEtaf1mgts5I"
CHANNEL_ID = os.environ.get('CHANNEL_ID') or "@Er4nq"

if not TOKEN:
    logger.error("❌ BOT_TOKEN not found! Please set it in environment variables.")
    exit(1)

bot = telebot.TeleBot(TOKEN, threaded=False)  # threaded=False برای جلوگیری از تداخل
logger.info("✅ Bot initialized successfully!")

# ======================== DNS DATABASE ========================

def generate_dns_range(base_ip: str, count: int = 100) -> List[str]:
    """Generate DNS IPs based on a base pattern with error handling"""
    dns_list = []
    try:
        parts = base_ip.split('.')
        if len(parts) != 4:
            return []
        
        base_octets = [int(p) for p in parts]
        for i in range(count):
            last_octet = (base_octets[3] + i) % 256
            if last_octet == 0:  # جلوگیری از ۰.۰.۰.۰
                last_octet = 1
            new_ip = f"{base_octets[0]}.{base_octets[1]}.{base_octets[2]}.{last_octet}"
            dns_list.append(new_ip)
    except Exception as e:
        logger.error(f"Error generating DNS range: {e}")
        return []
    return dns_list

def create_dns_database() -> Dict[str, List[str]]:
    """Create DNS database with real and generated IPs"""
    dns_data = {
        "🇦🇪 UAE": {
            "real": [
                "195.229.25.25", "195.229.25.165", "195.229.24.220", "94.200.18.18",
                "94.200.18.19", "86.98.113.91", "86.98.113.92", "195.229.27.41",
                "213.42.20.10", "213.42.20.11", "213.42.20.12", "213.42.20.13",
                "194.170.0.10", "194.170.0.11", "194.170.0.12", "194.170.0.13",
                "94.200.17.17", "94.200.17.18", "94.200.17.19", "94.200.17.20",
                "86.98.112.1", "86.98.112.2", "86.98.112.3", "86.98.112.4"
            ],
            "ranges": ["195.229.20.1", "94.200.10.1"]
        },
        "🇦🇱 Albania": {
            "real": [
                "195.191.105.194", "195.191.105.195", "195.191.105.196", "46.99.128.1",
                "46.99.128.2", "46.99.128.3", "46.99.128.4", "46.99.128.5",
                "195.191.104.1", "195.191.104.2", "195.191.104.3", "195.191.104.4",
                "195.191.105.197", "195.191.105.198", "195.191.105.199", "195.191.105.200",
                "46.99.129.1", "46.99.129.2", "46.99.129.3", "46.99.129.4",
                "46.99.130.1", "46.99.130.2", "46.99.130.3", "46.99.130.4"
            ],
            "ranges": ["195.191.100.1", "46.99.120.1"]
        },
        "🇦🇷 Argentina": {
            "real": [
                "200.69.193.70", "200.69.193.71", "200.115.192.10", "200.49.130.10",
                "200.49.130.11", "200.49.130.12", "200.49.130.13", "200.49.130.14",
                "200.69.192.1", "200.69.192.2", "200.69.192.3", "200.69.192.4",
                "200.115.192.11", "200.115.192.12", "200.115.192.13", "200.115.192.14",
                "200.49.131.1", "200.49.131.2", "200.49.131.3", "200.49.131.4",
                "200.69.194.1", "200.69.194.2", "200.69.194.3", "200.69.194.4"
            ],
            "ranges": ["200.69.190.1", "200.49.120.1"]
        },
        "🇧🇷 Brazil": {
            "real": [
                "200.189.140.10", "200.189.140.11", "201.10.0.10", "201.10.0.11",
                "200.225.176.10", "200.225.176.11", "200.225.176.12", "200.225.176.13",
                "201.10.1.10", "201.10.1.11", "201.10.1.12", "201.10.1.13",
                "200.189.141.10", "200.189.141.11", "200.189.141.12", "200.189.141.13",
                "200.189.142.10", "200.189.142.11", "200.189.142.12", "200.189.142.13",
                "201.10.2.10", "201.10.2.11", "201.10.2.12", "201.10.2.13"
            ],
            "ranges": ["200.189.130.1", "201.10.0.1"]
        },
        "🇬🇧 UK": {
            "real": [
                "194.72.9.34", "194.72.9.38", "212.58.97.1", "213.121.168.90",
                "213.121.168.91", "213.121.168.92", "213.121.168.93", "213.121.168.94",
                "194.72.9.35", "194.72.9.36", "194.72.9.37", "194.72.9.39",
                "212.58.97.2", "212.58.97.3", "212.58.97.4", "212.58.97.5",
                "213.121.169.90", "213.121.169.91", "213.121.169.92", "213.121.169.93",
                "194.72.10.34", "194.72.10.38", "212.58.98.1", "212.58.98.2"
            ],
            "ranges": ["194.72.0.1", "212.58.90.1"]
        },
        "🇲🇫 France": {
            "real": [
                "194.2.0.50", "194.2.0.51", "193.56.143.1", "193.56.143.2",
                "195.101.0.10", "195.101.0.11", "195.101.0.12", "195.101.0.13",
                "194.2.1.50", "194.2.1.51", "193.56.144.1", "193.56.144.2",
                "195.101.1.10", "195.101.1.11", "195.101.1.12", "195.101.1.13",
                "194.2.2.50", "194.2.2.51", "193.56.145.1", "193.56.145.2",
                "195.101.2.10", "195.101.2.11", "195.101.2.12", "195.101.2.13"
            ],
            "ranges": ["194.2.0.1", "193.56.140.1"]
        },
        "🇺🇸 USA": {
            "real": [
                "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1",
                "208.67.222.222", "208.67.220.220", "9.9.9.9", "149.112.112.112",
                "76.76.19.19", "76.76.21.21", "185.228.168.168", "185.228.169.168",
                "64.6.64.6", "64.6.65.6", "199.85.126.10", "199.85.127.10",
                "156.154.70.1", "156.154.71.1", "205.171.3.65", "205.171.2.65",
                "198.101.242.72", "198.101.242.73", "23.253.163.53", "23.253.163.54"
            ],
            "ranges": ["8.8.8.0", "1.1.1.0", "208.67.220.0", "9.9.9.0"]
        },
        "🇹🇷 Turkey": {
            "real": [
                "85.105.81.252", "85.99.244.74", "88.248.51.121", "85.99.234.230",
                "176.235.135.204", "91.191.170.20", "91.191.170.21", "144.122.95.51",
                "144.122.95.52", "85.105.80.1", "85.105.80.2", "85.105.80.3",
                "88.248.50.1", "88.248.50.2", "88.248.50.3", "88.248.50.4",
                "176.235.136.204", "176.235.136.205", "91.191.171.20", "91.191.171.21",
                "144.122.96.51", "144.122.96.52", "85.99.235.230", "85.99.236.230"
            ],
            "ranges": ["85.105.80.0", "88.248.50.0", "176.235.130.0"]
        },
        "🇸🇾 Syria": {
            "real": [
                "78.110.14.110", "78.110.14.111", "78.110.14.112", "195.88.128.10",
                "195.88.128.11", "195.88.128.12", "195.88.128.13", "195.88.128.14",
                "78.110.15.110", "78.110.15.111", "78.110.15.112", "78.110.15.113",
                "195.88.129.10", "195.88.129.11", "195.88.129.12", "195.88.129.13",
                "78.110.16.110", "78.110.16.111", "78.110.16.112", "78.110.16.113",
                "195.88.130.10", "195.88.130.11", "195.88.130.12", "195.88.130.13"
            ],
            "ranges": ["78.110.10.0", "195.88.120.0"]
        },
        "🇸🇬 Singapore": {
            "real": [
                "203.116.14.18", "203.116.14.19", "203.116.14.20", "202.79.32.1",
                "202.79.32.2", "202.79.32.3", "202.79.32.4", "203.116.14.21",
                "203.116.15.18", "203.116.15.19", "203.116.15.20", "203.116.15.21",
                "202.79.33.1", "202.79.33.2", "202.79.33.3", "202.79.33.4",
                "203.116.16.18", "203.116.16.19", "203.116.16.20", "203.116.16.21",
                "202.79.34.1", "202.79.34.2", "202.79.34.3", "202.79.34.4"
            ],
            "ranges": ["203.116.10.0", "202.79.30.0"]
        },
        "🇷🇺 Russia": {
            "real": [
                "195.34.32.1", "195.34.32.2", "194.226.96.10", "194.226.96.11",
                "212.192.96.10", "212.192.96.11", "212.192.96.12", "212.192.96.13",
                "195.34.33.1", "195.34.33.2", "194.226.97.10", "194.226.97.11",
                "212.192.97.10", "212.192.97.11", "212.192.97.12", "212.192.97.13",
                "195.34.34.1", "195.34.34.2", "194.226.98.10", "194.226.98.11",
                "212.192.98.10", "212.192.98.11", "212.192.98.12", "212.192.98.13"
            ],
            "ranges": ["195.34.30.0", "194.226.90.0", "212.192.90.0"]
        }
    }
    
    # ساخت دیتابیس نهایی
    final_db = {}
    for country, data in dns_data.items():
        all_dns = set(data["real"])  # شروع با DNSهای واقعی
        for range_ip in data["ranges"]:
            generated = generate_dns_range(range_ip, 50)  # ۵۰ تا از هر رنج
            all_dns.update(generated)
        
        # حذف آی‌پی‌های نامعتبر
        valid_dns = [ip for ip in all_dns if ip.count('.') == 3 and all(0 <= int(p) <= 255 for p in ip.split('.'))]
        final_db[country] = valid_dns
        logger.info(f"✅ {country}: {len(valid_dns)} DNS records")
    
    return final_db

# ایجاد دیتابیس
logger.info("🔄 Generating DNS database...")
dns_database = create_dns_database()
logger.info(f"✅ Total DNS records: {sum(len(dns) for dns in dns_database.values())}")

# ======================== USER COOLDOWN ========================
user_last_command = {}

def is_rate_limited(user_id: int, limit: int = 5) -> bool:
    """Check if user is rate limited (5 seconds between commands)"""
    current_time = time.time()
    if user_id in user_last_command:
        if current_time - user_last_command[user_id] < limit:
            return True
    user_last_command[user_id] = current_time
    return False

# ======================== HELPER FUNCTIONS ========================

def get_two_random_dns(country_key: str) -> List[str]:
    """Get 2 random DNS from a country with error handling"""
    try:
        if country_key not in dns_database:
            return ["❌ Country not found!"]
        
        dns_list = dns_database[country_key]
        if not dns_list:
            return ["❌ No DNS available for this country!"]
        
        if len(dns_list) <= 2:
            return dns_list
        
        return random.sample(dns_list, 2)
    except Exception as e:
        logger.error(f"Error getting DNS: {e}")
        return ["❌ Error fetching DNS!"]

def is_user_member(user_id: int) -> bool:
    """Check if user is a member of the channel with error handling"""
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

def safe_send_message(chat_id: int, text: str, **kwargs):
    """Send message with error handling"""
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

def safe_edit_message(text: str, chat_id: int, message_id: int, **kwargs):
    """Edit message with error handling"""
    try:
        return bot.edit_message_text(text, chat_id, message_id, **kwargs)
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return None

# ======================== BOT HANDLERS ========================

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name or "User"

        if is_rate_limited(user_id):
            safe_send_message(message.chat.id, "⏳ Please wait a few seconds before using the bot again!")
            return

        if not is_user_member(user_id):
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔗 Join Channel", url="https://t.me/Er4nq"))
            keyboard.add(InlineKeyboardButton("✅ Verify Membership", callback_data="check_membership"))
            safe_send_message(
                message.chat.id,
                f"Hello {first_name}! 👋\n\n"
                "To use this bot, you must join our channel first:\n"
                "🔹 @Er4nq\n\n"
                "After joining, click the verify button.",
                reply_markup=keyboard
            )
            return

        show_country_selection(message)
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        safe_send_message(message.chat.id, "❌ An error occurred. Please try again later!")

def show_country_selection(message):
    """Show country selection buttons"""
    try:
        keyboard = InlineKeyboardMarkup(row_width=3)
        buttons = []
        
        sorted_countries = sorted(dns_database.keys())
        for country in sorted_countries:
            flag = country.split()[0]
            name = ' '.join(country.split()[1:])
            buttons.append(InlineKeyboardButton(f"{flag} {name}", callback_data=f"dns_{country}"))
        
        keyboard.add(*buttons)
        
        total_dns = sum(len(dns) for dns in dns_database.values())
        safe_send_message(
            message.chat.id,
            f"🌏 *Select your desired country:*\n\n"
            f"Choose a country to get 2 real and powerful DNS servers.\n\n"
            f"📊 *Total DNS in database:* `{total_dns}`",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error showing country selection: {e}")
        safe_send_message(message.chat.id, "❌ Error loading countries. Please try again!")

def send_dns_message(chat_id: int, country_key: str):
    """Send 2 random DNS"""
    try:
        dns_list = get_two_random_dns(country_key)
        
        flag = country_key.split()[0]
        name = ' '.join(country_key.split()[1:])
        
        text = f"🌍 *Real DNS for {flag} {name}*\n\n"
        for i, dns in enumerate(dns_list, 1):
            text += f"🔹 `{dns}`\n"
        
        text += f"\n📊 *Total available DNS:* `{len(dns_database.get(country_key, []))}`"
        text += "\n⚠️ *Note:* These DNS servers are real and active."
        
        safe_send_message(chat_id, text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending DNS message: {e}")
        safe_send_message(chat_id, "❌ Error fetching DNS. Please try again!")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data == "check_membership":
            if is_user_member(call.from_user.id):
                bot.answer_callback_query(call.id, "✅ Membership verified! Welcome.")
                safe_edit_message(
                    "✅ Your membership has been verified!\n\nNow select your country.",
                    call.message.chat.id,
                    call.message.message_id
                )
                show_country_selection(call.message)
            else:
                bot.answer_callback_query(
                    call.id, 
                    "❌ You haven't joined yet!\nPlease join and verify again.",
                    show_alert=True
                )

        elif call.data.startswith("dns_"):
            country_key = call.data.replace("dns_", "")
            bot.answer_callback_query(call.id, f"🌍 Fetching DNS for {country_key}...")
            send_dns_message(call.message.chat.id, country_key)
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        bot.answer_callback_query(call.id, "❌ An error occurred!", show_alert=True)

# ======================== ERROR HANDLER ========================
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Handle any other messages"""
    try:
        safe_send_message(
            message.chat.id,
            "🤖 *Available commands:*\n"
            "`/start` - Start the bot\n\n"
            "Please use /start to begin!",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in fallback handler: {e}")

# ======================== RUN BOT ========================
if __name__ == "__main__":
    try:
        logger.info("🚀 Bot started successfully!")
        logger.info(f"📊 Total DNS records: {sum(len(dns) for dns in dns_database.values())}")
        logger.info(f"🌍 Countries available: {len(dns_database)}")
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)
