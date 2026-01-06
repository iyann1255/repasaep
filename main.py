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

CHATREP_RULES = [
    ("ubot", "bot gacor di sini @asepvoid", "contains"),
]

COOLDOWN_SECONDS = 6
HUMAN_DELAY_RANGE = (0.2, 0.8)
REPLY_TO_TRIGGER_MESSAGE = True

LAST_SENT: Dict[Tuple[int, str], float] = {}
ACTIVE_CHAT_IDS: Set[int] = set()

# =========================
# PYROGRAM CLIENT
# =========================
app = Client("chatrep_userbot", api_id=API_ID, api_hash=API_HASH)

def dlog(msg: str):
    if DEBUG:
        print(msg)

# =========================
# PATCH: skip Peer id invalid
# =========================
from pyrogram.client import Client as PyroClient

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
# MONGODB
# =========================
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo[MONGO_DB]
col = db["chatrep_settings"]

async def load_active_chats():
    ACTIVE_CHAT_IDS.clear()
    async for doc in col.find({"enabled": True}):
        ACTIVE_CHAT_IDS.add(int(doc["chat_id"]))
    dlog(f"[DB] Loaded active chats: {len(ACTIVE_CHAT_IDS)}")

async def set_enabled(chat_id: int, enabled: bool):
    await col.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": enabled, "updated_at": int(time.time())}},
        upsert=True
    )
    if enabled:
        ACTIVE_CHAT_IDS.add(chat_id)
    else:
        ACTIVE_CHAT_IDS.discard(chat_id)

def is_enabled(chat_id: int) -> bool:
    return chat_id in ACTIVE_CHAT_IDS

# =========================
# HELPERS
# =========================
def normalize(text: str) -> str:
    return (text or "").lower().strip()

def is_group(m) -> bool:
    return m.chat and m.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)

def match(mode: str, trigger: str, incoming: str) -> bool:
    t = normalize(trigger)
    i = normalize(incoming)
    return i == t if mode == "exact" else t in i

async def safe_send(client, chat_id, text, reply_to):
    try:
        await client.send_message(chat_id, text, reply_to_message_id=reply_to)
    except FloodWait as e:
        await asyncio.sleep(int(e.value) + 1)
        await client.send_message(chat_id, text, reply_to_message_id=reply_to)
    except RPCError as e:
        dlog(f"[SEND ERROR] {e}")

# =========================
# COMMANDS
# =========================
@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]ping"))
async def ping(_, m):
    await m.reply_text("pong")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]on"))
async def on(_, m):
    await set_enabled(m.chat.id, True)
    await m.reply_text("ChatRep ON (tersimpan)")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]off"))
async def off(_, m):
    await set_enabled(m.chat.id, False)
    await m.reply_text("ChatRep OFF (tersimpan)")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]status"))
async def status(_, m):
    await m.reply_text("ON" if is_enabled(m.chat.id) else "OFF")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]menu"))
async def menu(_, m):
    rules = "\n".join([f"- {r[0]} → {r[1]}" for r in CHATREP_RULES])
    await m.reply_text(
        f"CHATREP (MongoDB)\n\n"
        f"Status: {'ON' if is_enabled(m.chat.id) else 'OFF'}\n\n"
        f"Rules:\n{rules}"
    )

# =========================
# AUTO REPLY
# =========================
@app.on_message(filters.group & filters.text & ~filters.outgoing)
async def chatrep(client, m):
    if not is_group(m):
        return
    if not is_enabled(m.chat.id):
        return

    text = m.text or ""
    for trigger, response, mode in CHATREP_RULES:
        if match(mode, trigger, text):
            key = (m.chat.id, trigger)
            now = time.time()
            if now - LAST_SENT.get(key, 0) < COOLDOWN_SECONDS:
                return
            LAST_SENT[key] = now

            await asyncio.sleep(random.uniform(*HUMAN_DELAY_RANGE))
            await safe_send(client, m.chat.id, response, m.id if REPLY_TO_TRIGGER_MESSAGE else None)
            return

# =========================
# STARTUP TASK
# =========================
async def startup():
    await load_active_chats()
    me = await app.get_me()
    print(f"RUNNING AS: {me.first_name} (@{me.username})")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("Starting ChatRep (MongoDB persistence)...")

    async def runner():
        await app.start()
        await startup()
        await asyncio.Event().wait()

    asyncio.run(runner())
