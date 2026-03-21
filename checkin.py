import os, time, hmac, hashlib, json, requests
from datetime import datetime

LTOKEN    = os.environ["HOYO_LTOKEN_V2"]
LTUID     = os.environ["HOYO_LTUID_V2"]
SK_CRED   = os.environ["SK_CRED"]
SK_TOKEN  = os.environ["SK_TOKEN"]
SK_ID     = os.environ["SK_GAME_ID"]
TG_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT   = os.environ["TELEGRAM_CHAT_ID"]
SK_SERVER = "2"

HOYO_COOKIE = f"ltoken_v2={LTOKEN}; ltuid_v2={LTUID};"
HOYO_HEADERS = {
    "Cookie": HOYO_COOKIE,
    "Content-Type": "application/json",
    "x-rpc-app_version": "2.34.1",
    "x-rpc-client_type": "5",
    "x-rpc-language": "ko-kr",
    "Referer": "https://act.hoyolab.com",
    "Origin": "https://act.hoyolab.com",
}
HOYO_GAMES = [
    ("원신",          "https://sg-hk4e-api.hoyolab.com/event/sol/sign",            "e202102251931551"),
    ("붕괴 스타레일",  "https://sg-public-api.hoyolab.com/event/luna/os/sign",      "e202303301540311"),
    ("젠레스 존 제로", "https://sg-act-nap-api.hoyolab.com/event/luna/zzz/os/sign", "e202406031448091"),
]

def hoyo_checkin(name, url, act_id):
    r = requests.post(url, headers=HOYO_HEADERS,
                      json={"act_id": act_id, "lang": "ko-kr"})
    code = r.json().get("retcode", -1)
    if code == 0:
        return f"✅ {name}: 출석 완료"
    elif code == -5003:
        return f"☑️ {name}: 이미 출석함"
    else:
        return f"❌ {name}: 실패 (retcode={code})"

def sk_sign(path, body, token):
    ts = str(int(time.time() * 1000))
    header_json = json.dumps({"platform":"3","timestamp":ts,"dId":"","vName":"1.0.0"}, separators=(',',':'))
    msg = path + body + ts + header_json
    h = hmac.new(token.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return hashlib.md5(h.encode()).hexdigest(), ts

def sk_checkin():
    path = "/web/v1/user/game_role/sign"
    body = json.dumps({"id": SK_ID, "server": SK_SERVER}, separators=(',',':'))
    sign, ts = sk_sign(path, body, SK_TOKEN)
    headers = {
        "cred": SK_CRED,
        "Content-Type": "application/json",
        "sign": sign,
        "timestamp": ts,
        "platform": "3",
        "vName": "1.0.0",
        "dId": "",
    }
    r = requests.post(f"https://zonai.skport.com{path}", headers=headers, data=body)
    print(f"SKPORT 응답: {r.status_code} / {r.text}")
    try:
        code = r.json().get("code", -1)
        if code == 0:
            return "✅ 엔드필드: 출석 완료"
        elif code == 1:
            return "☑️ 엔드필드: 이미 출석함"
        else:
            return f"❌ 엔드필드: 실패 ({r.text[:80]})"
    except Exception:
        return f"❌ 엔드필드: 응답 파싱 실패 ({r.text[:80]})"

def send_telegram(msg):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": TG_CHAT, "text": msg})

if __name__ == "__main__":
    results = []
    for name, url, act_id in HOYO_GAMES:
        results.append(hoyo_checkin(name, url, act_id))
        time.sleep(1)
    results.append(sk_checkin())

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    msg = f"🎮 일일 출석체크 ({now})\n\n" + "\n".join(results)
    send_telegram(msg)
    print(msg)
