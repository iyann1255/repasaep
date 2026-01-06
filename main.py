import asyncio
import random
import time
from typing import Dict, Tuple, Set

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, RPCError
from motor.motor_asyncio import AsyncIOMotorClient

from config import API_ID, API_HASH, MONGO_URL, MONGO_DB

# =========================
# SETTINGS
# =========================
DEBUG = True

# Trigger rules: (trigger, response, mode) mode: contains | exact
CHATREP_RULES = [
    ("ubot", "bot gacor di sini @asepvoid", "contains"),
]

COOLDOWN_SECONDS = 6
HUMAN_DELAY_RANGE = (0.2, 0.8)
REPLY_TO_TRIGGER_MESSAGE = True

# cooldown in-memory
LAST_SENT: Dict[Tuple[int, str], float] = {}

# cache enabled groups in-memory (loaded from Mongo lazily)
ACTIVE_CHAT_IDS: Set[int] = set()
DB_LOADED = False
DB_LOCK = asyncio.Lock()

# =========================
# PYROGRAM APP
# =========================
app = Client("chatrep_userbot", api_id=API_ID, api_hash=API_HASH)

def dlog(msg: str):
    if DEBUG:
        print(msg)

def normalize(text: str) -> str:
    return (text or "").strip().lower()

def is_group(m) -> bool:
    return bool(m.chat) and m.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)

def match(mode: str, trigger: str, incoming: str) -> bool:
    mode = (mode or "contains").lower()
    t = normalize(trigger)
    inc = normalize(incoming)
    if not t or not inc:
        return False
    if mode == "exact":
        return inc == t
    return t in inc

async def safe_send(client: Client, chat_id: int, text: str, reply_to: int | None):
    try:
        await client.send_message(chat_id, text, reply_to_message_id=reply_to)
    except FloodWait as e:
        await asyncio.sleep(int(e.value) + 1)
        await client.send_message(chat_id, text, reply_to_message_id=reply_to)
    except RPCError as e:
        dlog(f"[SEND ERROR] chat={chat_id} err={e}")

# =========================
# PATCH: skip Peer id invalid (opsi 1)
# =========================
from pyrogram.client import Client as PyroClient  # noqa: E402
_original_handle_updates = PyroClient.handle_updates

async def _safe_handle_updates(self, updates):
    try:
        return await _original_handle_updates(self, updates)
    except ValueError as e:
        if "Peer id invalid" in str(e):
            dlog(f"[WARN] skipped update: {e}")
            return
        raise

PyroClient.handle_updates = _safe_handle_updates

# =========================
# MONGO
# =========================
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo[MONGO_DB]
col = db["chatrep_settings"]

async def ensure_db_loaded():
    """
    Lazy load: dipanggil saat ada command/handler pertama kali.
    Ini menghindari 'model async wait' yang bikin handler gak jalan.
    """
    global DB_LOADED
    if DB_LOADED:
        return
    async with DB_LOCK:
        if DB_LOADED:
            return
        ACTIVE_CHAT_IDS.clear()
        async for doc in col.find({"enabled": True}, {"_id": 0, "chat_id": 1}):
            ACTIVE_CHAT_IDS.add(int(doc["chat_id"]))
        DB_LOADED = True
        dlog(f"[DB] loaded active chats: {len(ACTIVE_CHAT_IDS)}")

async def set_enabled(chat_id: int, enabled: bool):
    await ensure_db_loaded()
    chat_id = int(chat_id)
    await col.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "enabled": bool(enabled), "updated_at": int(time.time())}},
        upsert=True,
    )
    if enabled:
        ACTIVE_CHAT_IDS.add(chat_id)
    else:
        ACTIVE_CHAT_IDS.discard(chat_id)

async def is_enabled(chat_id: int) -> bool:
    await ensure_db_loaded()
    return int(chat_id) in ACTIVE_CHAT_IDS

# =========================
# COMMANDS (OUTGOING) — stabil
# =========================
@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]ping(\s|$)"))
async def cmd_ping(_, m):
    await ensure_db_loaded()
    dlog("[CMD] ping")
    await m.reply_text("pong")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]id(\s|$)"))
async def cmd_id(_, m):
    await ensure_db_loaded()
    dlog("[CMD] id")
    await m.reply_text(f"chat_id: `{m.chat.id}`", quote=True)

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]on(\s|$)"))
async def cmd_on(_, m):
    await set_enabled(m.chat.id, True)
    dlog(f"[CMD] ON chat={m.chat.id} title={m.chat.title}")
    await m.reply_text("ChatRep ON.")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]off(\s|$)"))
async def cmd_off(_, m):
    await set_enabled(m.chat.id, False)
    dlog(f"[CMD] OFF chat={m.chat.id} title={m.chat.title}")
    await m.reply_text("ChatRep OFF .")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]status(\s|$)"))
async def cmd_status(_, m):
    status = "ON" if await is_enabled(m.chat.id) else "OFF"
    dlog(f"[CMD] status -> {status}")
    await m.reply_text(f"Status ChatRep grup ini: {status}")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]menu(\s|$)"))
async def cmd_menu(_, m):
    status = "ON" if await is_enabled(m.chat.id) else "OFF"
    rules = "\n".join([f"• [{r[2]}] {r[0]} -> {r[1]}" for r in CHATREP_RULES]) or "- (kosong)"
    await m.reply_text(
        "CHATREP USERBOT (MongoDB)\n\n"
        f"Status grup ini : {status}\n"
        f"Cooldown        : {COOLDOWN_SECONDS}s\n\n"
        "Commands:\n"
        "• .ping\n"
        "• .id\n"
        "• .on\n"
        "• .off\n"
        "• .status\n"
        "• .menu\n\n"
        f"Rules:\n{rules}"
    )

# =========================
# AUTO REPLY (pesan orang lain)
# =========================
@app.on_message(filters.group & filters.text & ~filters.outgoing)
async def chatrep_handler(client: Client, m):
    if not is_group(m):
        return

    if not await is_enabled(m.chat.id):
        return

    incoming = m.text or ""
    if not incoming.strip():
        return

    dlog(f"[IN] chat={m.chat.id} text={incoming[:80]!r}")

    for trigger, response, mode in CHATREP_RULES:
        if not match(mode, trigger, incoming):
            continue

        trig_key = normalize(trigger)
        key = (m.chat.id, trig_key)

        now = time.time()
        last = LAST_SENT.get(key, 0.0)
        if now - last < COOLDOWN_SECONDS:
            dlog(f"[COOLDOWN] chat={m.chat.id} trig={trig_key}")
            return
        LAST_SENT[key] = now

        d0, d1 = HUMAN_DELAY_RANGE
        if d1 > 0:
            await asyncio.sleep(random.uniform(d0, d1))

        reply_to = m.id if REPLY_TO_TRIGGER_MESSAGE else None
        dlog(f"[MATCH] chat={m.chat.id} trig={trig_key} -> send")
        await safe_send(client, m.chat.id, response, reply_to=reply_to)
        return

# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("Running ChatRep userbot (MongoDB persistence)...")
    print("Test: .ping di grup harus dibales pong")
    app.run()
