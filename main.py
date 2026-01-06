import asyncio
import time
import random
from typing import Dict, Tuple

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, RPCError

from config import API_ID, API_HASH, SESSION

# ============================================================
# CHATREP RULES (HARDCODE)
# ============================================================
# mode: "contains" | "exact"
CHATREP_RULES = [
    ("ubot", "bot gacor di sini @asepvoid", "contains"),
]

DEFAULT_MATCH_MODE = "contains"

# ============================================================
# ON/OFF PER GRUP (BUKAN GLOBAL)
# ============================================================
ACTIVE_CHAT_IDS = set()  # grup yang sudah di-ON-in

# Anti spam per (chat_id, trigger)
COOLDOWN_SECONDS = 8
LAST_SENT: Dict[Tuple[int, str], float] = {}

# Optional: delay biar keliatan manusia
HUMAN_DELAY_RANGE = (0.4, 1.2)  # set (0,0) untuk off delay

# Reply ke pesan pemicu
REPLY_TO_TRIGGER_MESSAGE = True

# Debug log ke console
DEBUG = True

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
    return t in inc  # contains

def apply_placeholders(template: str, message) -> str:
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
    except RPCError as e:
        if DEBUG:
            print(f"[SEND ERROR] chat={chat_id} err={e}")
        return

# ============================================================
# COMMANDS (HANYA KAMU) - pakai regex biar gak rewel
# ============================================================

@app.on_message(filters.me & filters.group & filters.regex(r"^[./]on(\s|$)"))
async def rep_on(client: Client, message):
    chat_id = message.chat.id
    ACTIVE_CHAT_IDS.add(chat_id)
    if DEBUG:
        print(f"[ON] chat_id={chat_id} title={message.chat.title}")
    await message.reply_text("ChatRep ON di grup ini.")

@app.on_message(filters.me & filters.group & filters.regex(r"^[./]off(\s|$)"))
async def rep_off(client: Client, message):
    chat_id = message.chat.id
    ACTIVE_CHAT_IDS.discard(chat_id)
    if DEBUG:
        print(f"[OFF] chat_id={chat_id} title={message.chat.title}")
    await message.reply_text("ChatRep OFF di grup ini.")

@app.on_message(filters.me & filters.group & filters.regex(r"^[./]status(\s|$)"))
async def rep_status(client: Client, message):
    chat_id = message.chat.id
    status = "ON" if chat_id in ACTIVE_CHAT_IDS else "OFF"
    await message.reply_text(f"Status ChatRep grup ini: {status}")

@app.on_message(filters.me & filters.group & filters.regex(r"^[./]id(\s|$)"))
async def rep_id(client: Client, message):
    await message.reply_text(f"chat_id: `{message.chat.id}`", quote=True)

@app.on_message(filters.me & filters.group & filters.regex(r"^[./]menu(\s|$)"))
async def rep_menu(client: Client, message):
    chat_id = message.chat.id
    status = "ON" if chat_id in ACTIVE_CHAT_IDS else "OFF"

    rules = []
    for trig, resp, mode in CHATREP_RULES:
        rules.append(f"• [{mode}] {trig} -> {resp}")

    txt = (
        "CHATREP USERBOT\n\n"
        f"Status grup ini : {status}\n"
        f"Cooldown        : {COOLDOWN_SECONDS}s\n\n"
        "Commands:\n"
        "• .on / /on\n"
        "• .off / /off\n"
        "• .status\n"
        "• .id\n"
        "• .menu\n\n"
        "Rules:\n" + ("\n".join(rules) if rules else "- (kosong)")
    )
    await message.reply_text(txt)

# ============================================================
# AUTO REPLY (HANYA DI GRUP YANG DI-ON-in)
# ============================================================

@app.on_message(filters.group & ~filters.me & filters.text)
async def chatrep_handler(client: Client, message):
    if not is_group(message):
        return

    chat_id = message.chat.id

    if chat_id not in ACTIVE_CHAT_IDS:
        if DEBUG:
            print(f"[SKIP] chat {chat_id} belum ON")
        return

    incoming = message.text or ""
    if not incoming.strip():
        return

    if DEBUG:
        u = message.from_user
        who = f"{u.first_name} (@{u.username})" if u else "Unknown"
        print(f"[IN] chat={chat_id} from={who}: {incoming[:80]}")

    for trigger, response, mode in CHATREP_RULES:
        if not match(mode, trigger, incoming):
            continue

        trig_key = normalize(trigger)

        # cooldown
        now = time.time()
        last = LAST_SENT.get((chat_id, trig_key), 0.0)
        if now - last < COOLDOWN_SECONDS:
            if DEBUG:
                print(f"[COOLDOWN] chat={chat_id} trigger={trig_key}")
            return
        LAST_SENT[(chat_id, trig_key)] = now

        # human delay
        d0, d1 = HUMAN_DELAY_RANGE
        if d1 > 0:
            await asyncio.sleep(random.uniform(d0, d1))

        out = apply_placeholders(response, message)
        reply_to = message.id if REPLY_TO_TRIGGER_MESSAGE else None

        if DEBUG:
            print(f"[MATCH] chat={chat_id} trigger={trig_key} -> send")

        await safe_send(client, chat_id, out, reply_to=reply_to)
        return

async def main():
    await app.start()
    me = await app.get_me()
    print(f"ChatRep userbot running as: {me.first_name} (@{me.username})")
    print("Note: Semua grup OFF dulu. Ketik .on di grup yang mau diaktifin.")

    try:
        await asyncio.Event().wait()
    finally:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped (CTRL+C).")
