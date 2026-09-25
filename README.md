# 🎮 게임 자동 출석체크

HoYoLAB(원신, 붕괴 스타레일, 젠레스 존 제로)와 SKPORT(명일방주 엔드필드) 출석체크를 GitHub Actions로 매일 자동 실행하고 디스코드로 결과를 알려주는 스크립트입니다.

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
- 디스코드 계정 (단순 알림용이라 없어도 무방)
- 위 게임들의 계정 (하는 게임 계정만)

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
```

파일명 입력란에 `.github/workflows/checkin.yml` 입력 후 아래 코드 붙여넣기:

```yaml
name: Daily Game Check-in

on:
  schedule:
    - cron: '15 19 * * *'  # 매일 UTC 19:15 = KST 04:15
  workflow_dispatch:

jobs:
  checkin:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'
      - run: pip install requests
      - run: python checkin.py
        env:
          HOYO_COOKIE: ${{ secrets.HOYO_COOKIE }}
          SK_CRED: ${{ secrets.SK_CRED }}
          SK_GAME_ROLE: ${{ secrets.SK_GAME_ROLE }}
          SK_TOKEN: ${{ secrets.SK_TOKEN }}
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
```

---

### Step 3. 쿠키/토큰 추출

#### HoYoLAB 쿠키

> ⚠️ Console에서 `document.cookie`를 쳐도 인증에 꼭 필요한 `ltoken_v2`는 **나오지 않습니다**. HttpOnly 속성이라 JavaScript로 읽을 수 없기 때문이며, 이 값이 빠지면 `retcode=-100`으로 실패합니다.

1. **시크릿 창**에서 [hoyolab.com](https://www.hoyolab.com) 로그인
2. F12 → **Application** 탭
3. 좌측 **Storage → Cookies → `https://www.hoyolab.com`** 선택
4. 목록에서 아래 두 개를 찾아 Value를 직접 복사

| 쿠키 이름 | 설명 |
|-----------|------|
| `ltoken_v2` | 인증 토큰 (보통 `v2_`로 시작) |
| `ltuid_v2` | 계정 UID (숫자) |

5. 아래 형식으로 조합해서 `HOYO_COOKIE`로 저장

```
ltoken_v2=v2_여기에값; ltuid_v2=여기에숫자;
```

> 💡 `ltuid_v2`가 안 보이면 `ltmid_v2`(`xxxxxxxx_mhy` 형식)를 대신 사용해도 됩니다.
> 💡 더 확실한 방법: F12 → **Network** 탭 → 아무 요청이나 클릭 → Request Headers의 `Cookie:` 줄을 통째로 복사 (HttpOnly 값 포함)

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

#### 디스코드 웹훅

1. 알림 받을 디스코드 채널 → **⚙️ 채널 편집** → **연동** → **웹후크 만들기**
2. 생성된 웹훅 클릭 → 이름 지정(선택) → **웹후크 URL 복사** → **변경사항 저장**
3. 복사한 URL → `DISCORD_WEBHOOK_URL`로 저장

> ⚠️ 웹훅 URL만 있으면 누구나 해당 채널에 메시지를 보낼 수 있으니 Secret에만 저장하세요. 유출 시 웹훅을 삭제하고 새로 만들면 됩니다.

---

### Step 4. Secrets 등록

repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 값 |
|------------|-----|
| `HOYO_COOKIE` | `ltoken_v2=...; ltuid_v2=...;` 형식 문자열 |
| `SK_CRED` | SK_OAUTH_CRED_KEY 값 |
| `SK_GAME_ROLE` | sk-game-role 값 (예: `3_123456_2`) |
| `SK_TOKEN` | SK_TOKEN_CACHE_KEY 값 (선택사항) |
| `DISCORD_WEBHOOK_URL` | 디스코드 웹훅 URL |

> ⚠️ 값을 붙여넣을 때 앞뒤 따옴표·공백·줄바꿈이 섞이면 인증에 실패합니다. 한 줄로만 입력하세요.

---

### Step 5. 테스트 실행

repo → **Actions** → **Daily Game Check-in** → **Run workflow** → **Run workflow**

---

## ⏰ 실행 시간

매일 **새벽 4시 15분 (KST)** 자동 실행됩니다.

HoYoLAB 출석 기준 시각은 KST 01:00에 초기화되므로 그 이후 시간대라면 문제없습니다. 시간을 바꾸려면 `checkin.yml`의 cron 값을 UTC 기준으로 수정하세요. (GitHub Actions 스케줄은 서버 부하에 따라 수 분~수십 분 지연될 수 있습니다.)

## 📱 알림 예시

```
🎮 일일 출석체크 (2026-03-22 04:15 KST)

✅ 원신: 출석 완료
✅ 붕괴 스타레일: 출석 완료
✅ 젠레스 존 제로: 출석 완료
✅ 엔드필드: 출석 완료
```

## 🔧 문제 해결

| 증상 | 원인 및 조치 |
|------|--------------|
| `retcode=-100` | `ltoken_v2`가 누락됐거나 만료됨. Step 3 방식으로 재추출 |
| 비밀번호 변경 후 전부 실패 | 기존 토큰이 모두 무효화됨. 재로그인 후 쿠키 재발급 |
| 엔드필드 `토큰 갱신 실패` | `SK_CRED` 만료. 재로그인 후 갱신 |
| 알림이 아예 안 옴 | Actions 로그에서 secret 누락 여부 확인 |

## ⚠️ 주의사항

- 아시아 서버 기준으로 작성되었습니다
- **HoYoLAB 비밀번호를 변경하거나 로그아웃하면 `ltoken_v2`가 즉시 무효화됩니다.** 이 경우 쿠키를 새로 발급받아야 합니다
- SKPORT `SK_CRED` 값도 로그아웃 시 만료되므로 재로그인 후 갱신 필요
- HoYoLAB 쿠키는 주기적으로 만료될 수 있으므로 출석 실패 알림 시 갱신 필요
- **Secrets에 저장된 값은 절대 외부에 공유하지 마세요**
