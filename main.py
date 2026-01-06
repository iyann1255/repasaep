import asyncio
import random
import time
from typing import Dict, Tuple, Set, Union, List

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
# response bisa str atau list[str]
CHATREP_RULES = [
    # ===== BOT / UBOT =====
    ("ubot", ["bot gacor di sini @asepvoid", "ubot gacor ada", "gas ke @asepvoid", "ubot aman kak"], "contains"),
    ("userbot", ["userbot gacor ada", "userbot aman", "userbot jalan kak", "userbot aktif"], "contains"),
    ("bot", ["bukan bot", "apalah", "halu kak", "kok bot sih"], "contains"),
    ("ai", ["halu dikit", "ai apaan", "ga ngerti ai", "kok ai"], "contains"),
    ("robot", ["aku manusia", "bukan robot", "human kak", "ngaco lu"], "contains"),
    ("auto", ["auto kak", "auto jalan", "auto gas", "auto aja"], "contains"),
    ("script", ["spill script", "mana script", "kirim dulu"], "contains"),
    ("kode", ["spill kode", "kirim kodenya", "mana kodenya"], "contains"),

    # ===== SAPAAN =====
    ("hai", ["yo", "hai juga", "halo", "apa kabar"], "exact"),
    ("halo", ["yo", "halo juga", "apa kak", "iya"], "contains"),
    ("hallo", ["yo", "halo", "hai juga", "apa"], "contains"),
    ("p", ["yo", "apa", "kenapa"], "exact"),
    ("oi", ["apa", "kenapa", "hah"], "contains"),
    ("oy", ["kenapa", "apa kak", "hah"], "contains"),
    ("woi", ["apa kak", "kenapa", "hah"], "contains"),
    ("weh", ["apa", "kenapa", "hah"], "contains"),
    ("eh", ["kenapa", "apa", "hah"], "contains"),
    ("bro", ["iya bro", "siap bro", "gas bro", "apa bro"], "contains"),
    ("kak", ["iya kak", "kenapa kak", "apa kak", "hm"], "contains"),
    ("bang", ["siap bang", "kenapa bang", "apa bang", "hm"], "contains"),
    ("gan", ["siap gan", "kenapa gan", "apa gan"], "contains"),
    ("min", ["iya min", "kenapa min", "apa min"], "contains"),
    ("bos", ["siap bos", "kenapa bos", "apa bos"], "contains"),
    ("cuy", ["apa cuy", "kenapa cuy", "gas cuy"], "contains"),
    ("cuk", ["apa cuk", "waduh", "wkwk"], "contains"),
    ("sis", ["iya sis", "kenapa sis", "apa sis"], "contains"),
    ("bestie", ["iya bestie", "kenapa", "gas"], "contains"),
    ("beb", ["iya beb", "kenapa", "apa"], "contains"),
    ("ayang", ["iya ayang", "kenapa", "apa"], "contains"),

    # ===== KEHADIRAN =====
    ("hadir", ["hadir kak", "siap hadir", "gas", "hadir min"], "contains"),
    ("online", ["hadir", "online kak", "siap", "hadir kak"], "contains"),
    ("off", ["gas dulu", "off dulu", "cabut dulu", "oke"], "contains"),
    ("offline", ["oke", "gas dulu", "cabut", "hati-hati"], "contains"),
    ("afk", ["oke kak", "siap", "ditunggu", "gas"], "contains"),
    ("brb", ["ditunggu", "oke kak", "siap", "balik lagi"], "contains"),
    ("balik", ["gas", "akhirnya", "oke", "hadir lagi"], "contains"),
    ("gone", ["oke", "gas", "hati-hati"], "contains"),

    # ===== LOKASI / GERAK =====
    ("live", ["dimana kak", "lagi dimana", "lokasi mana", "shareloc dong"], "contains"),
    ("tmo", ["dimana kak", "lokasi mana", "shareloc kak", "tmo mana"], "contains"),
    ("otw", ["otw kak", "gas", "hati-hati", "siap jalan"], "contains"),
    ("otwe", ["otw kak", "gas", "hati-hati"], "contains"),
    ("dbyohh", ["otwe kak", "gas otw", "siap jalan"], "contains"),
    ("nyampe", ["aman kak", "sip", "akhirnya", "gas"], "contains"),
    ("sampe", ["sip", "aman", "gas", "akhirnya"], "contains"),
    ("sampai", ["sip", "aman", "gas", "akhirnya"], "contains"),
    ("datang", ["siap nyusul", "gas", "otw", "nyusul"], "contains"),
    ("jalan", ["hati-hati", "aman kak", "gas", "jangan ngebut"], "contains"),
    ("pulang", ["hati-hati", "aman kak", "gas", "jangan lupa kabar"], "contains"),
    ("jemput", ["gas", "otw", "siap", "jemput dimana"], "contains"),
    ("nunggu", ["ditunggu", "sabar", "oke", "bentar"], "contains"),
    ("nungguin", ["ditunggu", "sabar", "oke"], "contains"),

    # ===== AJAKAN =====
    ("call", ["ayukk kak", "gas call", "kapan call", "join call"], "contains"),
    ("vc", ["yukk kak", "gas vc", "masuk vc", "join vc"], "contains"),
    ("koll", ["ayukk koll kak", "gas koll", "join koll", "koll gas"], "contains"),
    ("join", ["ikut kak", "gas masuk", "mana link", "ayo"], "contains"),
    ("masuk", ["gas kak", "ikut", "oke", "ayok"], "contains"),
    ("nongkrong", ["gas kak", "ayuk", "dimana", "kuy"], "contains"),
    ("mabar", ["gas mabar", "ayuk mabar", "main apa", "kuy"], "contains"),
    ("push", ["gas push", "ayuk push", "rank berapa", "kuy"], "contains"),
    ("duo", ["gas duo", "kuy", "ayok"], "contains"),
    ("party", ["gas party", "kuy", "ikut"], "contains"),

    # ===== PERTANYAAN UMUM =====
    ("apa", ["iya kenapa", "kenapa kak", "apa kak", "hah", "apaan"], "contains"),
    ("apaan", ["apaan", "hah", "kenapa", "apasi"], "contains"),
    ("apasih", ["apaan", "hah", "kenapa", "apasi"], "contains"),
    ("kenapa", ["gatau kak", "kenapa emang", "kurang tau", "kenapa tuh", "hah"], "contains"),
    ("knp", ["gatau kak", "kenapa emang", "kenapa tuh"], "contains"),
    ("kok", ["gatau kak", "kok bisa", "iya ya", "aneh ya", "lah iya"], "contains"),
    ("siapa", ["gatau kak", "kurang tau", "siapa tuh", "siapa emang"], "contains"),
    ("dimana", ["kurang tau", "dimana emang", "lokasi mana", "shareloc"], "contains"),
    ("dmn", ["lokasi mana", "dimana emang", "shareloc"], "contains"),
    ("kapan", ["nanti kak", "belum tau", "kayaknya nanti", "ntar"], "contains"),
    ("kpn", ["nanti", "belum tau", "ntar"], "contains"),
    ("gimana", ["jalanin aja", "pelan-pelan", "aman kak", "gitu aja", "yaudah"], "contains"),
    ("gmn", ["pelan-pelan", "jalanin aja", "aman"], "contains"),
    ("berapa", ["kurang tau", "ga ngitung", "sekitar segitu", "brp emang"], "contains"),
    ("brp", ["kurang tau", "sekitar segitu", "ga ngitung"], "contains"),

    # ===== REAKSI / EKSPRESI =====
    ("anu", ["anu apanya kak", "anu yang mana", "hah anu"], "contains"),
    ("becek", ["waduh becek", "becek bener", "hati-hati licin"], "contains"),
    ("wkwk", ["wkwk", "ngakak", "ketawa mulu", "wkwkwk"], "contains"),
    ("wk", ["wkwk", "ngakak", "wkwk"], "contains"),
    ("haha", ["wkwk", "ngakak", "haha juga"], "contains"),
    ("hehe", ["hehe", "wkwk", "asik"], "contains"),
    ("lol", ["ngakak", "wkwk"], "contains"),
    ("anjir", ["santai kak", "waduh", "parah", "anjir juga"], "contains"),
    ("njir", ["waduh", "anjir", "wkwk"], "contains"),
    ("jir", ["wkwk", "anjir", "waduh"], "contains"),
    ("buset", ["waduh", "parah", "anjir"], "contains"),
    ("gila", ["anjir", "parah", "gokil"], "contains"),
    ("parah", ["waduh", "parah juga", "gila"], "contains"),
    ("waduh", ["waduh", "lah iya", "santai"], "contains"),
    ("yah", ["yah", "waduh", "lain kali"], "contains"),
    ("lah", ["iya juga", "lah iya", "wkwk"], "contains"),
    ("loh", ["iya ya", "loh iya", "wkwk"], "contains"),
    ("anjay", ["mantap", "wkwk", "gas"], "contains"),

    # ===== MEDIA =====
    ("pap", ["kirim kak ke cpc", "spill kak", "gas pap", "mana pap"], "contains"),
    ("foto", ["spill kak", "kirim kak", "gas", "mana foto"], "contains"),
    ("video", ["spill kak", "kirim kak", "gas", "mana video"], "contains"),
    ("vidio", ["spill kak", "kirim kak", "gas"], "contains"),
    ("ss", ["spill kak", "mana ss", "kirim dulu", "mana ss nya"], "contains"),
    ("rekam", ["gas kak", "spill", "kirim"], "contains"),
    ("bukti", ["mana bukti", "spill", "kirim"], "contains"),
    ("link", ["mana link", "kirim link", "spill link"], "contains"),

    # ===== OPINI / STATUS =====
    ("serius", ["serius dikit", "beneran?", "waduh", "fix?"], "contains"),
    ("beneran", ["iya", "serius", "fix", "beneran nih"], "contains"),
    ("bener", ["iya kak", "bener juga", "mantap"], "contains"),
    ("salah", ["waduh", "yah", "skip"], "contains"),
    ("aman", ["aman kak", "sip", "gas"], "contains"),
    ("bahaya", ["waduh kak", "hati-hati", "ngeri"], "contains"),
    ("ribet", ["santai kak", "pelan-pelan", "yaudah"], "contains"),
    ("gampang", ["aman kak", "gas", "sip"], "contains"),

    # ===== EMOSI =====
    ("capek", ["istirahat kak", "rebahan dulu", "sabar"], "contains"),
    ("lelah", ["rebahan dulu", "istirahat", "santai"], "contains"),
    ("ngantuk", ["tidur kak", "met tidur", "istirahat"], "contains"),
    ("lapar", ["makan dulu", "met makan", "gas makan"], "contains"),
    ("haus", ["minum dulu", "gas minum", "jangan dehidrasi"], "contains"),
    ("bete", ["santai kak", "tarik napas", "waduh"], "contains"),
    ("stress", ["tarik napas", "santai dulu", "istirahat"], "contains"),
    ("sedih", ["sabar kak", "jangan sedih", "pelan-pelan"], "contains"),
    ("marah", ["santai kak", "tenang dulu", "waduh"], "contains"),
    ("kesel", ["tarik napas", "santai", "waduh"], "contains"),
    ("takut", ["santai kak", "aman", "tenang"], "contains"),
    ("panik", ["tenang dulu", "aman", "pelan-pelan"], "contains"),
    ("seneng", ["mantap kak", "gas", "asik"], "contains"),
    ("bahagia", ["mantap kak", "gas", "asik"], "contains"),

    # ===== WAKTU =====
    ("sekarang", ["iya kak", "gas sekarang", "oke"], "contains"),
    ("nanti", ["siap kak", "nanti ya", "oke"], "contains"),
    ("besok", ["gas besok", "oke besok", "siap"], "contains"),
    ("pagi", ["pagi kak", "gas", "mantap"], "contains"),
    ("siang", ["siang kak", "gas", "oke"], "contains"),
    ("sore", ["sore kak", "gas", "oke"], "contains"),
    ("malam", ["gas malem", "malem ya", "oke"], "contains"),
    ("malem", ["gas malem", "malem ya", "oke"], "contains"),

    # ===== AKTIVITAS =====
    ("kerja", ["semangat kak", "gas kerja", "jangan capek"], "contains"),
    ("kuliah", ["semangat kak", "gas kuliah", "jangan bolos"], "contains"),
    ("sekolah", ["semangat kak", "gas sekolah", "jangan telat"], "contains"),
    ("belajar", ["gas belajar", "semangat", "pelan-pelan"], "contains"),
    ("main", ["gas main", "main apa", "ayuk"], "contains"),
    ("tidur", ["met tidur", "tidur kak", "istirahat"], "contains"),
    ("mandi", ["gas mandi", "siap kak", "jangan kelamaan"], "contains"),
    ("makan", ["met makan", "gas makan", "jangan lupa makan"], "contains"),

    # ===== PENILAIAN =====
    ("mantap", ["mantap", "gas", "sip"], "contains"),
    ("keren", ["mantap kak", "gokil", "gas"], "contains"),
    ("gokil", ["gokil", "mantap", "gas"], "contains"),
    ("bagus", ["bagus", "mantap", "sip"], "contains"),
    ("jelek", ["waduh", "yah", "skip"], "contains"),
    ("lucu", ["wkwk", "ngakak", "asik"], "contains"),
    ("aneh", ["iya juga", "aneh ya", "wkwk"], "contains"),

    # ===== INTERNET SLANG =====
    ("fix", ["iya fix", "fix bener", "fix sih"], "contains"),
    ("real", ["real sih", "iya real", "bener"], "contains"),
    ("relate", ["relate banget", "iya relate", "bener sih"], "contains"),
    ("valid", ["valid sih", "iya valid", "bener"], "contains"),
    ("skip", ["skip dulu", "yaudah", "next"], "contains"),
    ("next", ["gas next", "lanjut", "oke"], "contains"),
    ("spill", ["spill kak", "mana spill", "kirim"], "contains"),
    ("receh", ["wkwk", "ngakak", "receh amat"], "contains"),

    # ===== PENUTUP =====
    ("makasih", ["siap kak", "sama-sama", "aman"], "contains"),
    ("terimakasih", ["sama-sama", "siap kak", "aman"], "contains"),
    ("thanks", ["siap", "aman", "sama-sama"], "contains"),
    ("thx", ["siap", "aman"], "contains"),
    ("bye", ["gas dulu", "hati-hati", "aman"], "contains"),
    ("dadah", ["hati-hati", "aman kak", "gas"], "contains"),
    ("cabut", ["gas kak", "aman", "bye"], "contains"),

    # ===== VARIAN "APA" / "KENAPA" / "KOK" (lebih banyak) =====
    ("apasi", ["iya kenapa", "apasi", "hah", "kenapa tuh"], "contains"),
    ("apaan sih", ["apaan", "kenapa", "hah"], "contains"),
    ("apa sih", ["apaan", "kenapa", "hah"], "contains"),
    ("apa aja", ["apa tuh", "gatau", "hmm"], "contains"),
    ("apa tuh", ["hah", "apa", "kenapa"], "contains"),
    ("apatu", ["hah", "apa", "kenapa"], "contains"),
    ("apaaan", ["apaan", "hah", "kenapa"], "contains"),
    ("apaaa", ["iya kenapa", "apaan"], "contains"),
    ("kenapaa", ["kenapa tuh", "gatau", "kenapa emang"], "contains"),
    ("kenapaaa", ["kenapa tuh", "gatau", "hah"], "contains"),
    ("knpaa", ["kenapa tuh", "gatau", "hah"], "contains"),
    ("knp sih", ["kenapa emang", "gatau", "hah"], "contains"),
    ("kenapa sih", ["kenapa emang", "gatau", "hah"], "contains"),
    ("kok bisa", ["iya ya", "aneh ya", "gatau"], "contains"),
    ("kok gitu", ["iya ya", "aneh ya", "wkwk"], "contains"),
    ("kok sih", ["iya ya", "gatau", "waduh"], "contains"),
    ("kok ya", ["iya ya", "aneh ya"], "contains"),
    ("kok bisa sih", ["iya ya", "aneh ya", "gatau"], "contains"),

    # ===== VARIAN "IYA / YA / OKE" biar gak 1 respon =====
    ("iya", ["oke", "iya", "siap", "iya kak", "oke kak", "iya bro", "iyain aja"], "contains"),
    ("iyaaa", ["oke kak", "siap", "iya", "iya dong"], "contains"),
    ("iyah", ["iya", "oke", "siap", "iyahh"], "contains"),
    ("ya", ["iya", "oke", "siap", "yaudah"], "contains"),
    ("yaa", ["iya", "oke", "siap", "yaudah"], "contains"),
    ("y", ["iya", "oke", "siap"], "exact"),
    ("yoi", ["yoi", "gas", "siap", "mantap"], "contains"),
    ("yoii", ["gas", "yoi", "siap"], "contains"),
    ("sip", ["sip", "aman", "gas", "oke"], "contains"),
    ("sipp", ["sip", "gas", "aman"], "contains"),
    ("oke", ["oke", "siap", "aman", "gas"], "contains"),
    ("okeh", ["okeh", "siap", "aman"], "contains"),
    ("ok", ["ok", "siap", "aman"], "contains"),
    ("okey", ["ok", "siap", "aman"], "contains"),
    ("deal", ["deal", "gas", "siap"], "contains"),
    ("setuju", ["gas", "iya", "setuju", "oke"], "contains"),
    ("boleh", ["boleh", "gas", "oke"], "contains"),
    ("boleh sih", ["boleh", "gas", "oke"], "contains"),
    ("gas", ["gas", "ayo", "siap", "kuy"], "contains"),
    ("gass", ["gas", "ayo", "siap"], "contains"),
    ("gaskeun", ["gas", "ayo", "kuy"], "contains"),
    ("lanjut", ["gas lanjut", "oke", "siap", "next"], "contains"),

    # ===== PENOLAKAN / NEGASI (varian typo) =====
    ("ga", ["waduh", "yah", "oke", "yaudah"], "contains"),
    ("g", ["waduh", "yah", "oke"], "exact"),
    ("gak", ["waduh", "yah", "oke", "yaudah"], "contains"),
    ("gk", ["waduh", "yah", "oke"], "contains"),
    ("nggak", ["waduh", "yah", "oke"], "contains"),
    ("ngga", ["waduh", "yah", "oke"], "contains"),
    ("engga", ["waduh", "yah", "oke"], "contains"),
    ("enggak", ["waduh", "yah", "oke"], "contains"),
    ("kagak", ["waduh", "yaudah", "oke"], "contains"),
    ("tidak", ["oke", "yah", "sip"], "contains"),
    ("batal", ["oke kak", "yah", "lain kali", "yaudah"], "contains"),
    ("skip", ["skip dulu", "yaudah", "next"], "contains"),
    ("gajadi", ["oke", "yaudah", "lain kali"], "contains"),
    ("ga jadi", ["oke", "yaudah", "lain kali"], "contains"),

    # ===== “GIMANA” / “DIMANA” / “KAPAN” versi singkatan =====
    ("dmn", ["lokasi mana", "dimana emang", "shareloc"], "contains"),
    ("dmna", ["lokasi mana", "dimana emang", "shareloc"], "contains"),
    ("dmmn", ["lokasi mana", "dimana emang", "shareloc"], "contains"),
    ("gmn", ["pelan-pelan", "jalanin aja", "aman"], "contains"),
    ("gmana", ["jalanin aja", "pelan-pelan", "aman"], "contains"),
    ("gmna", ["jalanin aja", "pelan-pelan", "aman"], "contains"),
    ("kpn", ["nanti", "belum tau", "ntar"], "contains"),
    ("kapan nih", ["nanti", "ntar", "belum tau"], "contains"),
    ("kpn nih", ["nanti", "ntar", "belum tau"], "contains"),
    ("brp", ["kurang tau", "sekitar segitu", "ga ngitung"], "contains"),
    ("brapa", ["kurang tau", "sekitar segitu"], "contains"),

    # ===== RESPONS “IYA KENAPA” / “KENAPA KAK” (varian banyak) =====
    ("iya kenapa", ["kenapa kak", "kenapa emang", "hah", "apa"], "contains"),
    ("kenapa kak", ["kenapa", "apa", "hah"], "contains"),
    ("kenapaa kak", ["kenapa", "hah", "apaan"], "contains"),
    ("kenapa bro", ["kenapa", "apa", "hah"], "contains"),
    ("kenapa bang", ["kenapa", "apa", "hah"], "contains"),
    ("kenapa cuy", ["kenapa", "apa", "hah"], "contains"),
    ("kenapa si", ["kenapa", "hah"], "contains"),

    # ===== JAWABAN SINGKAT “OK” =====
    ("hmm", ["hm", "iya", "oh", "oke"], "contains"),
    ("hm", ["hm", "iya", "oh"], "exact"),
    ("oh", ["oh", "iya", "sip"], "exact"),
    ("ohh", ["oh", "iya", "sip"], "contains"),
    ("ooh", ["oh", "iya", "sip"], "contains"),
    ("oke deh", ["oke", "siap", "gas"], "contains"),
    ("yaudah", ["yaudah", "oke", "sip"], "contains"),
    ("ya udah", ["yaudah", "oke", "sip"], "contains"),

    # ===== REAKSI / EMOTE TEXT =====
    (":)", ["wkwk", "asik", "mantap"], "contains"),
    (":(", ["waduh", "sabar", "yah"], "contains"),
    ("😭", ["waduh", "sabar", "yah"], "contains"),
    ("🤣", ["wkwk", "ngakak", "kwkw"], "contains"),
    ("😂", ["wkwk", "ngakak", "kwkw"], "contains"),
    ("😳", ["eh", "waduh", "hah"], "contains"),

    # ===== KATA-KATA GC RANDOM =====
    ("anjay", ["gas", "mantap", "wkwk"], "contains"),
    ("mantul", ["mantap", "gas", "sip"], "contains"),
    ("goks", ["gokil", "mantap", "gas"], "contains"),
    ("gg", ["mantap", "gas", "gg"], "contains"),
    ("ggez", ["wkwk", "gg", "gas"], "contains"),
    ("nt", ["nt", "wkwk", "mantap"], "contains"),
    ("nice", ["mantap", "oke", "sip"], "contains"),
    ("cringe", ["waduh", "wkwk", "aneh"], "contains"),
    ("respect", ["mantap", "sip", "gas"], "contains"),
    ("savage", ["anjir", "parah", "wkwk"], "contains"),
    ("cie", ["ciee", "wkwk", "asek"], "contains"),
    ("ciee", ["ciee", "wkwk", "asek"], "contains"),
    ("asek", ["asek", "wkwk", "mantap"], "contains"),

    # ===== MABAR / GAME (biar rame) =====
    ("ml", ["gas mabar", "rank apa", "ayok"], "contains"),
    ("mobile legend", ["gas mabar", "rank apa", "ayok"], "contains"),
    ("ff", ["gas mabar", "room mana", "ayok"], "contains"),
    ("free fire", ["gas mabar", "room mana", "ayok"], "contains"),
    ("valo", ["gas valo", "party mana", "ayok"], "contains"),
    ("valorant", ["gas valo", "party mana", "ayok"], "contains"),
    ("pubg", ["gas pubg", "ayok", "kuy"], "contains"),
    ("rank", ["rank berapa", "gas", "ayok"], "contains"),
    ("push rank", ["gas push", "rank apa", "kuy"], "contains"),
    ("room", ["mana room", "kirim room", "gas"], "contains"),
    ("party", ["gas party", "mana party", "kuy"], "contains"),

    # ===== JUALAN / TRANSAKSI (umum banget di GC) =====
    ("ready", ["ready kak", "aman", "gas"], "contains"),
    ("stok", ["stok ada", "ready", "gas"], "contains"),
    ("stock", ["stok ada", "ready", "gas"], "contains"),
    ("harga", ["dm aja", "cek pm", "tanya pm"], "contains"),
    ("price", ["dm aja", "cek pm", "tanya pm"], "contains"),
    ("dm", ["cek pm", "siap", "gas"], "contains"),
    ("pm", ["cek pm", "siap", "gas"], "contains"),
    ("cod", ["bisa cod", "aman", "gas"], "contains"),
    ("transfer", ["aman", "gas", "siap"], "contains"),
    ("tf", ["aman", "gas", "siap"], "contains"),
    ("rekber", ["aman", "gas", "siap"], "contains"),

    # ===== BUCIN RINGAN (aman) =====
    ("kangen", ["cie", "wkwk", "asek"], "contains"),
    ("rindu", ["cie", "wkwk", "asek"], "contains"),
    ("sayang", ["ciee", "asek", "wkwk"], "contains"),
    ("bucin", ["ciee", "wkwk", "asek"], "contains"),
    ("ayang", ["ciee", "wkwk", "asek"], "contains"),
    ("beb", ["ciee", "wkwk", "asek"], "contains"),

    # ===== KEGIATAN HARIAN (lebih banyak) =====
    ("lagi apa", ["biasa", "ngopi", "rebahan"], "contains"),
    ("lg apa", ["biasa", "rebahan", "ngopi"], "contains"),
    ("ngapain", ["biasa kak", "rebahan", "ngopi"], "contains"),
    ("ngopi", ["mantap", "gas", "asik"], "contains"),
    ("rebahan", ["mantap", "asik", "wkwk"], "contains"),
    ("scroll", ["wkwk", "asik", "mantap"], "contains"),
    ("mager", ["mood dulu", "rebahan", "santai"], "contains"),
    ("malas", ["mood dulu", "rebahan", "santai"], "contains"),
    ("males", ["mood dulu", "rebahan", "santai"], "contains"),

    # ===== PENUTUP TAMBAHAN =====
    ("gn", ["gas dulu", "hati-hati", "aman"], "exact"),
    ("goodnight", ["met tidur", "gas dulu", "hati-hati"], "contains"),
    ("met tidur", ["met tidur", "hati-hati", "aman"], "contains"),
    ("met malem", ["met malem", "gas dulu", "aman"], "contains"),
    ("selamat malam", ["met malem", "hati-hati", "aman"], "contains"),
    ("selamat pagi", ["pagi kak", "gas", "mantap"], "contains"),
    ("selamat siang", ["siang kak", "gas", "oke"], "contains"),
    ("selamat sore", ["sore kak", "gas", "oke"], "contains"),
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

def pick_response(resp: Union[str, List[str]]) -> str:
    if isinstance(resp, (list, tuple)):
        return random.choice(resp) if resp else ""
    return str(resp or "")

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
# COMMANDS (OUTGOING)
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
    await m.reply_text("ChatRep OFF.")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]status(\s|$)"))
