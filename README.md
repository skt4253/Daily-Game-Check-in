# 🎮 게임 자동 출석체크

HoYoLAB(원신, 붕괴 스타레일, 젠레스 존 제로)와 SKPORT(명일방주 엔드필드) 출석체크를 GitHub Actions로 매일 자동 실행하고 텔레그램으로 결과를 알려주는 스크립트입니다.

### "컴퓨터와 출석체크 앱조차 켜기 귀찮은 사람들을 위한 스크립트"

## ✅ 지원 게임

| 게임 | 플랫폼 |
|------|--------|
| 원신 (Genshin Impact) | HoYoLAB |
| 붕괴: 스타레일 (Honkai: Star Rail) | HoYoLAB |
| 젠레스 존 제로 (Zenless Zone Zero) | HoYoLAB |
| 명일방주: 엔드필드 (Arknights: Endfield) | SKPORT |

## 📋 사전 준비

- GitHub 계정
- 텔레그램 계정
- 위 게임들의 계정 (아시아 서버 기준)

---

## 🚀 설치 방법

### Step 1. Repository 생성

1. GitHub에서 **New repository** 클릭
2. Repository name 입력 (예: `auto-checkin`)
3. **Private** 선택
4. **Add a README file** 체크 후 생성

### Step 2. 파일 업로드

repo 메인 페이지 → **Add file** → **Create new file**

**`checkin.py`** 생성 후 아래 코드 붙여넣기:

```python
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
    if code == 0:
        return f"✅ {name}: 출석 완료"
    elif code == -5003:
        return f"☑️ {name}: 이미 출석함"
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
        if code == 0:
            return "✅ 엔드필드: 출석 완료"
        elif code == 10001:
            return "☑️ 엔드필드: 이미 출석함"
        elif code == 10000:
            new_token = sk_refresh_token()
            if new_token:
                r2 = attempt(new_token)
                code2 = r2.json().get("code", -1)
                if code2 == 0:
                    return "✅ 엔드필드: 출석 완료"
                elif code2 == 10001:
                    return "☑️ 엔드필드: 이미 출석함"
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
```

파일명 입력란에 `.github/workflows/checkin.yml` 입력 후 아래 코드 붙여넣기:

```yaml
name: Daily Check-in

on:
  schedule:
    - cron: '0 0 * * *'  # 매일 UTC 00:00 = KST 09:00
  workflow_dispatch:

jobs:
  checkin:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install requests
      - run: python checkin.py
        env:
          HOYO_COOKIE: ${{ secrets.HOYO_COOKIE }}
          SK_CRED: ${{ secrets.SK_CRED }}
          SK_GAME_ROLE: ${{ secrets.SK_GAME_ROLE }}
          SK_TOKEN: ${{ secrets.SK_TOKEN }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

---

### Step 3. 쿠키/토큰 추출

#### HoYoLAB 쿠키

1. **시크릿 창**에서 [hoyolab.com](https://www.hoyolab.com) 로그인
2. F12 → **Console** 탭 → `document.cookie` 입력 후 엔터
3. 출력된 문자열 전체 복사 → `HOYO_COOKIE`로 저장

#### SKPORT 값 추출

1. [game.skport.com/endfield/sign-in](https://game.skport.com/endfield/sign-in) 로그인
2. F12 → **Console** 탭에 아래 코드 붙여넣기 후 엔터:

```javascript
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}
let cred = getCookie('SK_OAUTH_CRED_KEY');
console.log('SK_CRED:', cred);
```

3. 출력된 값 → `SK_CRED`로 저장
4. F12 → **Network** 탭 → 페이지 새로고침 → `attendance` 요청 클릭 → Request Headers에서 `sk-game-role` 값 복사 → `SK_GAME_ROLE`로 저장 (형식: `3_숫자_2`)

#### 텔레그램 봇

1. 텔레그램에서 **@BotFather** → `/newbot` → 봇 생성
2. 발급된 토큰 → `TELEGRAM_BOT_TOKEN`으로 저장
3. 봇에게 메시지 전송 후 `https://api.telegram.org/bot{토큰}/getUpdates` 접속
4. `"chat":{"id":` 뒤 숫자 → `TELEGRAM_CHAT_ID`로 저장

---

### Step 4. Secrets 등록

repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 값 |
|------------|-----|
| `HOYO_COOKIE` | HoYoLAB 쿠키 전체 문자열 |
| `SK_CRED` | SK_OAUTH_CRED_KEY 값 |
| `SK_GAME_ROLE` | sk-game-role 값 (예: `3_123456_2`) |
| `SK_TOKEN` | SK_TOKEN_CACHE_KEY 값 (선택사항) |
| `TELEGRAM_BOT_TOKEN` | BotFather 발급 토큰 |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅 ID |

---

### Step 5. 테스트 실행

repo → **Actions** → **Daily Check-in** → **Run workflow** → **Run workflow**

---

## ⏰ 실행 시간

매일 **오전 9시 (KST)** 자동 실행됩니다.

## 📱 알림 예시

```
🎮 일일 출석체크 (2026-03-22 09:00 KST)

✅ 원신: 출석 완료
✅ 붕괴 스타레일: 출석 완료
✅ 젠레스 존 제로: 출석 완료
✅ 엔드필드: 출석 완료
```

## ⚠️ 주의사항

- 아시아 서버 기준으로 작성되었습니다
- SKPORT `SK_CRED` 값은 로그아웃 시 만료되므로 재로그인 후 갱신 필요
- HoYoLAB 쿠키도 주기적으로 만료될 수 있으므로 출석 실패 알림 시 갱신 필요
- **Secrets에 저장된 값은 절대 외부에 공유하지 마세요**
