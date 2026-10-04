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

이 저장소의 아래 두 파일을 내 repo에 **같은 경로**로 복사합니다. (repo 메인 페이지 → **Add file** → **Create new file** → 경로 입력 후 내용 붙여넣기)

| 파일 | 설명 |
|------|------|
| `checkin.py` | 출석체크 및 디스코드 알림 스크립트 |
| `.github/workflows/checkin.yml` | 매일 자동 실행 스케줄 (GitHub Actions) |

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

매일 **새벽 1시 30분 (KST)** 자동 실행됩니다.

HoYoLAB 출석 기준 시각은 KST 01:00에 초기화되므로 그 이후 시간대라면 문제없습니다. 시간을 바꾸려면 `checkin.yml`의 cron 값을 UTC 기준으로 수정하세요. (GitHub Actions 스케줄은 서버 부하에 따라 수 분~수십 분 지연될 수 있습니다.)

## 📱 알림 예시

```
🎮 일일 출석체크 (2026-03-22 01:30 KST)

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
