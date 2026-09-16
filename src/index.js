// ==========================================
// Telegram Self-Bot Manager - Fly.io Edition
// Pure Node.js with mtcute - WASM works natively
// ==========================================
import express from 'express';
import { TelegramClient, SqliteStorage } from '@mtcute/node';
import Database from 'better-sqlite3';
import crypto from 'crypto';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ==========================================
// Configuration
// ==========================================
const BOT_TOKEN = process.env.BOT_TOKEN || '8301773080:AAHH-f674N9wm3Z9ahNbor9CxkQAnsqLrqg';
const USERBOT_API_ID = parseInt(process.env.USERBOT_API_ID || '611335', 10);
const USERBOT_API_HASH = process.env.USERBOT_API_HASH || 'd524b414d21f4d37f08684c1df41ac9c';
const SESSION_ENCRYPTION_KEY = process.env.SESSION_ENCRYPTION_KEY || crypto.randomBytes(32).toString('hex');
const AI_API_KEY = process.env.AI_API_KEY || '';
const PORT = process.env.PORT || 8080;
const ADMIN_IDS = (process.env.ADMIN_IDS || '').split(',').map(s => s.trim()).filter(Boolean);

const TELEGRAM_API = 'https://api.telegram.org';

// ==========================================
// SQLite Database Setup
// ==========================================
const db = new Database(path.join(__dirname, 'selfbot.db'));
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_user_id INTEGER UNIQUE NOT NULL,
  tg_username TEXT,
  tg_first_name TEXT,
  is_admin INTEGER DEFAULT 0,
  is_banned INTEGER DEFAULT 0,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  last_activity INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS selfbot_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id INTEGER NOT NULL,
  api_id INTEGER NOT NULL,
  api_hash TEXT NOT NULL,
  phone TEXT NOT NULL,
  session_string TEXT,
  session_encrypted INTEGER DEFAULT 1,
  my_user_id INTEGER,
  my_username TEXT,
  my_first_name TEXT,
  is_premium INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending',
  last_connected_at INTEGER,
  last_error TEXT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_selfbot_owner ON selfbot_sessions(owner_id);

CREATE TABLE IF NOT EXISTS login_states (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id INTEGER NOT NULL UNIQUE,
  step TEXT NOT NULL,
  temp_api_id INTEGER,
  temp_api_hash TEXT,
  temp_phone TEXT,
  dc_id INTEGER,
  phone_code_hash TEXT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS feature_settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  feature TEXT NOT NULL,
  enabled INTEGER DEFAULT 0,
  config TEXT,
  UNIQUE(session_id, feature)
);

CREATE TABLE IF NOT EXISTS activity_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER,
  level TEXT NOT NULL,
  category TEXT NOT NULL,
  message TEXT NOT NULL,
  extra TEXT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_logs_session ON activity_logs(session_id, created_at DESC);

CREATE TABLE IF NOT EXISTS spy_targets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  target_user_id INTEGER NOT NULL,
  target_username TEXT,
  target_first_name TEXT,
  keywords TEXT,
  notify_owner INTEGER DEFAULT 1,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  UNIQUE(session_id, target_user_id)
);

CREATE TABLE IF NOT EXISTS spy_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  target_user_id INTEGER NOT NULL,
  chat_id INTEGER,
  chat_title TEXT,
  message_text TEXT,
  message_id INTEGER,
  captured_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS security_alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  alert_type TEXT NOT NULL,
  details TEXT,
  ip_hint TEXT,
  device_hint TEXT,
  location_hint TEXT,
  handled INTEGER DEFAULT 0,
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS banners (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  banner_type TEXT NOT NULL,
  text TEXT,
  media_file_id TEXT,
  caption TEXT,
  interval_sec INTEGER DEFAULT 300,
  is_active INTEGER DEFAULT 1,
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS tabchi_stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL UNIQUE,
  sent_count INTEGER DEFAULT 0,
  failed_count INTEGER DEFAULT 0,
  last_send_at INTEGER,
  last_error TEXT
);

CREATE TABLE IF NOT EXISTS auto_reactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  emoji TEXT NOT NULL,
  probability INTEGER DEFAULT 50
);

