# 경계면 정합성 매트릭스

V-AIS 봇의 전체 검증 항목. `discord-bot-qa` 스킬 2단계의 보충 레퍼런스. 자동 검사에서 결함이 나왔거나, 변경이 스키마·config·태스크·외부 연동을 건드렸을 때 해당 절만 읽는다.

## 목차

1. [설정 경계면](#1-설정-경계면)
2. [데이터 경계면](#2-데이터-경계면)
3. [커맨드 경계면](#3-커맨드-경계면)
4. [백그라운드 태스크 경계면](#4-백그라운드-태스크-경계면)
5. [외부 연동 경계면](#5-외부-연동-경계면)
6. [배포 경계면](#6-배포-경계면)
7. [증상별 진단 경로](#7-증상별-진단-경로)

---

## 1. 설정 경계면

**왼쪽**: `config_sample.json` / **오른쪽**: 코드의 모든 `config[...]` 접근

`config.json`은 비밀 파일이므로 읽지 않는다. 검증 기준은 항상 `config_sample.json`이다.

| 항목 | 확인 방법 | 실패 시 증상 |
|------|----------|-------------|
| 코드가 읽는 모든 키가 sample에 존재 | 자동 검사 | 신규 환경에서 해당 cog만 로딩 실패 |
| cog `__init__`에서 읽는 키 | 자동 검사가 `런타임` 등급으로 표시 | cog 전체가 조용히 사라짐 |
| `FEED_CHANNEL` 하위 키 | `bot.py`의 `get_channel` 호출과 대조 | 태스크가 `None.send`로 죽음 |
| `OWNERS` 배열 | `helpers/checks.py:31`가 `config.json`을 직접 읽음 | 소유자 커맨드 전면 차단 |

`helpers/checks.py`는 `bot.config`가 아니라 **파일을 매번 직접 연다.** 커맨드 호출마다 디스크 I/O가 발생하며, 봇 실행 중 `config.json`을 수정하면 재시작 없이 반영된다. 이 비대칭을 인지하고 검증한다.

**선택적 연동의 방어 패턴**: 키가 없어도 봇이 떠야 하는 기능이라면 cog `__init__`에서 방어한다.

```python
def __init__(self, bot):
    self.bot = bot
    self.api_key = bot.config.get("TOKENS", {}).get("GOOGLE", {}).get("KEY")

# 커맨드 안에서
if not self.api_key:
    embed.description = "이 기능은 아직 설정되지 않았어요!"
```

---

## 2. 데이터 경계면

### 2-1. 3자 대조 (스키마 ↔ 함수 ↔ 호출부)

이 봇에서 가장 자주 깨지고 가장 조용한 경계면.

```
database/schema.sql          helpers/db_manager.py         cogs/*.py
컬럼 순서 (DDL)      →       SELECT 절 + docstring   →     row[N]
```

검증 순서:

1. 스키마에서 테이블 컬럼 순서를 인덱스와 함께 적는다
2. 함수가 `SELECT *`인지 컬럼 명시인지 확인한다
   - `SELECT *` → 반환 인덱스 = 스키마 컬럼 순서
   - `SELECT a, b, c` → 반환 인덱스 = **SELECT 절 순서** (스키마와 무관)
3. 모든 호출부의 `row[N]`이 의도한 컬럼을 가리키는지 확인한다

현재 확인된 정상 매핑 (회귀 기준선). **테이블 인덱스와 함수 반환 인덱스는 다를 수 있다** — 함수가 컬럼을 명시하면 반환 인덱스는 SELECT 절을 따른다:

| 테이블 (스키마 순서) | 인덱스 |
|--------|--------|
| `blacklist` | 0:user_id 1:created_at |
| `github` | 0:channel_name 1:channel_id 2:message_author 3:message_author_id 4:github_username 5:repository_name 6:description 7:created_at |
| `paper` | 0:channel_name 1:channel_id 2:message_author 3:message_author_id 4:source 5:title 6:authors 7:url 8:conference 9:year 10:created_at |
| `youtube_video` | 0:channel_name 1:video_id 2:video_link 3:published 4:send 5:created_at |

| 함수 | SELECT 방식 | 반환 인덱스 | 호출부 |
|------|-----------|-----------|--------|
| `get_paper` | `SELECT *` | 스키마 순서 그대로 | `cogs/search.py:51` — `row[5]`=title, `row[7]`=url ✓ |
| `get_github` | `SELECT *` | 스키마 순서 그대로 | `cogs/search.py:55` — `row[4]`/`row[5]`/`row[6]` ✓ |
| `get_youtube_video` | **컬럼 명시** `channel_name, video_id, video_link` | **0:channel_name 1:video_id 2:video_link** (스키마 순서 아님) | `bot.py:215` — `row[2]`=video_link ✓, `bot.py:216` — `update_youtube_video(row[0], row[1], row[2])` ✓ |
| `get_blacklisted_users` | **컬럼 명시** `user_id, strftime('%s', created_at)` | 0:user_id 1:유닉스 타임스탬프 | `cogs/owner.py` — `bluser[1]`을 `<t:...>`로 렌더링 ✓ |

`get_youtube_video`가 이 함정의 교과서적 사례다. 테이블 인덱스로는 `video_link`가 2번이 **맞지만** 이는 우연이며, `send`(4번)나 `created_at`(5번)을 읽으려고 `row[4]`를 쓰면 `IndexError`가 난다. 반환 인덱스는 항상 함수의 SELECT 절에서 세야 한다.

`get_blacklisted_users`를 `SELECT *`로 바꾸면 `created_at`이 유닉스 초가 아닌 타임스탬프 문자열이 되어 `<t:...>` 렌더링이 깨진다.

스키마를 변경했다면 이 표를 갱신하고 해당 호출부를 다시 확인한다.

### 2-2. 스키마 멱등성

`bot.py:135`의 `init_db()`가 매 부팅마다 `executescript`한다.

| 확인 | 실패 시 |
|------|--------|
| 모든 `CREATE TABLE`에 `IF NOT EXISTS` | 두 번째 부팅부터 봇이 죽음 |
| `INSERT`/`ALTER`/`DROP` 문장 없음 | 매 부팅 실행 → 데이터 중복 또는 실패 |

### 2-3. 기존 테이블 컬럼 추가

`CREATE TABLE IF NOT EXISTS`만 고치면 **이미 존재하는 DB에는 반영되지 않는다.** 새 컬럼을 참조하는 `INSERT`가 `no such column`으로 실패한다.

검증 항목:
- 컬럼 추가가 있었다면 `bot.py`의 `init_db()`에 `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` 마이그레이션이 있는가
- `ALTER TABLE`로 추가된 컬럼은 **맨 뒤**(`created_at` 뒤)에 붙으므로, 신규 DB와 기존 DB의 컬럼 순서가 달라진다 → 해당 테이블 조회는 `SELECT *`를 쓰면 안 된다

### 2-4. 트랜잭션

| 확인 | 실패 시 |
|------|--------|
| 모든 쓰기 함수에 `await db.commit()` | 에러 없이 데이터만 사라짐 |
| SQL 값이 `?` 바인딩 | `db검색` 경로로 사용자 입력이 직접 유입 |
| 단일 인자 튜플이 `(x,)` | 문자열이 문자 단위로 펼쳐져 바인딩 개수 오류 |

---

## 3. 커맨드 경계면

### 3-1. 로딩 가능성

`bot.py:381`이 로딩 실패를 삼키므로, 실패한 cog는 **봇이 정상 기동한 상태에서 조용히 사라진다.**

| 확인 | 방법 |
|------|------|
| `async def setup(bot)` 존재 | 자동 검사 |
| 커맨드명 최상위 중복 없음 | 자동 검사 (그룹 서브커맨드는 제외됨) |
| import 가능 | `requirements.txt`에 패키지가 있는가 |
| `__init__`의 config 접근 | 자동 검사 `런타임` 등급 |
| 로그 확인 | `grep "Failed to load extension" discord.log` |

### 3-2. 호출 경로 이중성

`hybrid_command`는 슬래시와 프리픽스 양쪽으로 호출된다. **프리픽스 경로에서 `context.interaction`은 `None`이다.**

| 확인 | 실패 시 |
|------|--------|
| `context.interaction` 직접 사용 시 `None` 분기 존재 | 프리픽스 호출에서 `AttributeError` |
| 3초 초과 작업에 `context.defer()` | 슬래시에서 "응용 프로그램이 응답하지 않습니다" |
| `defer` 후 `context.send()` 사용 | `interaction.followup`를 직접 쓰면 프리픽스가 깨짐 |

### 3-3. 응답 제약

| 대상 | 제한 | 실패 시 |
|------|------|--------|
| Embed description | 4096 | `HTTPException` — 커맨드 전체 실패 |
| Embed field value | 1024 | 동일 |
| Embed field 수 | 25 | 동일 |
| 메시지당 embed | 10 | 동일 |

외부 데이터(LLM 응답, RSS 본문, 스크래핑 결과)가 Embed로 들어가는 모든 경로에 절단 로직이 있는지 확인한다. `bot.py`의 `tldr_feed`가 필드 수로 1024를 나눠 배분하는 패턴을 참고 기준으로 삼는다.

### 3-4. 데코레이터

| 확인 | 실패 시 |
|------|--------|
| `hybrid_command`가 최상단 | 커맨드 등록 실패 |
| 일반 커맨드에 `@checks.not_blacklisted()` | 차단된 사용자가 사용 가능 |
| 파괴적 커맨드에 `@checks.is_owner()` | 권한 상승 |

### 3-5. 사용자 노출 일관성

새 커맨드 추가 시 `cogs/general.py`의 `도움말` 커맨드 문구가 갱신되었는지 확인한다. 자동 검사 대상이 아니므로 육안 대조가 필요하다.

---

## 4. 백그라운드 태스크 경계면

**왼쪽**: `@tasks.loop` 정의 / **오른쪽**: `on_ready`의 `.start()`

| 확인 | 실패 시 |
|------|--------|
| `.start()` 호출 존재 | 태스크가 영원히 실행되지 않음 |
| 본문 전체가 `try/except` | 예외 1회로 루프 영구 정지, 봇은 정상으로 보임 |
| `except`에 `logger.error` | 정지 원인 추적 불가 |
| `bot.get_channel()` 결과 `None` 확인 | `None.send`로 태스크 사망 |
| 정시 실행에 `tasks.loop(time=...)` | 초 단위 폴링은 지연 시 그날 실행을 통째로 건너뜀 |

현재 `news_feed`/`tldr_feed`가 `@tasks.loop(seconds=1)` + 문자열 시각 비교 패턴이다. 이 방식은 루프가 1초 이상 밀리면 `"09:00:00"` 문자열과 영원히 일치하지 않는다. 새 코드에서 이 패턴을 복제하지 않는지 확인한다.

`status_task`는 예외적으로 `try/except`가 없다 — `change_presence`만 호출하는 단순 태스크지만, 네트워크 오류 시 정지 가능성이 있다.

---

## 5. 외부 연동 경계면

| 확인 | 실패 시 |
|------|--------|
| 이벤트 루프 내 동기 `requests` 사용 여부 | 봇 전체 정지 → 하트비트 누락 → 연결 끊김 |
| HTTP status 확인 | 에러 JSON에 `["message"]["content"]` 접근 → `KeyError` |
| 응답 키 접근 방어 | 동일 |
| 타임아웃 설정 | 외부 서버 무응답 시 태스크/커맨드 무한 대기 |

현재 동기 호출 지점 (레거시, 범위 밖이면 수정 요청하지 않음):
- `archiving/__init__.py` — `requests` 기반 GitHub/논문 스크래핑, `on_message`에서 호출됨
- `cogs/llms.py:41` — `genai.generate_content`는 동기 호출

새로 추가되는 연동이 이 패턴을 따르지 않는지 확인한다.

---

## 6. 배포 경계면

| 확인 | 실패 시 |
|------|--------|
| 새 패키지가 `requirements.txt`에 `==` 고정 | 이미지 빌드 실패 또는 버전 드리프트 |
| 패키지가 Alpine(musl)에서 설치 가능 | C 확장 소스 빌드 실패 |
| `config.json`이 커밋되지 않음 | 토큰 유출 — `.gitignore` 확인 |
| 타임존 가정 | 컨테이너는 `TZ=Asia/Seoul`, 로컬 실행은 시스템 기본값 |

`docker-compose.yml`이 프로젝트 전체를 `/app`에 바인드 마운트하므로, 컨테이너 내부에서 `database/database.db`와 `discord.log`가 호스트 파일을 직접 수정한다. 스키마 변경 검증 시 이 DB 파일이 운영 데이터임을 전제한다.

---

## 7. 증상별 진단 경로

| 증상 | 확인 순서 |
|------|----------|
| 봇이 아예 안 뜸 | `config.json` 존재 → `schema.sql` 멱등성 → `bot.py` 문법 |
| 특정 커맨드만 안 보임 | `discord.log`의 `Failed to load extension` → `setup()` 존재 → 커맨드명 중복 → `__init__`의 config 키 |
| 모든 슬래시 커맨드가 안 보임 | `SYNC_COMMANDS_GLOBALLY` 설정 → `/sync guild` 실행 여부 (코드 문제가 아닌 경우가 많다) |
| 커맨드가 응답 없음 | 3초 초과 작업에 `defer` 누락 → 프리픽스면 `context.interaction` None |
| 화면에 엉뚱한 값 | `row[N]` 3자 대조 |
| DB에 저장 안 됨 | `db.commit()` 누락 → `INSERT` 컬럼명이 스키마에 존재하는지 |
| 피드가 어느 날부터 멈춤 | `discord.log`의 traceback → `tasks.loop`의 `try/except` → 초 단위 폴링 지연 |
| 새 환경에서만 실패 | `config_sample.json` 키 누락 → `requirements.txt` 누락 |
