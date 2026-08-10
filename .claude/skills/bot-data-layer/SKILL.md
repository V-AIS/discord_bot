---
name: bot-data-layer
description: "V-AIS Discord Bot의 데이터·연동 계층을 작성한다. database/schema.sql DDL 추가·변경, helpers/db_manager.py의 aiosqlite 비동기 함수 작성, 테이블 마이그레이션, utils/의 RSS·피드 파서, archiving/의 GitHub·논문 스크래핑, bot.py의 tasks.loop 백그라운드 주기 작업, config_sample.json 설정 키 추가, requirements.txt 의존성 추가 시 반드시 이 스킬을 사용할 것. 'DB에 저장', '스키마 추가', '피드 연동', '주기 실행' 요청과 데이터가 저장 안 되거나 피드가 멈춘 문제 진단에도 사용."
---

# 데이터·연동 계층 규약

V-AIS 봇의 `helpers/db_manager.py`, `database/schema.sql`, `utils/`, `archiving/`, `bot.py` 작성 지침.

## DB 구조의 핵심 사실

이 프로젝트는 aiosqlite + **위치 기반 튜플**을 쓴다. `row_factory`를 설정하지 않으므로 `SELECT`는 `tuple`을 반환하고, 호출부는 `row[5]` 같은 인덱스로 값을 꺼낸다.

이 사실의 결과가 이 계층의 가장 중요한 제약이다:

> **DDL의 컬럼 순서가 곧 API다.** 컬럼 순서를 바꾸면 예외 없이 모든 호출부가 잘못된 값을 읽는다.

따라서:
- 새 컬럼은 **항상 `created_at` 직전에** 추가한다. 기존 컬럼 사이에 끼워넣지 않는다
- `created_at`은 모든 테이블에서 마지막 컬럼이다
- 컬럼을 삭제하지 않는다. 미사용 컬럼은 그대로 두는 비용이 인덱스가 밀리는 비용보다 훨씬 싸다

## schema.sql — 멱등성 필수

`bot.py:135`의 `init_db()`가 **매 부팅마다** `executescript(schema.sql)`을 실행한다:

```python
async def init_db():
    async with aiosqlite.connect(...) as db:
        with open(".../database/schema.sql") as file:
            await db.executescript(file.read())
        await db.commit()
```

멱등하지 않은 문장(`CREATE TABLE` without `IF NOT EXISTS`, `INSERT`, `ALTER TABLE`)을 넣으면 **두 번째 부팅부터 봇이 죽는다.** 모든 DDL은 이 형태를 지킨다:

```sql
CREATE TABLE IF NOT EXISTS `table_name` (
  `field_a` varchar(20) NOT NULL,
  `field_b` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

백틱 식별자와 `varchar(N)` 표기는 이 스키마의 관행이다(SQLite는 길이를 강제하지 않지만 문서 역할을 한다).

## 기존 테이블에 컬럼 추가 — schema.sql만 고치면 반영되지 않는다

이것이 이 계층에서 가장 비싼 함정이다. 이미 배포된 `database/database.db`에는 옛 테이블이 존재하고, `CREATE TABLE IF NOT EXISTS`는 **아무 일도 하지 않는다.** 새 컬럼은 생기지 않고, 그 컬럼을 참조하는 `INSERT`가 런타임에 `OperationalError: no such column`으로 실패한다.

컬럼 추가는 `schema.sql` 갱신 + `bot.py`의 `init_db()`에 마이그레이션을 함께 넣는다:

```python
async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        with open(SCHEMA_PATH) as file:
            await db.executescript(file.read())

        # 기존 DB에 신규 컬럼 반영 (멱등)
        async with db.execute("PRAGMA table_info(paper)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        if "abstract" not in columns:
            await db.execute("ALTER TABLE paper ADD COLUMN abstract varchar(1000)")

        await db.commit()
```

`ALTER TABLE ADD COLUMN`은 컬럼을 **맨 뒤**에 붙인다. 따라서 `created_at`보다 뒤에 오게 되어 새 DB와 기존 DB의 컬럼 순서가 달라진다. 이 불일치를 피하려면 새 컬럼을 참조하는 조회는 `SELECT *` 대신 **컬럼을 명시**한다:

```sql
SELECT title, url, abstract FROM paper WHERE ...
```

이 경우 반환 인덱스는 `SELECT` 절 순서를 따르므로 DDL 순서와 무관해진다. 새로 만드는 조회 함수는 처음부터 이 방식을 쓰는 것이 안전하다.

## db_manager 함수 작성

```python
async def add_thing(name: str, url: str) -> None:
    """
    설명.

    :param name: 이름
    :param url: 링크
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO thing(name, url) VALUES (?, ?)",
            (name, url),
        )
        await db.commit()


async def get_thing(name: str) -> list:
    """
    설명.

    :param name: 이름
    :return: list[tuple] — (0:name, 1:url, 2:created_at)
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT * FROM thing WHERE name=?", (name,)
        ) as cursor:
            return await cursor.fetchall()
