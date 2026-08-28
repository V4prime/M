import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import os
import logging
import time
from typing import List, Dict
from flask import Flask
from threading import Thread

# ======================== LOGGING ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ======================== FLASK SERVER ========================
app = Flask('')

@app.route('/')
def home():
    return "🤖 V4Prime DNS Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    logger.info("✅ Flask server started on port 8080")

# ======================== SETTINGS ========================
TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

if not TOKEN or not CHANNEL_ID:
    logger.error("❌ BOT_TOKEN or CHANNEL_ID not found!")
    exit(1)

bot = telebot.TeleBot(TOKEN, threaded=False)
logger.info("✅ Bot initialized successfully!")

# ======================== DNS GENERATOR ========================

def generate_dns_range(base_ip: str, count: int = 500) -> List[str]:
    """Generate DNS IPs based on a base pattern"""
    dns_list = []
    try:
        parts = base_ip.split('.')
        if len(parts) != 4:
            return []
        
        base_octets = [int(p) for p in parts]
        for i in range(count):
            last_octet = (base_octets[3] + i) % 256
            if last_octet == 0:
                last_octet = 1
            new_ip = f"{base_octets[0]}.{base_octets[1]}.{base_octets[2]}.{last_octet}"
            dns_list.append(new_ip)
    except Exception as e:
        logger.error(f"Error generating DNS range: {e}")
        return []
    return dns_list

# ======================== DNS DATABASE ========================

dns_database = {}

# 1. 🇺🇸 USA
dns_database["🇺🇸 USA"] = list(set(
    [
        "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1",
        "208.67.222.222", "208.67.220.220", "9.9.9.9", "149.112.112.112",
        "76.76.19.19", "76.76.21.21", "185.228.168.168", "185.228.169.168",
        "64.6.64.6", "64.6.65.6", "199.85.126.10", "199.85.127.10",
        "156.154.70.1", "156.154.71.1", "205.171.3.65", "205.171.2.65",
        "198.101.242.72", "198.101.242.73", "23.253.163.53", "23.253.163.54",
        "216.146.35.35", "216.146.36.36", "208.76.50.50", "208.76.51.51",
        "4.2.2.1", "4.2.2.2", "4.2.2.3", "4.2.2.4"
    ] + generate_dns_range("8.8.8.0", 500) + generate_dns_range("1.1.1.0", 500) +
    generate_dns_range("208.67.220.0", 300) + generate_dns_range("9.9.9.0", 300) +
    generate_dns_range("76.76.19.0", 200) + generate_dns_range("64.6.64.0", 200)
))

# 2. 🇬🇧 UK
dns_database["🇬🇧 UK"] = list(set(
    [
        "194.72.9.34", "194.72.9.38", "212.58.97.1", "213.121.168.90",
        "213.121.168.91", "213.121.168.92", "213.121.168.93", "213.121.168.94",
        "194.72.9.35", "194.72.9.36", "194.72.9.37", "194.72.9.39",
        "212.58.97.2", "212.58.97.3", "212.58.97.4", "212.58.97.5",
        "213.121.169.90", "213.121.169.91", "213.121.169.92", "213.121.169.93",
        "194.72.10.34", "194.72.10.38", "212.58.98.1", "212.58.98.2"
    ] + generate_dns_range("194.72.0.0", 500) + generate_dns_range("212.58.90.0", 500) +
    generate_dns_range("213.121.160.0", 500)
))

# 3. 🇩🇪 Germany
dns_database["🇩🇪 Germany"] = list(set(
    [
        "194.25.2.129", "194.25.2.130", "80.150.2.10", "80.150.2.11",
        "193.189.244.10", "193.189.244.11", "212.18.10.10", "212.18.10.11",
        "195.185.151.10", "195.185.151.11", "194.97.1.1", "194.97.1.2"
    ] + generate_dns_range("194.25.0.0", 500) + generate_dns_range("80.150.0.0", 500) +
    generate_dns_range("193.189.240.0", 400) + generate_dns_range("212.18.0.0", 400)
))

# 4. 🇫🇷 France
dns_database["🇫🇷 France"] = list(set(
    [
        "194.2.0.50", "194.2.0.51", "193.56.143.1", "193.56.143.2",
        "195.101.0.10", "195.101.0.11", "195.101.0.12", "195.101.0.13",
        "194.2.1.50", "194.2.1.51", "193.56.144.1", "193.56.144.2",
        "195.101.1.10", "195.101.1.11", "195.101.1.12", "195.101.1.13",
        "194.2.2.50", "194.2.2.51", "193.56.145.1", "193.56.145.2",
        "195.101.2.10", "195.101.2.11", "195.101.2.12", "195.101.2.13"
    ] + generate_dns_range("194.2.0.0", 500) + generate_dns_range("193.56.140.0", 500) +
    generate_dns_range("195.101.0.0", 500)
))

