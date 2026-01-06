import time
import random
from typing import Dict, Tuple, Set

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, RPCError

from config import API_ID, API_HASH

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
HUMAN_DELAY_RANGE = (0.2, 0.8)  # (0,0) kalau mau off
REPLY_TO_TRIGGER_MESSAGE = True

# ON/OFF per grup (bukan global)
ACTIVE_CHAT_IDS: Set[int] = set()

# cooldown state
LAST_SENT: Dict[Tuple[int, str], float] = {}

app = Client("chatrep_userbot", api_id=API_ID, api_hash=API_HASH)


def dlog(msg: str):
    if DEBUG:
        print(msg)


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def is_group_chat(message) -> bool:
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


def safe_send(client: Client, chat_id: int, text: str, reply_to: int | None):
    try:
        client.send_message(chat_id, text, reply_to_message_id=reply_to)
    except FloodWait as e:
        time.sleep(int(e.value) + 1)
        client.send_message(chat_id, text, reply_to_message_id=reply_to)
    except RPCError as e:
        dlog(f"[SEND ERROR] chat={chat_id} err={e}")
        return


# =========================
# COMMANDS (OUTGOING)
# =========================
@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]ping(\s|$)"))
def cmd_ping(client: Client, message):
    dlog("[CMD] ping")
    message.reply_text("pong")


@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]id(\s|$)"))
def cmd_id(client: Client, message):
    dlog("[CMD] id")
    message.reply_text(f"chat_id: `{message.chat.id}`", quote=True)


@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]on(\s|$)"))
def cmd_on(client: Client, message):
    ACTIVE_CHAT_IDS.add(message.chat.id)
    dlog(f"[CMD] ON chat={message.chat.id} title={message.chat.title}")
    message.reply_text("ChatRep ON di grup ini.")


@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]off(\s|$)"))
def cmd_off(client: Client, message):
    ACTIVE_CHAT_IDS.discard(message.chat.id)
    dlog(f"[CMD] OFF chat={message.chat.id} title={message.chat.title}")
    message.reply_text("ChatRep OFF di grup ini.")


@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]status(\s|$)"))
def cmd_status(client: Client, message):
    status = "ON" if message.chat.id in ACTIVE_CHAT_IDS else "OFF"
    dlog(f"[CMD] status -> {status}")
    message.reply_text(f"Status ChatRep grup ini: {status}")


@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]menu(\s|$)"))
def cmd_menu(client: Client, message):
    status = "ON" if message.chat.id in ACTIVE_CHAT_IDS else "OFF"
    rules = "\n".join([f"• [{r[2]}] {r[0]} -> {r[1]}" for r in CHATREP_RULES]) or "- (kosong)"
    dlog("[CMD] menu")
    message.reply_text(
        "CHATREP USERBOT\n\n"
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
# AUTO REPLY (PESAN ORANG LAIN)
# =========================
@app.on_message(filters.group & filters.text & ~filters.outgoing)
def chatrep_handler(client: Client, message):
    if not is_group_chat(message):
        return

    chat_id = message.chat.id

    # hanya grup yang di-ON
    if chat_id not in ACTIVE_CHAT_IDS:
        return

    incoming = message.text or ""
    if not incoming.strip():
        return

    dlog(f"[IN] chat={chat_id} text={incoming[:80]!r}")

    for trigger, response, mode in CHATREP_RULES:
        if not match(mode, trigger, incoming):
            continue

        trig_key = normalize(trigger)
        now = time.time()
        last = LAST_SENT.get((chat_id, trig_key), 0.0)
        if now - last < COOLDOWN_SECONDS:
            dlog(f"[COOLDOWN] chat={chat_id} trig={trig_key}")
            return
        LAST_SENT[(chat_id, trig_key)] = now

        d0, d1 = HUMAN_DELAY_RANGE
        if d1 > 0:
            time.sleep(random.uniform(d0, d1))

        reply_to = message.id if REPLY_TO_TRIGGER_MESSAGE else None
        dlog(f"[MATCH] chat={chat_id} trig={trig_key} -> send")
        safe_send(client, chat_id, response, reply_to=reply_to)
        return


if __name__ == "__main__":
    me = None
    app.start()
    me = app.get_me()
    print(f"RUNNING AS: {me.first_name} (@{me.username}) | is_deleted={getattr(me, 'is_deleted', None)}")
    print("Test: ketik .ping di grup. Kalau dibalas pong, command sudah hidup.")
    app.run()