```

지켜야 할 것:

- **쓰기 후 `await db.commit()`.** 누락하면 에러 없이 데이터만 사라진다. 이 계층에서 가장 조용한 버그다
- **`:return:` docstring에 인덱스 의미를 적는다.** `(0:name, 1:url, 2:created_at)` 형태. 이것이 `cog-developer`가 참조하는 유일한 계약이며, 없으면 호출부가 인덱스를 추측하게 된다
- **파라미터는 반드시 `?` 바인딩.** f-string 금지 — `db검색` 커맨드가 사용자 입력을 그대로 이 계층에 전달한다
- **단일 인자 튜플은 `(x,)`** — 쉼표를 빠뜨리면 문자열이 문자 단위로 펼쳐진다
- **`DATABASE_PATH` 상수를 쓴다.** 경로를 다시 계산하지 않는다

## 조회 함수의 빈 인자 처리

`db검색` 커맨드는 `channel=""`, `teller=""` 같은 빈 문자열을 넘긴다. 기존 `get_paper`/`get_github`가 이를 어떻게 처리하는지 확인하고 같은 방식을 따른다. 빈 값을 "필터 없음"으로 다룰 거라면 명시적으로 분기한다:

```python
if channel:
    conditions.append("channel_name=?")
    params.append(channel)
```

조건을 문자열로 조립하더라도 **값은 항상 `?` 바인딩**을 유지한다.

## 백그라운드 태스크 (bot.py)

`tasks.loop` 안에서 예외가 새어나가면 **해당 루프가 영구 정지**하고, 봇은 멀쩡히 살아있어 아무도 눈치채지 못한다. 예외를 반드시 잡는다:

```python
@tasks.loop(minutes=2.5)
async def youtube_feed():
    channel = bot.get_channel(bot.config["FEED_CHANNEL"]["YOUTUBE"])
    try:
        ...
    except Exception:
        bot.logger.error(str(traceback.format_exc()))
```

새 태스크는 `on_ready`에서 `.start()`를 호출해야 동작한다. 정의만 하고 등록을 빠뜨리면 조용히 실행되지 않는다:

```python
@bot.event
async def on_ready() -> None:
    ...
    status_task.start()
    news_feed.start()
    my_new_feed.start()      # 추가 필수
```

**정해진 시각에 실행하는 작업은 `time=`을 쓴다.** `bot.py`의 `news_feed`/`tldr_feed`는 `@tasks.loop(seconds=1)`로 매초 깨어나 `now.strftime("%H:%M:%S") == "09:00:00"`을 비교하는 레거시 패턴이다. 이 방식은 루프가 1초 이상 지연되면 그날 실행을 통째로 건너뛴다. 새 스케줄 작업은:

```python
from datetime import time
import zoneinfo

KST = zoneinfo.ZoneInfo("Asia/Seoul")

