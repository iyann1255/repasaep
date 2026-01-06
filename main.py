import asyncio
import time
import random
from typing import Dict, Tuple

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, RPCError

from config import API_ID, API_HASH, SESSION

# ============================================================
# CHATREP CONFIG (HARDCODE)
# ============================================================
CHATREP_ENABLED = True

# Jika True, bot akan membalas dengan reply ke pesan pemicu.
REPLY_TO_TRIGGER_MESSAGE = True

# Anti spam: minimal jeda per (chat_id, trigger)
COOLDOWN_SECONDS = 8

# Optional: delay biar keliatan "manusia"
HUMAN_DELAY_RANGE = (0.4, 1.3)  # seconds; set (0,0) untuk off

# Trigger mode:
# - "contains": jika trigger ada di dalam teks
# - "exact": harus sama persis
DEFAULT_MATCH_MODE = "contains"

# Daftar rule:
# key: trigger
# value: response string
CHATREP_RULES = [
    # trigger, response, mode(optional)
    ("ubot", "bot gacor di sini @asepvoid", "contains"),

    # contoh tambahan:
    # ("admin", "adminnya lagi AFK", "contains"),
    # ("halo", "yo", "exact"),
]

# Optional: whitelist grup tertentu (kalau kosong -> semua grup)
# Isi dengan chat_id grup (angka negatif biasanya)
ALLOWED_CHAT_IDS = set()  # contoh: {-1001234567890, -1009876543210}

# Optional: blacklist grup tertentu
BLOCKED_CHAT_IDS = set()

# ============================================================
# INTERNAL STATE
# ============================================================
LAST_SENT: Dict[Tuple[int, str], float] = {}  # (chat_id, trigger_lower) -> timestamp

app = Client(
    name="chatrep_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION if SESSION else None,
)

def normalize(text: str) -> str:
    return (text or "").strip().lower()

def is_group(message) -> bool:
    return bool(message.chat) and message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)

def match(mode: str, trigger: str, incoming: str) -> bool:
    mode = (mode or DEFAULT_MATCH_MODE).lower()
    t = normalize(trigger)
    inc = normalize(incoming)

    if not t or not inc:
        return False

    if mode == "exact":
        return inc == t

    # default contains
    return t in inc

def apply_placeholders(template: str, message) -> str:
    """
    Placeholder ringan biar fleksibel:
    {first}    -> first name user
    {username} -> @username (kalau ada)
    {mention}  -> mention user
    {chat}     -> judul grup
    {text}     -> teks masuk
    """
    u = message.from_user
    first = (u.first_name if u else "") or ""
    username = (u.username if u else "") or ""
    mention = (u.mention(first) if u else "") or ""
    chat_title = (message.chat.title if message.chat else "") or ""
    text = message.text or ""

    out = template or ""
    out = out.replace("{first}", first)
    out = out.replace("{username}", f"@{username}" if username else "")
    out = out.replace("{mention}", mention)
    out = out.replace("{chat}", chat_title)
    out = out.replace("{text}", text)
    return out

async def safe_send(client: Client, chat_id: int, text: str, reply_to: int | None):
    try:
        await client.send_message(chat_id, text, reply_to_message_id=reply_to)
    except FloodWait as e:
        await asyncio.sleep(int(e.value) + 1)
        await client.send_message(chat_id, text, reply_to_message_id=reply_to)
    except RPCError:
        # Kalau error kirim pesan (misal permission), skip aja
        return

@app.on_message(filters.group & ~filters.me & filters.text)
async def chatrep_handler(client: Client, message):
    if not CHATREP_ENABLED:
        return

    if not is_group(message):
        return

    chat_id = message.chat.id

    if BLOCKED_CHAT_IDS and chat_id in BLOCKED_CHAT_IDS:
        return

    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        return

    incoming = message.text or ""
    if not incoming.strip():
        return

    # Cari rule pertama yang match
    for rule in CHATREP_RULES:
        trigger = rule[0]
        response = rule[1]
        mode = rule[2] if len(rule) >= 3 else DEFAULT_MATCH_MODE

        if not match(mode, trigger, incoming):
            continue

        # cooldown per trigger per chat
        trig_key = normalize(trigger)
        now = time.time()
        last = LAST_SENT.get((chat_id, trig_key), 0.0)
        if now - last < COOLDOWN_SECONDS:
            return
        LAST_SENT[(chat_id, trig_key)] = now

        # delay human-like
        d0, d1 = HUMAN_DELAY_RANGE
        if d1 > 0:
            await asyncio.sleep(random.uniform(d0, d1))

        out = apply_placeholders(response, message)
        reply_to = message.id if REPLY_TO_TRIGGER_MESSAGE else None

        await safe_send(client, chat_id, out, reply_to=reply_to)
        return  # hanya kirim satu respon

async def main():
    await app.start()
    me = await app.get_me()
    print(f"ChatRep userbot running as: {me.first_name} (@{me.username})")

    # Info cepat
    print("Rules loaded:")
    for r in CHATREP_RULES:
        t, resp = r[0], r[1]
        mode = r[2] if len(r) >= 3 else DEFAULT_MATCH_MODE
        print(f" - [{mode}] {t} -> {resp}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
