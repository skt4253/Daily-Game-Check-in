import os, time, hmac, hashlib, json, requests
from datetime import datetime, timezone, timedelta

HOYO_COOKIE  = os.environ["HOYO_COOKIE"]
SK_CRED      = os.environ["SK_CRED"]
SK_GAME_ROLE = os.environ["SK_GAME_ROLE"]
SK_TOKEN     = os.environ.get("SK_TOKEN", "")
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

TIMEOUT = 20

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

def make_hoyo_headers(referer, extra=None):
    return {
        "Cookie": HOYO_COOKIE,
        "Content-Type": "application/json",
        "x-rpc-app_version": "2.34.1",
        "x-rpc-client_type": "5",
        "x-rpc-language": "ko-kr",
        "Referer": referer,
        "Origin": "https://act.hoyolab.com",
        **(extra or {}),
    }

def hoyo_checkin(name, url, act_id, referer, extra):
    try:
        r = requests.post(url, headers=make_hoyo_headers(referer, extra),
                          json={"act_id": act_id, "lang": "ko-kr"}, timeout=TIMEOUT)
        j = r.json()
    except Exception as e:
        return f"❌ {name}: 요청 실패 ({type(e).__name__})"

    code = j.get("retcode", -1)
    msg  = j.get("message", "")
    print(f"[DEBUG] {name}: retcode={code}, message={msg}")

    if code == 0:
        return f"✅ {name}: 출석 완료"
    elif code == -5003:
        return f"☑️ {name}: 이미 출석함"
    elif code == -100:
        return f"❌ {name}: 쿠키 만료/무효 (retcode=-100) → HOYO_COOKIE 갱신 필요"
    else:
        return f"❌ {name}: 실패 (retcode={code}, {msg})"

def sk_generate_sign(path, body, token):
    ts = str(int(time.time()))
    header_obj = {"platform": "3", "timestamp": ts, "dId": "", "vName": "1.0.0"}
    string_to_sign = path + body + ts + json.dumps(header_obj, separators=(',', ':'))
    hmac_hex = hmac.new(token.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    sign = hashlib.md5(hmac_hex.encode()).hexdigest()
    return sign, ts

def sk_refresh_token():
    try:
        r = requests.get("https://zonai.skport.com/web/v1/auth/refresh",
                         headers={**SK_BASE_HEADERS, "cred": SK_CRED}, timeout=TIMEOUT)
        data = r.json()
        if data.get("code") == 0:
            return data["data"]["token"]
        print(f"[DEBUG] SK refresh 실패: {r.text[:120]}")
    except Exception as e:
        print(f"[DEBUG] SK refresh 예외: {type(e).__name__}")
    return None

def sk_checkin():
    token = SK_TOKEN or sk_refresh_token()
    if not token:
        return "❌ 엔드필드: 토큰 갱신 실패 → SK_CRED 갱신 필요"

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
        resp = requests.post(f"https://zonai.skport.com{path}", headers=headers, timeout=TIMEOUT)
        try:
            code = resp.json().get("code", -1)
        except Exception:
            code = -1
        raw = resp.text[:80]
        print(f"[DEBUG] 엔드필드: code={code}, raw={raw}")
        return code, raw

    try:
        code, raw = attempt(token)
    except Exception as e:
        return f"❌ 엔드필드: 요청 실패 ({type(e).__name__})"

    if code == 0:
        return "✅ 엔드필드: 출석 완료"
    elif code == 10001:
        return "☑️ 엔드필드: 이미 출석함"
    elif code == 10000:
        new_token = sk_refresh_token()
        if not new_token:
            return "❌ 엔드필드: 토큰 갱신 실패 → SK_CRED 갱신 필요"
        try:
            code2, raw2 = attempt(new_token)
        except Exception as e:
            return f"❌ 엔드필드: 요청 실패 ({type(e).__name__})"
        if code2 == 0:
            return "✅ 엔드필드: 출석 완료"
        elif code2 == 10001:
            return "☑️ 엔드필드: 이미 출석함"
        return f"❌ 엔드필드: 실패 ({raw2})"
    else:
        return f"❌ 엔드필드: 실패 ({raw})"

def send_discord(msg):
    try:
        r = requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=TIMEOUT)
        if not r.ok:
            print(f"[WARN] 디스코드 전송 실패: HTTP {r.status_code}")
    except Exception as e:
        print(f"[WARN] 디스코드 전송 실패: {type(e).__name__}")

if __name__ == "__main__":
    results = []
    for name, url, act_id, referer, extra in HOYO_GAMES:
        results.append(hoyo_checkin(name, url, act_id, referer, extra))
        time.sleep(1)
    results.append(sk_checkin())

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    msg = f"🎮 일일 출석체크 ({now})\n\n" + "\n".join(results)
    send_discord(msg)
    print(msg)