CREATE TABLE IF NOT EXISTS auto_comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  text TEXT NOT NULL,
  probability INTEGER DEFAULT 50
);
`);

// ==========================================
// Active Session Manager (in-memory)
// Holds mtcute client instances per user
// ==========================================
const activeSessions = new Map(); // sessionId -> { client, state }

// ==========================================
// Encryption utilities
// ==========================================
function encryptString(plaintext, secret) {
  const iv = crypto.randomBytes(12);
  const key = crypto.scryptSync(secret, 'salt', 32);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag();
  return Buffer.concat([iv, authTag, encrypted]).toString('base64');
}

function decryptString(ciphertext, secret) {
  const buf = Buffer.from(ciphertext, 'base64');
  const iv = buf.slice(0, 12);
  const authTag = buf.slice(12, 28);
  const encrypted = buf.slice(28);
  const key = crypto.scryptSync(secret, 'salt', 32);
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(authTag);
  return decipher.update(encrypted, null, 'utf8') + decipher.final('utf8');
}

// ==========================================
// Telegram Bot API client
// ==========================================
async function tgApi(method, params = {}) {
  const url = `${TELEGRAM_API}/bot${BOT_TOKEN}/${method}`;
  // Normalize reply_markup
  if (params.reply_markup) {
    if (Array.isArray(params.reply_markup)) {
      params.reply_markup = { inline_keyboard: params.reply_markup };
    }
  }
  const cleanParams = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) cleanParams[k] = v;
  }
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cleanParams),
  });
  const data = await res.json();
  if (!data.ok) {
    throw new Error(`TG API ${method}: ${data.description || 'unknown'}`);
  }
  return data.result;
}

const botSendMessage = (chatId, text, opts = {}) => tgApi('sendMessage', {
  chat_id: chatId, text,
  parse_mode: opts.parseMode,
  reply_markup: opts.replyMarkup,
  disable_web_page_preview: opts.disablePreview,
  reply_to_message_id: opts.replyTo,
});

const botEditMessageText = (chatId, messageId, text, opts = {}) => tgApi('editMessageText', {
  chat_id: chatId, message_id: messageId, text,
  parse_mode: opts.parseMode,
  reply_markup: opts.replyMarkup,
  disable_web_page_preview: opts.disablePreview,
});

const botAnswerCallback = (callbackId, text, showAlert) => tgApi('answerCallbackQuery', {
  callback_query_id: callbackId, text, show_alert: showAlert,
});

// ==========================================
// Messages
// ==========================================
const MSG = {
  welcome: '👋 سلام {name}!\n\n🤖 به ربات مدیریت سلف خوش اومدی.\n\nبا این ربات می‌تونی اکانت تلگرامت رو به‌عنوان سلف متصل کنی و همه‌ی قابلیت‌ها رو از پنل کنترل کنی.',
  notAdmin: '⛔️ شما دسترسی لازم رو ندارید.',
  sessionNotFound: '❌ هیچ اکانت سلفی متصل نیست.\n\nبرای اتصال، روی «اتصال اکانت» بزنید.',
  sessionActive: '✅ اکانت سلف شما متصل و آنلاین است.\n\n👤 {name} (`{uid}`)\n📱 شماره: `{phone}`\n⭐️ پریمیوم: {premium}\n🔗 وضعیت: `{status}`',
  loginStart: '🔐 شروع اتصال اکانت سلف.\n\n📞 لطفاً شماره موبایل خودت رو با کد کشور بفرست.\n\n💡 مثال: `989123456789` یا `+989123456789`',
  loginPhoneInvalid: '❌ شماره نامعتبره. فقط اعداد با + یا بدون +.\n\nمثال: `989123456789`',
  loginCodeSent: '📨 کد تأیید به تلگرامت ارسال شد.\n\n🔢 لطفاً کد رو بفرست.\n\n💡 اگر کد به‌صورت `12-345-67` فرستاده شد، می‌تونی با خط تیره یا بدون خط تیره بفرستی.',
  loginPasswordPrompt: '🔒 اکانتت رمز دوم (2FA) داره.\n\n🔑 لطفاً رمز دوم رو بفرست.',
  loginSuccess: '🎉 اکانت با موفقیت متصل شد!\n\n👤 {name}\n📱 {phone}\n\nاز این به بعد اکانت ۲۴ ساعته آنلاین می‌مونه و از پنل می‌تونی کنترلش کنی.',
  loginError: '⚠️ خطا در ورود: `{error}`',
  reconnectStarted: '🔄 در حال اتصال مجدد...',
  reconnectSuccess: '✅ اکانت مجدداً متصل شد.',
  reconnectFailed: '❌ اتصال مجدد ناموفق: `{error}`',
  disconnectConfirm: '⚠️ مطمئنی می‌خوای اکانت رو قطع کنی؟',
  disconnected: '✅ اکانت قطع شد.',
  help: '📚 راهنما\n\nاین ربات به شما اجازه می‌ده اکانت تلگرامتون رو به‌عنوان سلف متصل کنید و قابلیت‌های زیر رو استفاده کنید:\n\n• تبچی هوشمند\n• ریکت خودکار\n• کامنت اول خودکار\n• چت AI\n• ساعت زنده کنار اسم\n• کپی پروفایل\n• فضول‌یاب\n• ضد لاگین\n\nبرای شروع، /start رو بزنید.',
};

function format(template, vars) {
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ''));
}

// ==========================================
// Inline Keyboards
// ==========================================
function btn(text, callback_data) { return { text, callback_data }; }

function mainPanelKeyboard(sessionActive) {
  if (!sessionActive) {
    return { inline_keyboard: [
      [btn('🔌 اتصال اکانت', 'login_start')],
      [btn('📚 راهنما', 'help'), btn('📊 وضعیت', 'status')],
    ]};
  }
  return { inline_keyboard: [
    [btn('📡 پنل سلف', 'page:self')],
    [btn('📢 تبچی', 'page:tabchi'), btn('💬 پیام خودکار', 'page:auto')],
    [btn('👤 پروفایل', 'page:profile'), btn('🛡️ امنیت', 'page:security')],
    [btn('🔌 قطع اتصال', 'disconnect_confirm'), btn('🔄 اتصال مجدد', 'reconnect')],
    [btn('📊 وضعیت', 'status'), btn('📚 راهنما', 'help')],
  ]};
}

function selfPanelKeyboard() {
  return { inline_keyboard: [
    [btn('🔄 راه‌اندازی مجدد', 'self:restart'), btn('📋 اطلاعات اکانت', 'self:info')],
    [btn('🔋 قطع موقت', 'self:pause'), btn('▶️ ادامه', 'self:resume')],
    [btn('🗑️ حذف سشن', 'self:delete')],
    [btn('🔙 بازگشت', 'main')],
  ]};
}

function tabchiPanelKeyboard(config) {
  return { inline_keyboard: [
    [btn(config.enabled ? '✅ تبچی: روشن' : '❌ تبچی: خاموش', 'tabchi:toggle')],
    [btn('➕ افزودن بنر متن', 'tabchi:add_text')],
    [btn('🎯 گروه‌های هدف', 'tabchi:targets'), btn('📨 فوروارد پیوی', 'tabchi:forward_pv')],
    [btn('⚡️ سرعت', 'tabchi:speed'), btn(config.antiRip ? '🛡️ ضد ریپ: روشن' : '🛡️ ضد ریپ: خاموش', `tabchi:antirip:${config.antiRip ? 'off' : 'on'}`)],
    [btn('📊 آمار', 'tabchi:stats'), btn('🗑️ پاک‌سازی', 'tabchi:clear')],
    [btn('🔙 بازگشت', 'main')],
  ]};
}

function autoPanelKeyboard(s) {
  return { inline_keyboard: [
    [btn(s.autoReact ? '✅ ریکت خودکار: روشن' : '❌ ریکت خودکار: خاموش', 'auto:react:toggle')],
    [btn(s.autoComment ? '✅ کامنت اول: روشن' : '❌ کامنت اول: خاموش', 'auto:comment:toggle')],
    [btn(s.aiChat ? '✅ چت AI: روشن' : '❌ چت AI: خاموش', 'auto:ai:toggle')],
    [btn(s.smartText ? '✅ متن هوشمند: روشن' : '❌ متن هوشمند: خاموش', 'auto:smart_text:toggle')],
    [btn(s.videoToGif ? '✅ ویدیو مسیج: روشن' : '❌ ویدیو مسیج: خاموش', 'auto:video_gif:toggle')],
    [btn('🔙 بازگشت', 'main')],
  ]};
}

function profilePanelKeyboard(s) {
  return { inline_keyboard: [
    [btn(s.clock ? '✅ ساعت زنده: روشن' : '❌ ساعت زنده: خاموش', 'profile:clock:toggle')],
    [btn('🔤 فونت ساعت', 'profile:clock:font'), btn('🎨 طرح ساعت', 'profile:clock:style')],
    [btn(s.rotatingName ? '✅ فونت چرخشی: روشن' : '❌ فونت چرخشی: خاموش', 'profile:rotating:toggle')],
    [btn('🎨 لوگوساز', 'profile:logo'), btn('📥 کپی پروفایل', 'profile:copy')],
    [btn('📖 استوری', 'profile:story'), btn('📝 تغییر بیو', 'profile:bio')],
    [btn('🔙 بازگشت', 'main')],
  ]};
}

function securityPanelKeyboard(s) {
  return { inline_keyboard: [
    [btn('🕵️ فضول‌یاب', 'page:spy')],
    [btn(s.antiLogin ? '✅ ضد لاگین: روشن' : '❌ ضد لاگین: خاموش', 'security:anti_login:toggle')],
    [btn('📋 هشدارها', 'security:alerts'), btn('🔐 سشن‌های فعال', 'security:sessions')],
    [btn('🚪 خروج از سشن‌های دیگر', 'security:terminate_others')],
    [btn('🔙 بازگشت', 'main')],
  ]};
}

function spyPanelKeyboard() {
  return { inline_keyboard: [
    [btn('➕ افزودن هدف (با ریپلای)', 'spy:add_reply'), btn('➖ حذف هدف (با ریپلای)', 'spy:remove_reply')],
    [btn('📋 لیست اهداف', 'spy:list'), btn('📊 رویدادها', 'spy:events')],
    [btn('🔙 بازگشت امنیت', 'page:security')],
  ]};
}

function backKeyboard(target = 'main') {
  return { inline_keyboard: [[btn('🔙 بازگشت', target)]] };
}

// ==========================================
// DB Query helpers
// ==========================================
const dbGet = (sql, ...params) => db.prepare(sql).get(...params);
const dbAll = (sql, ...params) => db.prepare(sql).all(...params);
const dbRun = (sql, ...params) => { db.prepare(sql).run(...params); };

function upsertUser(tgUserId, username, firstName) {
  db.prepare(`INSERT INTO users (tg_user_id, tg_username, tg_first_name, last_activity)
    VALUES (?, ?, ?, unixepoch())
    ON CONFLICT(tg_user_id) DO UPDATE SET
      tg_username = excluded.tg_username,
      tg_first_name = excluded.tg_first_name,
      last_activity = unixepoch()`).run(tgUserId, username, firstName);
  return dbGet('SELECT * FROM users WHERE tg_user_id = ?', tgUserId);
}

function getSessionByOwner(ownerId) {
  return dbGet('SELECT * FROM selfbot_sessions WHERE owner_id = ? ORDER BY id DESC LIMIT 1', ownerId);
}

function createSession(ownerId, apiId, apiHash, phone) {
  dbRun('INSERT INTO selfbot_sessions (owner_id, api_id, api_hash, phone, status) VALUES (?, ?, ?, ?, ?)', ownerId, apiId, apiHash, phone, 'pending');
  return dbGet('SELECT * FROM selfbot_sessions WHERE id = last_insert_rowid()');
}

function updateSession(sessionId, fields) {
  const sets = [];
  const vals = [];
  for (const [k, v] of Object.entries(fields)) {
    if (v === undefined) continue;
    sets.push(`${k} = ?`);
    vals.push(v);
  }
  if (sets.length === 0) return;
  sets.push('updated_at = unixepoch()');
  vals.push(sessionId);
  dbRun(`UPDATE selfbot_sessions SET ${sets.join(', ')} WHERE id = ?`, ...vals);
}

function getLoginState(ownerId) {
  return dbGet('SELECT * FROM login_states WHERE owner_id = ?', ownerId);
}

function upsertLoginState(ownerId, fields) {
  const existing = getLoginState(ownerId);
  if (existing) {
    const sets = [];
    const vals = [];
    for (const [k, v] of Object.entries(fields)) {
      if (v === undefined) continue;
      sets.push(`${k} = ?`);
      vals.push(v);
    }
    if (sets.length === 0) return;
    sets.push('updated_at = unixepoch()');
    vals.push(ownerId);
    dbRun(`UPDATE login_states SET ${sets.join(', ')} WHERE owner_id = ?`, ...vals);
  } else {
    dbRun(`INSERT INTO login_states (owner_id, step, temp_api_id, temp_api_hash, temp_phone, dc_id, phone_code_hash) VALUES (?, ?, ?, ?, ?, ?, ?)`,
      ownerId, fields.step || 'phone', fields.temp_api_id ?? null, fields.temp_api_hash ?? null,
      fields.temp_phone ?? null, fields.dc_id ?? null, fields.phone_code_hash ?? null);
  }
}

function deleteLoginState(ownerId) {
  dbRun('DELETE FROM login_states WHERE owner_id = ?', ownerId);
}

function getFeature(sessionId, feature) {
  return dbGet('SELECT * FROM feature_settings WHERE session_id = ? AND feature = ?', sessionId, feature);
}

function listFeatures(sessionId) {
  return dbAll('SELECT * FROM feature_settings WHERE session_id = ?', sessionId);
}

function setFeature(sessionId, feature, enabled, config) {
  db.prepare(`INSERT INTO feature_settings (session_id, feature, enabled, config) VALUES (?, ?, ?, ?)
    ON CONFLICT(session_id, feature) DO UPDATE SET enabled = excluded.enabled, config = excluded.config`)
    .run(sessionId, feature, enabled ? 1 : 0, config ? JSON.stringify(config) : null);
}

function logActivity(sessionId, level, category, message, extra) {
  dbRun('INSERT INTO activity_logs (session_id, level, category, message, extra) VALUES (?, ?, ?, ?, ?)',
    sessionId ?? null, level, category, message, extra ? JSON.stringify(extra) : null);
}

// ==========================================
// Session Manager - mtcute client management
// ==========================================
async function getClientForSession(session, fresh = false) {
  const cacheKey = session.id;
  if (!fresh && activeSessions.has(cacheKey)) {
    const cached = activeSessions.get(cacheKey);
    if (cached.client.isConnected) return cached.client;
  }

  // Decrypt session string
  let sessionString = '';
  if (session.session_string) {
    try {
      sessionString = session.session_encrypted
        ? decryptString(session.session_string, SESSION_ENCRYPTION_KEY)
        : session.session_string;
    } catch (e) {
      console.error('Session decrypt failed:', e.message);
    }
  }

  // Create sqlite-backed storage
  const storage = new SqliteStorage(`session-${session.id}.db`);
  await storage.load?.();

  const client = new TelegramClient({
    apiId: session.api_id,
    apiHash: session.api_hash,
    storage,
  });

  await client.connect();

  if (sessionString) {
    try {
      await client.importSession(sessionString);
    } catch (e) {
      console.error('Session import failed:', e.message);
    }
  }

  activeSessions.set(cacheKey, { client, state: session });
  return client;
}

// Track pending login state per session (for code/password flow)
const pendingLogins = new Map(); // sessionId -> { phone, sendCodeResult, code, password }

async function startLoginFlow(session, phone) {
  // Always start with a fresh client to avoid stale state
  const client = await getClientForSession(session, true);

  // Trigger code sending by trying to start
  try {
    await client.start({
      phone: () => Promise.resolve(phone),
      code: () => Promise.reject(new Error('CODE_REQUIRED')),
      password: () => Promise.reject(new Error('PASSWORD_REQUIRED')),
    });
    // If we reach here, login succeeded without code (cached session valid)
    const sessionString = await client.exportSession();
    return { done: true, session: sessionString };
  } catch (e) {
    const msg = String(e.message || e);
    if (msg.includes('CODE_REQUIRED')) {
      // Save pending state so verifyCode can use the same client
      pendingLogins.set(session.id, { phone, code: null, password: null });
      return { needs: 'code' };
    }
    if (msg.includes('PASSWORD_REQUIRED')) {
      pendingLogins.set(session.id, { phone, code: null, password: null });
      return { needs: 'password' };
    }
    throw e;
  }
}

async function verifyCode(session, code) {
  // Use the same client that sent the code (to avoid re-sending another code)
  const client = await getClientForSession(session);

  // If we have a pending login from startLoginFlow, update its code
  const pending = pendingLogins.get(session.id) || {};
  pending.code = code;
  pendingLogins.set(session.id, pending);

  try {
    await client.start({
      phone: () => Promise.resolve(session.phone),
      code: () => Promise.resolve(code),
      password: () => Promise.reject(new Error('PASSWORD_REQUIRED')),
    });
    const sessionString = await client.exportSession();
    pendingLogins.delete(session.id);
    return { done: true, session: sessionString };
  } catch (e) {
    const msg = String(e.message || e);
    if (msg.includes('PASSWORD_REQUIRED')) return { needs: 'password' };
    throw e;
  }
}

async function verifyPassword(session, password) {
  // Use the same client that sent the code
  const client = await getClientForSession(session);

  // Get the code from pending state
  const pending = pendingLogins.get(session.id) || {};
  const code = pending.code || '';

  try {
    await client.start({
      phone: () => Promise.resolve(session.phone),
      code: () => Promise.resolve(code),
      password: () => Promise.resolve(password),
    });
    const sessionString = await client.exportSession();
    pendingLogins.delete(session.id);
    return { done: true, session: sessionString };
  } catch (e) {
    // On error, reset the client so next attempt starts fresh
    activeSessions.delete(session.id);
    throw e;
  }
}

async function connectSession(session) {
  const client = await getClientForSession(session);
  const me = await client.getMe();
  return {
    id: Number(me.id),
    firstName: me.firstName,
    username: me.username,
    isPremium: me.isPremium ?? false,
  };
}

// ==========================================
// Login Handler
// ==========================================
async function handleLoginInput(msg, state) {
  const userId = msg.from.id;
  const text = (msg.text || '').trim();
  const PHONE_RE = /^\+?\d{7,15}$/;

  switch (state.step) {
    case 'phone': {
      if (!PHONE_RE.test(text)) {
        await botSendMessage(msg.chat.id, MSG.loginPhoneInvalid, { parseMode: 'Markdown' });
        return;
      }
      // Create or update session
      let session = getSessionByOwner(userId);
      if (session) {
        updateSession(session.id, { api_id: USERBOT_API_ID, api_hash: USERBOT_API_HASH, phone: text, status: 'awaiting_code' });
      } else {
        session = createSession(userId, USERBOT_API_ID, USERBOT_API_HASH, text);
      }
      upsertLoginState(userId, { step: 'code' });

      try {
        const result = await startLoginFlow(session, text);
        if (result.needs === 'code') {
          await botSendMessage(msg.chat.id, MSG.loginCodeSent, { parseMode: 'Markdown' });
        } else if (result.needs === 'password') {
          upsertLoginState(userId, { step: 'password' });
          updateSession(session.id, { status: 'awaiting_password' });
          await botSendMessage(msg.chat.id, MSG.loginPasswordPrompt, { parseMode: 'Markdown' });
        } else if (result.done) {
          await finalizeLogin(msg, session.id, result.session);
        }
      } catch (e) {
        logActivity(session.id, 'error', 'login', e.message);
        updateSession(session.id, { status: 'error', last_error: e.message });
        await botSendMessage(msg.chat.id, format(MSG.loginError, { error: e.message }), { parseMode: 'Markdown' });
        deleteLoginState(userId);
      }
      return;
    }
    case 'code': {
      const session = getSessionByOwner(userId);
      if (!session) {
        deleteLoginState(userId);
        await botSendMessage(msg.chat.id, '❌ جلسه نامعتبر. /login بزن.');
        return;
      }
      try {
        const result = await verifyCode(session, text);
        if (result.done) {
          await finalizeLogin(msg, session.id, result.session);
        } else if (result.needs === 'password') {
          upsertLoginState(userId, { step: 'password' });
          updateSession(session.id, { status: 'awaiting_password' });
          await botSendMessage(msg.chat.id, MSG.loginPasswordPrompt, { parseMode: 'Markdown' });
        }
      } catch (e) {
        if (String(e.message).includes('PASSWORD')) {
          upsertLoginState(userId, { step: 'password' });
          await botSendMessage(msg.chat.id, MSG.loginPasswordPrompt, { parseMode: 'Markdown' });
        } else {
          await botSendMessage(msg.chat.id, format(MSG.loginError, { error: e.message }), { parseMode: 'Markdown' });
        }
      }
      return;
    }
    case 'password': {
      const session = getSessionByOwner(userId);
      if (!session) {
        deleteLoginState(userId);
        await botSendMessage(msg.chat.id, '❌ جلسه نامعتبر.');
        return;
      }
      try {
        const result = await verifyPassword(session, text);
        if (result.done) {
          await finalizeLogin(msg, session.id, result.session);
        }
      } catch (e) {
        await botSendMessage(msg.chat.id, format(MSG.loginError, { error: e.message }), { parseMode: 'Markdown' });
      }
      return;
    }
    default:
      deleteLoginState(userId);
      await botSendMessage(msg.chat.id, '❌ وضعیت نامعتبر. /login بزن.');
  }
}

async function finalizeLogin(msg, sessionId, sessionString) {
  const userId = msg.from.id;
  const encrypted = encryptString(sessionString, SESSION_ENCRYPTION_KEY);
  updateSession(sessionId, {
    session_string: encrypted,
    session_encrypted: 1,
    status: 'active',
    last_connected_at: Math.floor(Date.now() / 1000),
    last_error: null,
  });
  upsertLoginState(userId, { step: 'done' });
  setTimeout(() => deleteLoginState(userId), 5000);

  // Get me info
  let meInfo = {};
  try {
    const session = dbGet('SELECT * FROM selfbot_sessions WHERE id = ?', sessionId);
    const me = await connectSession(session);
    meInfo = me;
    updateSession(sessionId, {
      my_user_id: me.id,
      my_username: me.username,
      my_first_name: me.firstName,
      is_premium: me.isPremium ? 1 : 0,
    });
  } catch (e) {
    console.error('connect after login failed:', e.message);
  }

  logActivity(sessionId, 'success', 'login', `Logged in as ${meInfo.firstName || 'unknown'}`);
  await botSendMessage(msg.chat.id, format(MSG.loginSuccess, {
    name: meInfo.firstName || 'کاربر',
    phone: dbGet('SELECT phone FROM selfbot_sessions WHERE id = ?', sessionId).phone,
  }), { parseMode: 'Markdown' });
}

// ==========================================
// Main Panel Display
// ==========================================
async function showMainPanel(env, msgOrCb, session) {
  const chatId = msgOrCb.message ? msgOrCb.message.chat.id : msgOrCb.chat.id;
  const messageId = msgOrCb.message ? msgOrCb.message.message_id : msgOrCb.message_id;
  const active = session?.status === 'active';
  const text = active
    ? format(MSG.sessionActive, {
        name: session.my_first_name || 'ناشناس',
        uid: String(session.my_user_id || '?'),
        phone: session.phone,
        premium: session.is_premium ? '✅' : '❌',
        status: session.status,
      })
    : MSG.sessionNotFound;
  await botEditMessageText(chatId, messageId, text, {
    parseMode: 'Markdown',
    replyMarkup: mainPanelKeyboard(active).inline_keyboard,
  });
}

async function showPage(cb, page, session) {
  const chatId = cb.message.chat.id;
  const messageId = cb.message.message_id;
  const features = listFeatures(session.id);
  const featMap = {};
  features.forEach(f => featMap[f.feature] = f);
  const isOn = (k) => featMap[k]?.enabled === 1;

  switch (page) {
    case 'self': {
      const text = `📄 صفحه ۲/۷ - پنل سلف\n\n🔧 مدیریت اتصال اکانت سلف.`;
      return botEditMessageText(chatId, messageId, text, {
        parseMode: 'Markdown',
        replyMarkup: selfPanelKeyboard().inline_keyboard,
      });
    }
    case 'tabchi': {
      const f = featMap['tabchi'];
      let config = {};
      try { config = f?.config ? JSON.parse(f.config) : {}; } catch {}
      const cfg = {
        enabled: f?.enabled === 1,
        speed: config.speed ?? 300,
        antiRip: config.antiRip ?? true,
        forwardPv: config.forwardPv ?? false,
      };
      const stats = dbGet('SELECT * FROM tabchi_stats WHERE session_id = ?', session.id);
      const text = `📢 پنل مدیریت تبچی\n\n📊 آمار:\n• ارسال موفق: ${stats?.sent_count ?? 0}\n• ناموفق: ${stats?.failed_count ?? 0}`;
      return botEditMessageText(chatId, messageId, text, {
        parseMode: 'Markdown',
        replyMarkup: tabchiPanelKeyboard(cfg).inline_keyboard,
      });
    }
    case 'auto': {
      const s = {
        autoReact: isOn('auto_react'),
        autoComment: isOn('auto_comment'),
        aiChat: isOn('ai_chat'),
        smartText: isOn('smart_text'),
        videoToGif: isOn('video_gif'),
      };
      return botEditMessageText(chatId, messageId, '⚙️ پنل پیام خودکار', {
        replyMarkup: autoPanelKeyboard(s).inline_keyboard,
      });
    }
    case 'profile': {
      const s = {
        clock: isOn('clock'),
        rotatingName: isOn('rotating_name'),
        clockFont: 'modern',
        clockStyle: 'default',
      };
      return botEditMessageText(chatId, messageId, '👤 پنل پروفایل', {
        replyMarkup: profilePanelKeyboard(s).inline_keyboard,
      });
    }
    case 'security': {
      const alerts = dbAll('SELECT * FROM security_alerts WHERE session_id = ? ORDER BY created_at DESC LIMIT 100', session.id);
      const s = {
        antiLogin: isOn('anti_login'),
        alertCount: alerts.length,
      };
      return botEditMessageText(chatId, messageId, `🛡️ پنل امنیت\n\n⚠️ هشدارها: ${alerts.length}`, {
        replyMarkup: securityPanelKeyboard(s).inline_keyboard,
      });
    }
    case 'spy': {
      const targets = dbAll('SELECT * FROM spy_targets WHERE session_id = ?', session.id);
      const events = dbAll('SELECT * FROM spy_events WHERE session_id = ?', session.id);
      return botEditMessageText(chatId, messageId, `🕵️ فضول‌یاب\n\n🎯 اهداف: ${targets.length}\n📊 رویدادها: ${events.length}`, {
        replyMarkup: spyPanelKeyboard().inline_keyboard,
      });
    }
    default:
      return showMainPanel(null, cb, session);
  }
}

// ==========================================
// Callback Handler
// ==========================================
async function handleCallback(cb) {
  const data = cb.data || '';
  const userId = cb.from.id;
  const msg = cb.message;
  const chatId = msg?.chat.id;

  await botAnswerCallback(cb.id).catch(() => {});
  if (data === 'noop') return;

  upsertUser(userId, cb.from.username, cb.from.first_name);

  if (ADMIN_IDS.length > 0 && !ADMIN_IDS.includes(String(userId))) {
    await botAnswerCallback(cb.id, MSG.notAdmin, true).catch(() => {});
    return;
  }

  const session = getSessionByOwner(userId);

  if (data === 'main') return showMainPanel(null, cb, session);
  if (data === 'help') return botEditMessageText(chatId, msg.message_id, MSG.help, { replyMarkup: backKeyboard().inline_keyboard });
  if (data === 'status') return showMainPanel(null, cb, session);

  if (data === 'login_start') {
    if (session?.status === 'active') {
      await botAnswerCallback(cb.id, 'اکانت از قبل متصله.', true);
      return;
    }
    upsertLoginState(userId, { step: 'phone' });
    return botEditMessageText(chatId, msg.message_id, MSG.loginStart, { parseMode: 'Markdown' });
  }

  if (!session && !['main', 'help', 'status'].includes(data)) {
    return botEditMessageText(chatId, msg.message_id, MSG.sessionNotFound, {
      parseMode: 'Markdown',
      replyMarkup: mainPanelKeyboard(false).inline_keyboard,
    });
  }

  // Page navigation
  if (data.startsWith('page:')) {
    return showPage(cb, data.slice(5), session);
  }

  // Self panel
  if (data.startsWith('self:')) {
    const action = data.slice(5);
    if (action === 'info') {
      const text = `📋 *اطلاعات اکانت*\n\n👤 نام: ${session.my_first_name || '-'}\n🆔 آیدی: \`${session.my_user_id || '-'}\`\n📱 شماره: \`${session.phone}\`\n⭐️ پریمیوم: ${session.is_premium ? '✅' : '❌'}\n🔗 وضعیت: \`${session.status}\``;
      return botEditMessageText(chatId, msg.message_id, text, { parseMode: 'Markdown', replyMarkup: backKeyboard('page:self').inline_keyboard });
    }
    if (action === 'restart') {
      try {
        const cached = activeSessions.get(session.id);
        if (cached?.client) await cached.client.destroy();
        activeSessions.delete(session.id);
        const me = await connectSession(session);
        updateSession(session.id, { status: 'active', last_connected_at: Math.floor(Date.now()/1000) });
        return showPage(cb, 'self', session);
      } catch (e) {
        return botEditMessageText(chatId, msg.message_id, format(MSG.reconnectFailed, { error: e.message }), { parseMode: 'Markdown' });
      }
    }
  }

  // Tabchi
  if (data.startsWith('tabchi:')) {
    const action = data.slice(7);
    if (action === 'toggle') {
      const f = getFeature(session.id, 'tabchi');
      const newEnabled = !(f?.enabled === 1);
      setFeature(session.id, 'tabchi', newEnabled);
      return showPage(cb, 'tabchi', session);
    }
    if (action === 'add_text') {
      setFeature(session.id, '_pending_banner', true, { type: 'text' });
      return botSendMessage(chatId, '📝 لطفاً متن بنر رو بفرست.', { replyMarkup: [[btn('❌ لغو', 'tabchi:cancel')]] });
    }
    if (action === 'cancel') {
      setFeature(session.id, '_pending_banner', false);
      return showPage(cb, 'tabchi', session);
    }
    if (action.startsWith('antirip:')) {
      const newAntiRip = action.endsWith('on');
      const f = getFeature(session.id, 'tabchi');
      let config = {};
      try { config = f?.config ? JSON.parse(f.config) : {}; } catch {}
      setFeature(session.id, 'tabchi', f?.enabled === 1, { ...config, antiRip: newAntiRip });
      return showPage(cb, 'tabchi', session);
    }
    if (action === 'stats') {
      const stats = dbGet('SELECT * FROM tabchi_stats WHERE session_id = ?', session.id);
      const banners = dbAll('SELECT * FROM banners WHERE session_id = ?', session.id);
      const text = `📊 *آمار تبچی*\n\n✅ موفق: ${stats?.sent_count ?? 0}\n❌ ناموفق: ${stats?.failed_count ?? 0}\n📋 بنرها: ${banners.length}`;
      return botEditMessageText(chatId, msg.message_id, text, { parseMode: 'Markdown', replyMarkup: backKeyboard('page:tabchi').inline_keyboard });
    }
    if (action === 'clear') {
      dbRun('DELETE FROM banners WHERE session_id = ?', session.id);
      dbRun('UPDATE tabchi_stats SET sent_count = 0, failed_count = 0 WHERE session_id = ?', session.id);
      return showPage(cb, 'tabchi', session);
    }
  }

  // Auto features
  if (data.startsWith('auto:')) {
    const [feature, sub] = data.slice(5).split(':');
    if (sub === 'toggle') {
      const map = { react: 'auto_react', comment: 'auto_comment', ai: 'ai_chat', smart_text: 'smart_text', video_gif: 'video_gif' };
      const featName = map[feature];
      if (featName) {
        const f = getFeature(session.id, featName);
        setFeature(session.id, featName, !(f?.enabled === 1));
      }
    }
    return showPage(cb, 'auto', session);
  }

  // Profile
  if (data.startsWith('profile:')) {
    const [feature, sub] = data.slice(8).split(':');
    if (feature === 'clock' && sub === 'toggle') {
      const f = getFeature(session.id, 'clock');
      setFeature(session.id, 'clock', !(f?.enabled === 1), { font: 'modern' });
      return showPage(cb, 'profile', session);
    }
    if (feature === 'rotating' && sub === 'toggle') {
      const f = getFeature(session.id, 'rotating_name');
      setFeature(session.id, 'rotating_name', !(f?.enabled === 1));
      return showPage(cb, 'profile', session);
    }
    return showPage(cb, 'profile', session);
  }

  // Security
  if (data.startsWith('security:')) {
    const action = data.slice(9);
    if (action === 'anti_login:toggle') {
      const f = getFeature(session.id, 'anti_login');
      setFeature(session.id, 'anti_login', !(f?.enabled === 1));
      return showPage(cb, 'security', session);
    }
    return showPage(cb, 'security', session);
  }

  // Spy
  if (data.startsWith('spy:')) {
    return showPage(cb, 'spy', session);
  }

  // Disconnect
  if (data === 'disconnect_confirm') {
    return botEditMessageText(chatId, msg.message_id, MSG.disconnectConfirm, {
      replyMarkup: { inline_keyboard: [[btn('✅ بله، قطع کن', 'disconnect_yes'), btn('❌ خیر', 'main')]] },
    });
  }
  if (data === 'disconnect_yes') {
    const cached = activeSessions.get(session.id);
    if (cached?.client) await cached.client.destroy();
    activeSessions.delete(session.id);
    updateSession(session.id, { status: 'disconnected' });
    return showMainPanel(null, cb, dbGet('SELECT * FROM selfbot_sessions WHERE id = ?', session.id));
  }

  // Reconnect
  if (data === 'reconnect') {
    await botEditMessageText(chatId, msg.message_id, MSG.reconnectStarted);
    try {
      const me = await connectSession(session);
      updateSession(session.id, { status: 'active', last_connected_at: Math.floor(Date.now()/1000), last_error: null });
      await botEditMessageText(chatId, msg.message_id, MSG.reconnectSuccess, { replyMarkup: mainPanelKeyboard(true).inline_keyboard });
    } catch (e) {
      updateSession(session.id, { status: 'error', last_error: e.message });
      await botEditMessageText(chatId, msg.message_id, format(MSG.reconnectFailed, { error: e.message }), { parseMode: 'Markdown' });
    }
  }
}