@tasks.loop(time=time(hour=9, minute=0, tzinfo=KST))
async def daily_news():
    ...
```

컨테이너는 `TZ=Asia/Seoul`로 뜨지만(`docker-compose.yml`), 명시적 tzinfo가 로컬 실행과 컨테이너 실행의 동작을 일치시킨다.

`bot.get_channel(...)`은 캐시 미스 시 `None`을 반환한다. `on_ready` 이전이나 잘못된 채널 ID면 `None.send`로 죽는다 — 태스크 시작부에서 확인한다.

## 외부 연동 — async를 유지한다

이벤트 루프 안에서 동기 `requests.get`을 호출하면 그 시간 동안 **봇 전체가 멈춘다** (하트비트 누락 → Discord 연결 끊김). 새 연동은 `aiohttp`를 쓴다:

```python
async with aiohttp.ClientSession() as session:
    async with session.post(url, headers=headers, data=json.dumps(payload)) as response:
        result = await response.json()
```

`archiving/`의 기존 `requests` 사용과 `cogs/llms.py`의 동기 `genai.generate_content`는 레거시다. 요청 범위에 없으면 건드리지 않되, 새 코드에서 따라하지 않는다.

응답 상태를 확인한다 — `response.json()`은 4xx/5xx 본문에도 성공하고, `response["message"]["content"]` 같은 접근이 `KeyError`로 죽는다:

```python
if response.status != 200:
    raise RuntimeError(f"{url} returned {response.status}")
```

## config 키 추가

코드에서 `bot.config["TOKENS"]["X"]["Y"]`를 새로 읽으면, **같은 작업에서** `config_sample.json`에 플레이스홀더를 추가한다:

```json
"TOKENS": {
  "NOTION": { "KEY": "KEY", "MARKET_TABLE_ID": "ID" },
  "GOOGLE": { "KEY": "YOUR_GOOGLE_API_KEY" }
}
```

`config_sample.json`은 신규 배포자가 `config.json`을 만드는 유일한 근거다. 누락되면 새 환경에서 해당 cog가 `KeyError`로 조용히 로딩 실패한다.

실제 `config.json`은 비밀이다. **읽지도, 수정하지도, 출력하지도 않는다.**

cog `__init__`에서 읽는 키는 특히 위험하다 — 키가 없으면 cog 전체가 로딩되지 않는다. 선택적 연동이라면 `.get()`으로 방어하고 커맨드 실행 시점에 안내한다.

## requirements.txt

버전을 `==`로 고정한다. 이 프로젝트는 전 의존성을 핀 고정하며 `python:3.11-alpine`에서 빌드된다. Alpine은 musl libc라 C 확장 wheel이 없는 패키지는 소스 빌드가 필요하고, 빌드 도구가 없어 실패할 수 있다. 순수 파이썬 패키지를 우선한다.

## 체크리스트

- [ ] 모든 DDL이 `CREATE TABLE IF NOT EXISTS`다
- [ ] 새 컬럼을 기존 컬럼 사이에 끼워넣지 않았다
- [ ] 기존 테이블 컬럼 추가라면 `init_db()`에 마이그레이션을 넣었다
- [ ] 쓰기 함수에 `await db.commit()`이 있다
- [ ] 조회 함수 docstring에 `:return:` 인덱스 의미가 있다
- [ ] 모든 SQL 값이 `?` 바인딩이다
- [ ] `tasks.loop` 본문이 `try/except`로 감싸여 있고 `logger.error`가 있다
- [ ] 새 태스크를 `on_ready`에서 `.start()` 했다
- [ ] 새 외부 요청이 `aiohttp` 기반이고 status를 확인한다
- [ ] 새 config 키가 `config_sample.json`에 반영되었다
- [ ] 새 패키지가 `requirements.txt`에 `==`로 고정되었다
- [ ] 시그니처/인덱스 변경을 `cog-developer`에게 통지했다