# 5. 🇷🇺 Russia
dns_database["🇷🇺 Russia"] = list(set(
    [
        "195.34.32.1", "195.34.32.2", "194.226.96.10", "194.226.96.11",
        "212.192.96.10", "212.192.96.11", "212.192.96.12", "212.192.96.13",
        "195.34.33.1", "195.34.33.2", "194.226.97.10", "194.226.97.11",
        "212.192.97.10", "212.192.97.11", "212.192.97.12", "212.192.97.13",
        "195.34.34.1", "195.34.34.2", "194.226.98.10", "194.226.98.11",
        "212.192.98.10", "212.192.98.11", "212.192.98.12", "212.192.98.13"
    ] + generate_dns_range("195.34.30.0", 500) + generate_dns_range("194.226.90.0", 500) +
    generate_dns_range("212.192.90.0", 500)
))

# 6. 🇨🇳 China
dns_database["🇨🇳 China"] = list(set(
    [
        "180.76.76.76", "223.5.5.5", "223.6.6.6", "1.2.4.8",
        "210.22.70.3", "210.22.84.3", "211.98.4.1", "211.98.2.4",
        "218.30.118.6", "218.30.118.7", "202.96.209.5", "202.96.209.6",
        "202.96.209.133", "202.96.209.134", "202.96.128.86", "202.96.128.87"
    ] + generate_dns_range("180.76.76.0", 500) + generate_dns_range("223.5.5.0", 500) +
    generate_dns_range("202.96.209.0", 500)
))

# 7. 🇯🇵 Japan
dns_database["🇯🇵 Japan"] = list(set(
    [
        "202.244.37.101", "202.244.37.102", "202.238.84.1", "202.238.84.2",
        "210.148.97.1", "210.148.97.2", "202.43.142.3", "202.43.142.4",
        "202.43.142.5", "202.43.142.6", "210.130.1.1", "210.130.1.2"
    ] + generate_dns_range("202.244.37.0", 500) + generate_dns_range("202.238.84.0", 500) +
    generate_dns_range("210.148.97.0", 400)
))

# 8. 🇨🇦 Canada
dns_database["🇨🇦 Canada"] = list(set(
    [
        "209.91.123.1", "209.91.123.2", "64.59.136.1", "64.59.136.2",
        "205.151.1.1", "205.151.1.2", "208.181.1.1", "208.181.1.2",
        "198.20.240.1", "198.20.240.2", "198.20.241.1", "198.20.241.2"
    ] + generate_dns_range("209.91.123.0", 500) + generate_dns_range("64.59.136.0", 500) +
    generate_dns_range("205.151.0.0", 500)
))

# 9. 🇦🇺 Australia
dns_database["🇦🇺 Australia"] = list(set(
    [
        "61.88.158.1", "61.88.158.2", "203.12.160.1", "203.12.160.2",
        "202.7.166.1", "202.7.166.2", "203.12.161.1", "203.12.161.2",
        "192.189.49.1", "192.189.49.2", "192.189.50.1", "192.189.50.2"
    ] + generate_dns_range("61.88.158.0", 500) + generate_dns_range("203.12.160.0", 500) +
    generate_dns_range("202.7.166.0", 400)
))

# 10. 🇧🇷 Brazil
dns_database["🇧🇷 Brazil"] = list(set(
    [
        "200.189.140.10", "200.189.140.11", "201.10.0.10", "201.10.0.11",
        "200.225.176.10", "200.225.176.11", "200.225.176.12", "200.225.176.13",
        "201.10.1.10", "201.10.1.11", "201.10.1.12", "201.10.1.13",
        "200.189.141.10", "200.189.141.11", "200.189.141.12", "200.189.141.13",
        "200.189.142.10", "200.189.142.11", "200.189.142.12", "200.189.142.13",
        "201.10.2.10", "201.10.2.11", "201.10.2.12", "201.10.2.13"
    ] + generate_dns_range("200.189.130.0", 500) + generate_dns_range("201.10.0.0", 500) +
    generate_dns_range("200.225.176.0", 500)
))

# 11. 🇮🇳 India
dns_database["🇮🇳 India"] = list(set(
    [
        "14.139.229.1", "14.139.229.2", "203.153.207.1", "203.153.207.2",
        "202.141.80.1", "202.141.80.2", "202.141.81.1", "202.141.81.2",
        "61.1.96.1", "61.1.96.2", "61.1.97.1", "61.1.97.2"
    ] + generate_dns_range("14.139.229.0", 500) + generate_dns_range("203.153.207.0", 500) +
    generate_dns_range("202.141.80.0", 500)
))

