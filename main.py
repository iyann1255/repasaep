import asyncio
import time
import random
from typing import Dict, Tuple

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, RPCError

from config import API_ID, API_HASH, SESSION

# ============================================================
# CHATREP RULES (HARDCODE DI CODE)
# ============================================================
# Format: (trigger, response, mode)
# mode: "contains" | "exact"
CHATREP_RULES = [
    ("ubot", "bot gacor di sini @asepvoid", "contains"),
    # contoh:
    # ("halo", "yo", "exact"),
    # ("musik", "{mention} musik ubot ready", "contains"),
]

DEFAULT_MATCH_MODE = "contains"

# ============================================================
# ON/OFF PER GRUP (BUKAN GLOBAL)
# ============================================================
# Default kosong = semua grup OFF sampai kamu ketik .on di grup itu
ACTIVE_CHAT_IDS = set()  # chat_id grup yang sudah di-ON-in

# Anti spam per (chat_id, trigger)
COOLDOWN_SECONDS = 8
LAST_SENT: Dict[Tuple[int, str], float] = {}

# Optional: delay biar keliatan manusia
HUMAN_DELAY_RANGE = (0.4, 1.2)  # set (0,0) buat matiin delay

# Optional: balas sebagai reply ke pesan pemicu
REPLY_TO_TRIGGER_MESSAGE = True

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
    """
    Placeholder ringan:
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
        # permission error / slowmode / dll -> skip
        return

# ============================================================
# COMMANDS (HANYA KAMU YANG BISA)
# ============================================================
@app.on_message(filters.me & filters.command("on", prefixes="."))
async def rep_on(client: Client, message):
    if not is_group(message):
        return await message.reply_text("Pakai di grup (bukan PM).")

    ACTIVE_CHAT_IDS.add(message.chat.id)
    await message.reply_text("ChatRep ON di grup ini.")

@app.on_message(filters.me & filters.command("off", prefixes="."))
async def rep_off(client: Client, message):
    if not is_group(message):
        return await message.reply_text("Pakai di grup (bukan PM).")

    ACTIVE_CHAT_IDS.discard(message.chat.id)
    await message.reply_text("ChatRep OFF di grup ini.")

@app.on_message(filters.me & filters.command("menu", prefixes="."))
async def menu(client: Client, message):
    status = "ON" if (message.chat and message.chat.id in ACTIVE_CHAT_IDS) else "OFF"
    rules = []
    for r in CHATREP_RULES:
        trig = r[0]
        mode = r[2] if len(r) >= 3 else DEFAULT_MATCH_MODE
        rules.append(f"• [{mode}] {trig}")

    rules_text = "\n".join(rules) if rules else "- (belum ada)"
    text = (
        "CHATREP USERBOT\n\n"
        f"Status grup ini : {status}\n"
        f"Cooldown        : {COOLDOWN_SECONDS}s\n"
        f"Reply mode      : {'reply' if REPLY_TO_TRIGGER_MESSAGE else 'send'}\n\n"
        "Commands:\n"
        "• .on   -> aktifkan di grup ini\n"
        "• .off  -> matikan di grup ini\n"
        "• .menu -> tampilkan menu\n\n"
        "Triggers:\n"
        f"{rules_text}\n\n"
        "Catatan:\n"
        "Trigger disimpan di code (CHATREP_RULES)."
    )
    await message.reply_text(text)

# ============================================================
# AUTO REPLY (JALAN HANYA DI GRUP YANG DI-ON-IN)
# ============================================================
@app.on_message(filters.group & ~filters.me & filters.text)
async def chatrep_handler(client: Client, message):
    if not is_group(message):
        return

    chat_id = message.chat.id

    # ✅ KUNCI UTAMA: hanya aktif di grup yang sudah .on
    if chat_id not in ACTIVE_CHAT_IDS:
        return

    incoming = message.text or ""
    if not incoming.strip():
        return

    for rule in CHATREP_RULES:
        trigger = rule[0]
        response = rule[1]
        mode = rule[2] if len(rule) >= 3 else DEFAULT_MATCH_MODE

        if not match(mode, trigger, incoming):
            continue

        trig_key = normalize(trigger)

        # cooldown anti spam
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
        return  # kirim 1 respon aja

async def main():
    await app.start()
    me = await app.get_me()
    print(f"ChatRep userbot running as: {me.first_name} (@{me.username})")
    print("Note: Semua grup OFF dulu. Ketik .on di grup yang mau diaktifin.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
