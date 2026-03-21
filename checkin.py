import os, time, hmac, hashlib, json, requests
from datetime import datetime, timezone, timedelta

HOYO_COOKIE  = os.environ["HOYO_COOKIE"]
SK_CRED      = os.environ["SK_CRED"]
SK_GAME_ROLE = os.environ["SK_GAME_ROLE"]
SK_TOKEN     = os.environ["SK_TOKEN"]
TG_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT      = os.environ["TELEGRAM_CHAT_ID"]

HOYO_GAMES = [
    ("원신",          "https://sg-hk4e-api.hoyolab.com/event/sol/sign",            "e202102251931481", "https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481"),
    ("붕괴 스타레일",  "https://sg-public-api.hoyolab.com/event/luna/os/sign",      "e202303301540311", "https://act.hoyolab.com/bbs/event/signin/hkrpg/e202303301540311.html"),
    ("젠레스 존 제로", "https://sg-act-nap-api.hoyolab.com/event/luna/zzz/os/sign", "e202406031448091", "https://act.hoyolab.com/bbs/event/signin/zzz/e202406031448091.html"),
]

def make_headers(referer):
    return {
        "Cookie": HOYO_COOKIE,
        "Content-Type": "application/json",
        "x-rpc-app_version": "2.34.1",
        "x-rpc-client_type": "5",
        "x-rpc-language": "ko-kr",
        "Referer": referer,
        "Origin": "https://act.hoyolab.com",
    }

def hoyo_checkin(name, url, act_id, referer):
    r = requests.post(url, headers=make_headers(referer),
                      json={"act_id": act_id, "lang": "ko-kr"})
    print(f"{name} 응답: {r.status_code} / {r.text[:150]}")
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
    path = "/web/v1/game/endfield/attendance"
    body = ""
    sign, ts = sk_sign(path, body, SK_TOKEN)
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
        "sign": sign,
    }
    r = requests.post(f"https://zonai.skport.com{path}", headers=headers)
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
    for name, url, act_id, referer in HOYO_GAMES:
        results.append(hoyo_checkin(name, url, act_id, referer))
        time.sleep(1)
    results.append(sk_checkin())

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    msg = f"🎮 일일 출석체크 ({now})\n\n" + "\n".join(results)
    send_telegram(msg)
    print(msg)