// ==========================================
// Message Handler
// ==========================================
async function handleMessage(msg) {
  const userId = msg.from?.id;
  if (!userId) return;

  upsertUser(userId, msg.from?.username, msg.from?.first_name);

  if (ADMIN_IDS.length > 0 && !ADMIN_IDS.includes(String(userId))) {
    await botSendMessage(msg.chat.id, MSG.notAdmin);
    return;
  }

  if (msg.text?.startsWith('/')) {
    const cmd = msg.text.split(/\s+/)[0].toLowerCase().split('@')[0];
    if (cmd === '/start') {
      const session = getSessionByOwner(userId);
      const active = session?.status === 'active';
      const text = active
        ? format(MSG.sessionActive, {
            name: session.my_first_name || 'ناشناس',
            uid: String(session.my_user_id || '?'),
            phone: session.phone,
            premium: session.is_premium ? '✅' : '❌',
            status: session.status,
          })
        : format(MSG.welcome, { name: msg.from?.first_name || 'دوست من' });
      return botSendMessage(msg.chat.id, text, {
        parseMode: 'Markdown',
        replyMarkup: mainPanelKeyboard(active).inline_keyboard,
      });
    }
    if (cmd === '/help') return botSendMessage(msg.chat.id, MSG.help);
    if (cmd === '/login') {
      const session = getSessionByOwner(userId);
      if (session?.status === 'active') {
        return botSendMessage(msg.chat.id, '✅ اکانت متصله.');
      }
      upsertLoginState(userId, { step: 'phone' });
      return botSendMessage(msg.chat.id, MSG.loginStart, { parseMode: 'Markdown' });
    }
    if (cmd === '/cancel') {
      deleteLoginState(userId);
      return botSendMessage(msg.chat.id, '❌ لغو شد.');
    }
    return;
  }

  // Handle pending banner text
  const session = getSessionByOwner(userId);
  if (session) {
    const pending = getFeature(session.id, '_pending_banner');
    if (pending?.enabled === 1) {
      setFeature(session.id, '_pending_banner', false);
      dbRun('INSERT INTO banners (session_id, banner_type, text, interval_sec) VALUES (?, ?, ?, 300)',
        session.id, 'text', msg.text);
      return botSendMessage(msg.chat.id, '✅ بنر ذخیره شد.');
    }
  }

  // Login state machine
  const loginState = getLoginState(userId);
  if (loginState && loginState.step !== 'done') {
    return handleLoginInput(msg, loginState);
  }

  // Default: show panel
  const s = getSessionByOwner(userId);
  const active = s?.status === 'active';
  const text = active
    ? format(MSG.sessionActive, {
        name: s.my_first_name || 'ناشناس',
        uid: String(s.my_user_id || '?'),
        phone: s.phone,
        premium: s.is_premium ? '✅' : '❌',
        status: s.status,
      })
    : MSG.sessionNotFound;
  await botSendMessage(msg.chat.id, text, {
    parseMode: 'Markdown',
    replyMarkup: mainPanelKeyboard(active).inline_keyboard,
  });
}