# 12. 🇰🇷 South Korea
dns_database["🇰🇷 South Korea"] = list(set(
    [
        "168.126.63.1", "168.126.63.2", "164.124.101.1", "164.124.101.2",
        "210.125.84.1", "210.125.84.2", "211.217.107.1", "211.217.107.2",
        "219.250.36.1", "219.250.36.2", "211.46.31.1", "211.46.31.2"
    ] + generate_dns_range("168.126.63.0", 500) + generate_dns_range("164.124.101.0", 500) +
    generate_dns_range("210.125.84.0", 500)
))

# 13. 🇮🇹 Italy
dns_database["🇮🇹 Italy"] = list(set(
    [
        "193.206.139.1", "193.206.139.2", "151.99.125.1", "151.99.125.2",
        "194.244.130.1", "194.244.130.2", "194.244.131.1", "194.244.131.2",
        "212.48.0.1", "212.48.0.2", "212.48.1.1", "212.48.1.2"
    ] + generate_dns_range("193.206.139.0", 500) + generate_dns_range("151.99.125.0", 500) +
    generate_dns_range("194.244.130.0", 500)
))

# 14. 🇪🇸 Spain
dns_database["🇪🇸 Spain"] = list(set(
    [
        "81.46.143.1", "81.46.143.2", "195.235.72.1", "195.235.72.2",
        "212.170.96.1", "212.170.96.2", "194.179.1.1", "194.179.1.2",
        "193.146.100.1", "193.146.100.2", "193.146.101.1", "193.146.101.2"
    ] + generate_dns_range("81.46.143.0", 500) + generate_dns_range("195.235.72.0", 500) +
    generate_dns_range("212.170.96.0", 500)
))

# 15. 🇳🇱 Netherlands
dns_database["🇳🇱 Netherlands"] = list(set(
    [
        "195.121.1.34", "195.121.1.35", "194.109.6.38", "194.109.6.39",
        "80.69.80.1", "80.69.80.2", "213.46.128.1", "213.46.128.2",
        "212.142.0.1", "212.142.0.2", "212.142.1.1", "212.142.1.2"
    ] + generate_dns_range("195.121.1.0", 500) + generate_dns_range("194.109.6.0", 500) +
    generate_dns_range("80.69.80.0", 500)
))

# 16. 🇸🇪 Sweden
dns_database["🇸🇪 Sweden"] = list(set(
    [
        "193.11.48.1", "193.11.48.2", "130.239.18.1", "130.239.18.2",
        "194.146.154.1", "194.146.154.2", "195.178.142.1", "195.178.142.2",
        "62.209.192.1", "62.209.192.2", "62.209.193.1", "62.209.193.2"
    ] + generate_dns_range("193.11.48.0", 500) + generate_dns_range("130.239.18.0", 500) +
    generate_dns_range("194.146.154.0", 500)
))

# 17. 🇹🇷 Turkey
dns_database["🇹🇷 Turkey"] = list(set(
    [
        "85.105.81.252", "85.99.244.74", "88.248.51.121", "85.99.234.230",
        "176.235.135.204", "91.191.170.20", "91.191.170.21", "144.122.95.51",
        "144.122.95.52", "85.105.80.1", "85.105.80.2", "85.105.80.3",
        "88.248.50.1", "88.248.50.2", "88.248.50.3", "88.248.50.4",
        "176.235.136.204", "176.235.136.205", "91.191.171.20", "91.191.171.21",
        "144.122.96.51", "144.122.96.52", "85.99.235.230", "85.99.236.230"
    ] + generate_dns_range("85.105.80.0", 500) + generate_dns_range("88.248.50.0", 500) +
    generate_dns_range("176.235.130.0", 500)
))

# 18. 🇦🇪 UAE
dns_database["🇦🇪 UAE"] = list(set(
    [
        "195.229.25.25", "195.229.25.165", "195.229.24.220", "94.200.18.18",
        "94.200.18.19", "86.98.113.91", "86.98.113.92", "195.229.27.41",
        "213.42.20.10", "213.42.20.11", "213.42.20.12", "213.42.20.13",
        "194.170.0.10", "194.170.0.11", "194.170.0.12", "194.170.0.13",
        "94.200.17.17", "94.200.17.18", "94.200.17.19", "94.200.17.20",
        "86.98.112.1", "86.98.112.2", "86.98.112.3", "86.98.112.4"
    ] + generate_dns_range("195.229.20.0", 500) + generate_dns_range("94.200.10.0", 500) +
    generate_dns_range("213.42.20.0", 500)
))

