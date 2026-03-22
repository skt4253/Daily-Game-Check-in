import os, time, hmac, hashlib, json, requests
from datetime import datetime, timezone, timedelta

HOYO_COOKIE  = os.environ["HOYO_COOKIE"]
SK_CRED      = os.environ["SK_CRED"]
SK_GAME_ROLE = os.environ["SK_GAME_ROLE"]
SK_TOKEN     = os.environ.get("SK_TOKEN", "")
TG_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT      = os.environ["TELEGRAM_CHAT_ID"]

HOYO_GAMES = [
    ("원신",          "https://sg-hk4e-api.hoyolab.com/event/sol/sign",           "e202102251931481", "https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481", {}),
    ("붕괴 스타레일",  "https://sg-public-api.hoyolab.com/event/luna/os/sign",     "e202303301540311", "https://act.hoyolab.com/bbs/event/signin/hkrpg/e202303301540311.html",             {}),
    ("젠레스 존 제로", "https://sg-public-api.hoyolab.com/event/luna/zzz/os/sign", "e202406031448091", "https://act.hoyolab.com/bbs/event/signin/zzz/e202406031448091.html",               {"x-rpc-signgame": "zzz"}),
]

SK_BASE_HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://game.skport.com/",
    "Origin": "https://game.skport.com",
    "platform": "3",
    "vName": "1.0.0",
}

def make_hoyo_headers(referer, extra={}):
    return {
        "Cookie": HOYO_COOKIE,
        "Content-Type": "application/json",
        "x-rpc-app_version": "2.34.1",
        "x-rpc-client_type": "5",
        "x-rpc-language": "ko-kr",
        "Referer": referer,
        "Origin": "https://act.hoyolab.com",
        **extra,
    }

def hoyo_checkin(name, url, act_id, referer, extra):
    r = requests.post(url, headers=make_hoyo_headers(referer, extra),
                      json={"act_id": act_id, "lang": "ko-kr"})
    code = r.json().get("retcode", -1)
    if code in (0, -5003):
        return f"✅ {name}: 출석 완료"
    else:
        return f"❌ {name}: 실패 (retcode={code})"

def sk_generate_sign(path, body, token):
    ts = str(int(time.time()))
    header_obj = {"platform": "3", "timestamp": ts, "dId": "", "vName": "1.0.0"}
    string_to_sign = path + body + ts + json.dumps(header_obj, separators=(',', ':'))
    hmac_hex = hmac.new(token.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    sign = hashlib.md5(hmac_hex.encode()).hexdigest()
    return sign, ts

def sk_refresh_token():
    r = requests.get("https://zonai.skport.com/web/v1/auth/refresh",
                     headers={**SK_BASE_HEADERS, "cred": SK_CRED})
    try:
        data = r.json()
        if data.get("code") == 0:
            return data["data"]["token"]
    except Exception:
        pass
    return None

def sk_checkin():
    token = SK_TOKEN or sk_refresh_token()
    if not token:
        return "❌ 엔드필드: 토큰 갱신 실패"

    path = "/web/v1/game/endfield/attendance"

    def attempt(tok):
        sign, ts = sk_generate_sign(path, "", tok)
        headers = {
            **SK_BASE_HEADERS,
            "cred": SK_CRED,
            "sk-game-role": SK_GAME_ROLE,
            "timestamp": ts,
            "sign": sign,
        }
        return requests.post(f"https://zonai.skport.com{path}", headers=headers)

    r = attempt(token)
    try:
        code = r.json().get("code", -1)
        if code in (0, 10001):
            return "✅ 엔드필드: 출석 완료"
        elif code == 10000:
            new_token = sk_refresh_token()
            if new_token:
                r2 = attempt(new_token)
                code2 = r2.json().get("code", -1)
                if code2 in (0, 10001):
                    return "✅ 엔드필드: 출석 완료"
                return f"❌ 엔드필드: 실패 ({r2.text[:80]})"
            return "❌ 엔드필드: 토큰 갱신 실패"
        else:
            return f"❌ 엔드필드: 실패 ({r.text[:80]})"
    except Exception:
        return f"❌ 엔드필드: 응답 파싱 실패 ({r.text[:80]})"

def send_telegram(msg):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": TG_CHAT, "text": msg})

if __name__ == "__main__":
    results = []
    for name, url, act_id, referer, extra in HOYO_GAMES:
        results.append(hoyo_checkin(name, url, act_id, referer, extra))
        time.sleep(1)
    results.append(sk_checkin())

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    msg = f"🎮 일일 출석체크 ({now})\n\n" + "\n".join(results)
    send_telegram(msg)
    print(msg)