// ==========================================
// Express Web Server (for Telegram webhook)
// ==========================================
const app = express();
app.use(express.json());

app.get('/', (req, res) => res.json({ ok: true, name: 'telegram-selfbot', version: '2.0.0' }));
app.get('/health', (req, res) => res.json({ ok: true, ts: Date.now() }));

app.post(`/webhook/${BOT_TOKEN}`, async (req, res) => {
  const update = req.body;
  res.json({ ok: true });
  try {
    if (update.message) {
      await handleMessage(update.message);
    } else if (update.callback_query) {
      await handleCallback(update.callback_query);
    }
  } catch (e) {
    console.error('Update error:', e);
  }
});

// Auto-reconnect active sessions on startup
async function autoReconnectSessions() {
  const sessions = dbAll("SELECT * FROM selfbot_sessions WHERE status = 'active'");
  console.log(`Found ${sessions.length} active sessions to reconnect`);
  for (const session of sessions) {
    try {
      const me = await connectSession(session);
      console.log(`Reconnected session ${session.id} (${me.firstName})`);
    } catch (e) {
      console.error(`Reconnect failed for session ${session.id}:`, e.message);
      updateSession(session.id, { status: 'error', last_error: e.message });
    }
  }
}

// Set webhook on startup
async function setupWebhook(publicUrl) {
  try {
    await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook?drop_pending_updates=true`);
    const res = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/setWebhook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: `${publicUrl}/webhook/${BOT_TOKEN}`,
        allowed_updates: ['message', 'callback_query', 'edited_message'],
        drop_pending_updates: true,
      }),
    });
    const data = await res.json();
    console.log('Webhook set:', data);
  } catch (e) {
    console.error('Webhook setup failed:', e.message);
  }
}

// Start server
app.listen(PORT, async () => {
  console.log(`🚀 Server running on port ${PORT}`);
  await autoReconnectSessions();

  // Detect public URL from Fly.io
  const appName = process.env.FLY_APP_NAME;
  if (appName) {
    const publicUrl = `https://${appName}.fly.dev`;
    console.log(`Public URL: ${publicUrl}`);
    await setupWebhook(publicUrl);
  } else {
    console.log('Set FLY_APP_NAME env var or manually configure webhook');
  }
});

// Periodic keep-alive for active sessions
setInterval(() => {
  for (const [id, cached] of activeSessions.entries()) {
    if (!cached.client.isConnected) {
      console.log(`Session ${id} disconnected, cleaning up`);
      activeSessions.delete(id);
    }
  }
}, 60000);

console.log('Telegram Self-Bot Manager started');