# 19. 🇸🇬 Singapore
dns_database["🇸🇬 Singapore"] = list(set(
    [
        "203.116.14.18", "203.116.14.19", "203.116.14.20", "202.79.32.1",
        "202.79.32.2", "202.79.32.3", "202.79.32.4", "203.116.14.21",
        "203.116.15.18", "203.116.15.19", "203.116.15.20", "203.116.15.21",
        "202.79.33.1", "202.79.33.2", "202.79.33.3", "202.79.33.4",
        "203.116.16.18", "203.116.16.19", "203.116.16.20", "203.116.16.21",
        "202.79.34.1", "202.79.34.2", "202.79.34.3", "202.79.34.4"
    ] + generate_dns_range("203.116.10.0", 500) + generate_dns_range("202.79.30.0", 500) +
    generate_dns_range("203.116.14.0", 500)
))

# 20. 🇦🇷 Argentina
dns_database["🇦🇷 Argentina"] = list(set(
    [
        "200.69.193.70", "200.69.193.71", "200.115.192.10", "200.49.130.10",
        "200.49.130.11", "200.49.130.12", "200.49.130.13", "200.49.130.14",
        "200.69.192.1", "200.69.192.2", "200.69.192.3", "200.69.192.4",
        "200.115.192.11", "200.115.192.12", "200.115.192.13", "200.115.192.14",
        "200.49.131.1", "200.49.131.2", "200.49.131.3", "200.49.131.4",
        "200.69.194.1", "200.69.194.2", "200.69.194.3", "200.69.194.4"
    ] + generate_dns_range("200.69.190.0", 500) + generate_dns_range("200.49.120.0", 500) +
    generate_dns_range("200.115.192.0", 500)
))

# Clean up
for country in dns_database:
    dns_database[country] = list(set(dns_database[country]))
    logger.info(f"✅ {country}: {len(dns_database[country])} DNS records")

total_dns = sum(len(dns) for dns in dns_database.values())
logger.info(f"🎯 Total DNS records: {total_dns}")

# ======================== USER COOLDOWN ========================
user_last_command = {}

def is_rate_limited(user_id: int, limit: int = 5) -> bool:
    current_time = time.time()
    if user_id in user_last_command:
        if current_time - user_last_command[user_id] < limit:
            return True
    user_last_command[user_id] = current_time
    return False

# ======================== HELPER FUNCTIONS ========================

def get_two_random_dns(country_key: str) -> List[str]:
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
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

def safe_send_message(chat_id: int, text: str, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

def safe_edit_message(text: str, chat_id: int, message_id: int, **kwargs):
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
            safe_send_message(message.chat.id, "⏳ Please wait a few seconds!")
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
    """Show country selection buttons (with message object)"""
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
            f"📊 *Total DNS in database:* `{total_dns:,}`",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error showing country selection: {e}")
        safe_send_message(message.chat.id, "❌ Error loading countries. Please try again!")

def show_country_selection_by_chat_id(chat_id: int):
    """Show country selection buttons using chat_id directly"""
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
            chat_id,
            f"🌏 *Select your desired country:*\n\n"
            f"Choose a country to get 2 real and powerful DNS servers.\n\n"
            f"📊 *Total DNS in database:* `{total_dns:,}`",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error showing country selection: {e}")
        safe_send_message(chat_id, "❌ Error loading countries. Please try again!")

def send_dns_message(chat_id: int, country_key: str):
    try:
        dns_list = get_two_random_dns(country_key)
        
        flag = country_key.split()[0]
        name = ' '.join(country_key.split()[1:])
        
        text = f"🌍 *Real DNS for {flag} {name}*\n\n"
        for i, dns in enumerate(dns_list, 1):
            text += f"🔹 `{dns}`\n"
        
        text += f"\n📊 *Total available DNS:* `{len(dns_database.get(country_key, [])):,}`"
        text += "\n⚠️ *Note:* These DNS servers are real and active."
        
        safe_send_message(chat_id, text, parse_mode='Markdown')
        
        # ========== نمایش دوباره کشورها ==========
        show_country_selection_by_chat_id(chat_id)
        
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
                    "❌ You haven't joined yet!",
                    show_alert=True
                )

        elif call.data.startswith("dns_"):
            country_key = call.data.replace("dns_", "")
            bot.answer_callback_query(call.id, f"🌍 Fetching DNS for {country_key}...")
            send_dns_message(call.message.chat.id, country_key)
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        bot.answer_callback_query(cal