async def cmd_status(_, m):
    status = "ON" if await is_enabled(m.chat.id) else "OFF"
    dlog(f"[CMD] status -> {status}")
    await m.reply_text(f"Status ChatRep grup ini: {status}")

@app.on_message(filters.group & filters.outgoing & filters.regex(r"^[./]menu(\s|$)"))
async def cmd_menu(_, m):
    status = "ON" if await is_enabled(m.chat.id) else "OFF"
    # biar ga kepanjangan, tampilkan 60 rules pertama
    show = CHATREP_RULES[:60]
    rules = "\n".join(
        [f"• [{r[2]}] {r[0]} -> {(' | '.join(r[1]) if isinstance(r[1], (list, tuple)) else r[1])}" for r in show]
    ) or "- (kosong)"
    if len(CHATREP_RULES) > 60:
        rules += f"\n\n... dan {len(CHATREP_RULES) - 60} rules lainnya"
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
        out = pick_response(response)
        if not out.strip():
            return

        dlog(f"[MATCH] chat={m.chat.id} trig={trig_key} -> send")
        await safe_send(client, m.chat.id, out, reply_to=reply_to)
        return

# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("Running ChatRep userbot (MongoDB persistence)...")
    print("Test: .ping di grup harus dibales pong")
    app.run()
