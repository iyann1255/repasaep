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

# Trigger rules: (trigger, response, mode)
# mode: "contains" | "exact"
CHATREP_RULES = [
    ("ubot", "bot gacor di sini @asepvoid", "contains"),
]

COOLDOWN_SECONDS = 6
HUMAN_DELAY_RANGE = (0.2, 0.8)  # (0,0) untuk off
REPLY_TO_TRIGGER_MESSAGE = True

# cooldown state (in-memory)
LAST_SENT: Dict[Tuple[int, str], float] = {}

# =========================
# PYROGRAM APP
# =========================
app = Client("chatrep_userbot", api_id=API_ID, api_hash=API_HASH)

def dlog(msg: str):
    if DEBUG:
        print(msg)

def normalize(text: str) -> str:
    return (text or "").strip().lower()

def is_group(message) -> bool:
    return bool(message.chat) and message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)

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
        return

# ============================================================
# PATCH (OPSI 1): Skip update yang error "Peer id invalid"
# ============================================================
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
# MONGODB
# =========================
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo[MONGO_DB]
col = db["chatrep_settings"]

# Cache ON groups in memory (loaded from DB on start)
ACTIVE_CHAT_IDS: Set[int] = set()

async def db_load_active_chats():
    ACTIVE_CHAT_IDS.clear()
    async for doc in col.find({"enabled": True}, {"_id": 0, "chat_id": 1}):
        ACTIVE_CHAT_IDS.add(int(doc["chat_id"]))
    dlog(f"[DB] Loaded active chats: {len(ACTIVE_CHAT_IDS)}")

async def db_set_enabled(chat_id: int, enabled: bool):
    await col.update_one(
        {"chat_id": int(chat_id)},
        {"$set": {"chat_id": int(chat_id), "enabled": bool(enabled), "updated_at": int(time.time())}},
        upsert=True,
    )
    if enabled:
        ACTIVE_CHAT_IDS.add(int(chat_id))
    else:
        ACTIVE_CHAT_IDS.discard(int(chat_id))

async def db_is_enabled(chat_id: int) -> bool:
    # use memory cache (fast)
    return int(chat_id) in ACTIVE_CHAT_IDS

# =========================
# COMMANDS (OUTGOING)
# =========================
@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]ping(\s|$)"))
async def cmd_ping(_, m):
    dlog("[CMD] ping")
    await m.reply_text("pong")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]id(\s|$)"))
async def cmd_id(_, m):
    dlog("[CMD] id")
    await m.reply_text(f"chat_id: `{m.chat.id}`", quote=True)

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]on(\s|$)"))
async def cmd_on(_, m):
    await db_set_enabled(m.chat.id, True)
    dlog(f"[CMD] ON chat={m.chat.id} title={m.chat.title}")
    await m.reply_text("ChatRep ON di grup ini (tersimpan).")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]off(\s|$)"))
async def cmd_off(_, m):
    await db_set_enabled(m.chat.id, False)
    dlog(f"[CMD] OFF chat={m.chat.id} title={m.chat.title}")
    await m.reply_text("ChatRep OFF di grup ini (tersimpan).")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]status(\s|$)"))
async def cmd_status(_, m):
    status = "ON" if await db_is_enabled(m.chat.id) else "OFF"
    dlog(f"[CMD] status -> {status}")
    await m.reply_text(f"Status ChatRep grup ini: {status}")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]menu(\s|$)"))
async def cmd_menu(_, m):
    status = "ON" if await db_is_enabled(m.chat.id) else "OFF"
    rules = "\n".join([f"• [{r[2]}] {r[0]} -> {r[1]}" for r in CHATREP_RULES]) or "- (kosong)"
    dlog("[CMD] menu")
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
        f"Rules:\n{rules}\n\n"
        f"Active cached groups: {len(ACTIVE_CHAT_IDS)}"
    )

# =========================
# AUTO REPLY (PESAN ORANG LAIN)
# =========================
@app.on_message(filters.group & filters.text & ~filters.outgoing)
async def chatrep_handler(client: Client, m):
    if not is_group(m):
        return

    chat_id = m.chat.id
    if not await db_is_enabled(chat_id):
        return

    incoming = m.text or ""
    if not incoming.strip():
        return

    dlog(f"[IN] chat={chat_id} text={incoming[:80]!r}")

    for trigger, response, mode in CHATREP_RULES:
        if not match(mode, trigger, incoming):
            continue

        trig_key = normalize(trigger)

        # cooldown
        now = time.time()
        last = LAST_SENT.get((chat_id, trig_key), 0.0)
        if now - last < COOLDOWN_SECONDS:
            dlog(f"[COOLDOWN] chat={chat_id} trig={trig_key}")
            return
        LAST_SENT[(chat_id, trig_key)] = now

        # delay
        d0, d1 = HUMAN_DELAY_RANGE
        if d1 > 0:
            await asyncio.sleep(random.uniform(d0, d1))

        reply_to = m.id if REPLY_TO_TRIGGER_MESSAGE else None
        dlog(f"[MATCH] chat={chat_id} trig={trig_key} -> send")
        await safe_send(client, chat_id, response, reply_to=reply_to)
        return

# =========================
# RUN
# =========================
async def _startup():
    # Load enabled chats from DB once on startup
    await db_load_active_chats()
    me = await app.get_me()
    print(f"RUNNING AS: {me.first_name} (@{me.username}) | is_deleted={getattr(me, 'is_deleted', None)}")
    print("Test: .ping, lalu .on di grup target. Status tersimpan di MongoDB.")

if __name__ == "__main__":
    print("Running ChatRep userbot (MongoDB persistence)...")
    # app.run() akan start client & loop
    # kita inject startup via on_start callback-style: jalankan saat client sudah start
    @app.on_start()
    async def _on_start(client):
        await _startup()

    app.run()
