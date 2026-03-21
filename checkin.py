import os, time, hashlib, json, requests
from datetime import datetime, timezone, timedelta

LTOKEN       = os.environ["HOYO_LTOKEN_V2"]
LTUID        = os.environ["HOYO_LTUID_V2"]
SK_CRED      = os.environ["SK_CRED"]
SK_GAME_ROLE = os.environ["SK_GAME_ROLE"]
TG_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT      = os.environ["TELEGRAM_CHAT_ID"]

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

def sk_checkin():
    ts = str(int(time.time()))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Referer": "https://game.skport.com/",
        "Origin": "https://game.skport.com",
        "cred": SK_CRED,
        "sk-game-role": SK_GAME_ROLE,
        "platform": "3",
        "vName": "1.0.0",
        "timestamp": ts,
        "sign": hashlib.md5(ts.encode()).hexdigest(),
    }
    r = requests.post("https://zonai.skport.com/web/v1/game/endfield/attendance", headers=headers)
    print(f"SKPORT 응답: {r.status_code} / {r.text}")
    try:
        code = r.json().get("code", -1)
        if code == 0:
            return "✅ 엔드필드: 출석 완료"
        elif code == 10001:
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

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    msg = f"🎮 일일 출석체크 ({now})\n\n" + "\n".join(results)
    send_telegram(msg)
    print(msg)
