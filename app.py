import os
import time
import logging
import requests
from flask import Flask, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

TOKEN = (os.environ.get("TOKEN") or os.environ.get("PAGE_ACCESS_TOKEN") or os.environ.get("ACCESS_TOKEN") or os.environ.get("PAGE_TOKEN"))
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "awlad_musa_2024")
GRAPH_URL = "https://graph.facebook.com/v19.0/me/messages"
SESSION_TTL = 60 * 60

if not TOKEN:
    log.warning("TOKEN غير موجود في متغيرات البيئة!")

PHONE = "+249968342013"
ACCOUNT = "6859973 موسى يعقوب"
LOCATION = "📍 شجرة اولاد حامد علي"

CARRIERS = {"1": "زين 💛", "2": "سوداني 💙", "3": "MTN 💛"}
PRICES = {
    "1": {"1": "1,500", "2": "5,500", "3": "17,000"},
    "2": {"1": "2,500", "2": "9,000", "3": "30,000"},
}
PERIODS = {"1": "يوم", "2": "اسبوع", "3": "شهر"}

PROMPTS = {
    "main": ("مرحبا بيك في خدمات اولاد موسى 💳⚡🏦\n1️⃣ بيع رصيد 💳\n2️⃣ شراء كهرباء ⚡\n3️⃣ فتح حساب بنكك 🏦\n4️⃣ خدمات جاهزه 📶\n5️⃣ التكلم مع التاجر 👨‍💼"),
    "raseed": ("💳 بيع رصيد خصم 200 على كل 1000 ⚠️\n1️⃣ زاين 💛\n2️⃣ سوداني 💙\n3️⃣ MTN 💛"),
    "raseed_pay": "1️⃣ كاش 💵\n2️⃣ بنكك 🏦",
    "bankak": "🏦 فتح حساب بنكك ✅\n📍 العزيز غرب السكر\n1️⃣ قريب 🚶‍♂️\n2️⃣ بعيد ✈️",
    "bankak_doc": "اختار نوع المستند 📄\n1️⃣ جواز سفر\n2️⃣ رقم وطني",
    "services": "📶 خدمات جاهزه\n1️⃣ زاين 💛\n2️⃣ سوداني 💙\n3️⃣ MTN 💛",
    "srv_period": "اختار الخدمة\n1️⃣ يوم\n2️⃣ اسبوع\n3️⃣ شهر",
}

sessions = {}
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def normalize(txt):
    txt = txt.translate(AR_DIGITS)
    txt = txt.replace("\ufe0f", "").replace("\u20e3", "")
    return txt.strip()

def cleanup_sessions():
    now = time.time()
    for k in [k for k, v in sessions.items() if now - v["ts"] > SESSION_TTL]:
        del sessions[k]

def get_session(sender):
    if len(sessions) > 500:
        cleanup_sessions()
    s = sessions.get(sender)
    if not s or time.time() - s["ts"] > SESSION_TTL:
        s = {"state": "start", "ts": time.time()}
        sessions[sender] = s
    s["ts"] = time.time()
    return s

def end_session(sender):
    sessions.pop(sender, None)

def send(recipient, text):
    if not TOKEN:
        log.error("لا يمكن الإرسال: TOKEN غير موجود")
        return
    try:
        r = requests.post(
            GRAPH_URL,
            params={"access_token": TOKEN},
            json={"recipient": {"id": recipient}, "message": {"text": text}},
            timeout=15,
        )
        if r.status_code != 200:
            log.error("Send failed: %s", r.text)
    except Exception:
        log.exception("Send error")

def invalid(sender, state):
    send(sender, "⚠️ اختيار غلط، اكتب رقم من القائمة (أو 0 للقائمة الرئيسية)\n\n" + PROMPTS[state])

def handle(sender, txt):
    s = get_session(sender)
    state = s["state"]
    if state == "start" or "السلام" in txt or txt in ("0", "القائمة", "menu"):
        s["state"] = "main"
        send(sender, "وعليكم السلام ورحمة الله\n" + PROMPTS["main"])
        return
    if state == "main":
        if txt == "1":
            s["state"] = "raseed"
            send(sender, PROMPTS["raseed"])
        elif txt == "2":
            send(sender, f"⚡ كهرباء ✅\nخصم 300 على كل 1000\nالتاجر {PHONE}\n🔢 رسل رقم العداد والمبلغ")
            end_session(sender)
        elif txt == "3":
            s["state"] = "bankak"
            send(sender, PROMPTS["bankak"])
        elif txt == "4":
            s["state"] = "services"
            send(sender, PROMPTS["services"])
        elif txt == "5":
            send(sender, f"👨‍💼 التاجر\n📱 واتساب {PHONE} 💚")
            end_session(sender)
        else:
            invalid(sender, "main")
        return
    if state == "raseed":
        if txt in CARRIERS:
            s["carrier"] = CARRIERS[txt]
            s["state"] = "raseed_pay"
            send(sender, PROMPTS["raseed_pay"])
        else:
            invalid(sender, "raseed")
        return
    if state == "raseed_pay":
        if txt in ("1", "2"):
            pay = "كاش 💵" if txt == "1" else "بنكك 🏦"
            send(sender, f"✅ رصيد {s['carrier']} - الدفع: {pay}\nرسل رقم الشريحة والاشعار\n💳 حساب: {ACCOUNT}\n{LOCATION}")
            end_session(sender)
        else:
            invalid(sender, "raseed_pay")
        return
    if state == "bankak":
        if txt in ("1", "2"):
            s["near"] = (txt == "1")
            s["state"] = "bankak_doc"
            send(sender, PROMPTS["bankak_doc"])
        else:
            invalid(sender, "bankak")
        return
    if state == "bankak_doc":
        if txt in ("1", "2"):
            doc = "جواز سفر" if txt == "1" else "رقم وطني"
            if s["near"]:
                send(sender, f"{LOCATION}\nتعال المحل ومعاك المستند ({doc})")
            else:
                send(sender, f"📱 واتساب {PHONE} 💚\nابعت صورة {doc}\n🌐 لازم تكون منشط نت")
            end_session(sender)
        else:
            invalid(sender, "bankak_doc")
        return
    if state == "services":
        if txt in ("1", "2"):
            s["carrier_key"] = txt
            s["carrier"] = CARRIERS[txt]
            s["state"] = "srv_period"
            send(sender, PROMPTS["srv_period"])
        elif txt == "3":
            send(sender, "💛 MTN\n⚠️ لا تتوفر خدمة جاهزه\n✅ يتوفر رصيد فقط")
            end_session(sender)
        else:
            invalid(sender, "services")
        return
    if state == "srv_period":
        if txt in PERIODS:
            price = PRICES[s["carrier_key"]][txt]
            send(sender, f"{s['carrier']} - خدمة {PERIODS[txt]}: {price}\n💳 حول {ACCOUNT}")
            end_session(sender)
        else:
            invalid(sender, "srv_period")
        return
    end_session(sender)
    handle(sender, txt)

@app.route("/")
def home():
    return "شغال"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if (request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN):
            return request.args.get("hub.challenge", ""), 200
        return "غلط", 403
    data = request.get_json(silent=True)
    if not data or data.get("object") != "page":
        return "ok", 200
    try:
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                msg = event.get("message")
                if not msg or msg.get("is_echo"):
                    continue
                text = msg.get("text")
                if not text:
                    continue
                handle(event["sender"]["id"], normalize(text))
    except Exception:
        log.exception("Webhook error")
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
