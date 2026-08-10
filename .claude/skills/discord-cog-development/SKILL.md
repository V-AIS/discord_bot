---
name: discord-cog-development
description: "V-AIS Discord Bot의 cogs/ 커맨드 계층을 discord.py 2.4 규약대로 작성한다. 슬래시/프리픽스 커맨드 추가, hybrid_command 작성, Embed 응답 구성, defer/followup 처리, app_commands.describe 인자 설명, checks 권한 데코레이터, discord.ui View/Select 상호작용, 새 cog 파일 신설, 기존 커맨드 수정 시 반드시 이 스킬을 사용할 것. 커맨드가 안 먹거나 cog가 로딩되지 않는 문제를 진단할 때도 사용."
---

# Discord Cog 개발 규약

V-AIS 봇의 `cogs/` 커맨드 계층 작성 지침. 이 프로젝트는 Krypton discord.py 템플릿 5.5.0 기반이며, `bot.py`의 `load_cogs()`가 `cogs/` 하위 모든 `.py`를 자동 로딩한다.

## 로딩 메커니즘 — 먼저 이해할 것

`bot.py:375`의 `load_cogs()`는 `cogs/` 디렉토리를 순회하며 각 파일을 `bot.load_extension()`으로 로딩하고, **실패해도 예외를 삼키고 로그만 남긴 뒤 다음 파일로 넘어간다.**

```python
except Exception as e:
    bot.logger.error(f"Failed to load extension {extension}\n{exception}")
```

결과: cog 하나가 깨져도 **봇은 정상 기동하고 해당 커맨드만 사라진다.** "커맨드가 안 보인다"는 신고의 대부분이 이것이다. 진단 시 `discord.log`에서 `Failed to load extension`을 먼저 찾는다.

로딩이 실패하는 대표 원인:
- 파일에 `async def setup(bot)` 함수가 없음
- 모듈 최상위나 cog `__init__`에서 `config` 키 접근 시 `KeyError` — `cogs/llms.py`의 `genai.configure(api_key=bot.config["TOKENS"]["GOOGLE"]["KEY"])`가 이 패턴이다
- 다른 cog와 커맨드명 중복
- import 실패 (`requirements.txt` 미반영 패키지)

## cog 파일 골격

```python
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks, db_manager


class MyFeature(commands.Cog, name="myfeature"):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="커맨드명", description="한국어 설명")
    @checks.not_blacklisted()
    @app_commands.describe(keyword="인자 설명")
    async def my_command(self, context: Context, *, keyword: str) -> None:
        embed = discord.Embed(title="제목", color=0x9C84EF)
        await context.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MyFeature(bot))
```

`setup(bot)`이 없으면 로딩되지 않는다. `name=`은 소문자 영문으로, 커맨드명은 한국어로 쓰는 것이 이 프로젝트의 관행이다(`아카이브검색`, `마켓등록`, `서버정보`).

## 데코레이터 순서

```python
@commands.hybrid_command(...)   # 1. 커맨드 정의가 항상 맨 위
@checks.not_blacklisted()       # 2. 권한 체크
@app_commands.describe(...)     # 3. 슬래시 인자 설명
async def cmd(self, context: Context, ...):
```

`hybrid_command`가 맨 위가 아니면 데코레이터가 커맨드 객체가 아닌 일반 함수에 적용되어 등록이 실패한다.

권한 체크는 두 가지가 있다:
- `@checks.not_blacklisted()` — 일반 커맨드 전부에 붙인다
- `@checks.is_owner()` — `config.json`의 `OWNERS` 목록만 허용. 파괴적 작업(`shutdown`, `sync`, 블랙리스트 관리)에 사용

## defer / followup — 가장 흔한 크래시 원인

`hybrid_command`는 슬래시와 프리픽스 **양쪽**으로 호출된다. 프리픽스로 호출되면 `context.interaction`은 `None`이다.

`cogs/llms.py:31`의 현재 코드는 이 사실을 무시한다:

```python
await context.interaction.response.defer(...)   # 프리픽스 호출 시 AttributeError
```

3초 이상 걸리는 작업(LLM 호출, 외부 API, 스크래핑)에는 defer가 **필요하다** — Discord는 3초 내 응답이 없으면 상호작용을 실패 처리한다. 양쪽을 모두 지원하려면:

```python
async def slow_command(self, context: Context, *, content: str) -> None:
    await context.defer()          # 슬래시면 defer, 프리픽스면 typing 표시
    result = await do_slow_work(content)
    embed = discord.Embed(description=result, color=discord.Color.green())
    await context.send(embed=embed)   # defer 후에도 context.send로 응답
```

`context.defer()`와 `context.send()`는 discord.py의 `Context`가 두 경로를 모두 흡수해준다. `context.interaction.response`/`context.interaction.followup`를 직접 만지면 프리픽스 경로가 깨진다.

`context.interaction`을 꼭 직접 써야 한다면 반드시 분기한다:

```python
if context.interaction is not None:
    await context.interaction.response.defer(ephemeral=True)
```

## Embed 규약

색상 관례:

| 상황 | 색상 |
|------|------|
| 일반/정보 | `0x9C84EF` |
| 성공 | `discord.Color.green()` |
| 실패/에러 | `0xE02B2B` 또는 `discord.Color.red()` |

Discord가 강제하는 길이 제한 — 초과하면 `HTTPException`으로 커맨드 전체가 실패한다:

| 대상 | 제한 |
|------|------|
| `title` | 256 |
| `description` | 4096 |
| field `name` | 256 |
| field `value` | 1024 |
| 임베드당 field 수 | 25 |
| 메시지당 embed 수 | 10 |

외부 데이터(LLM 응답, 스크래핑 결과, RSS 본문)를 넣을 때는 항상 자른다:

```python
MAX = 1024
if len(value) > MAX:
    value = value[:MAX - 3] + "..."
embed.add_field(name=title, value=value, inline=False)
```

`bot.py`의 `tldr_feed`가 필드 수로 1024를 나눠 예산을 배분하는 패턴을 쓴다 — 필드가 많을 때 참고한다.

여러 결과를 보낼 때는 `embeds=` 리스트로 한 번에 보낸다(`cogs/search.py:39`). 단 10개를 넘기지 않는다.

## 에러 처리 패턴

사용자에게는 톤을 유지하고, 진단 정보는 로그로 보낸다:

```python
try:
    result = await external_call()
    embed.color = discord.Color.green()
    embed.description = result
except Exception as e:
    embed.color = discord.Color.red()
    embed.description = "기능 확인이 필요합니다! 운영진에게 알려주세요!"
    self.bot.logger.error(f"{e}")
```

`self.bot.logger`는 `bot.py`에서 주입된다. `print`를 쓰지 않는다 — `discord.log` 파일에 남지 않는다.

전역 에러 핸들러는 `bot.py`의 `on_command_error`에 있으며 `CommandOnCooldown`, `UserBlacklisted`, `UserNotOwner`, `MissingPermissions`, `MissingRequiredArgument`를 처리한다. cog에서 이들을 중복 처리하지 않는다.

## 인자 타입

discord.py가 슬래시 인자로 변환할 수 있는 타입만 쓴다:

```python
# 선택지 고정 — 슬래시에서 드롭다운으로 표시된다
subject: typing.Literal["논문", "깃헙"]

# 선택 인자는 기본값을 준다
channel: str = ""

# 나머지 전부를 하나의 문자열로 — 마지막 인자에만 쓸 수 있다
*, content: str

# Discord 객체는 그대로 받는다
user: discord.User
member: discord.Member
```

`*` 뒤의 인자는 프리픽스 호출 시 "나머지 전부"를 흡수한다. 이것이 없으면 `!질문 오늘 날씨 어때`가 인자 3개로 쪼개져 실패한다.

## 커맨드명 충돌 확인

추가 전 반드시 실행한다:

```bash
grep -rhn 'hybrid_command(name=' cogs/ | sed -E 's/.*name="([^"]+)".*/\1/' | sort | uniq -d
```

출력이 있으면 중복이다. 중복 커맨드명은 나중에 로딩된 cog가 `CommandRegistrationError`로 실패한다.

## 커맨드 반영 방법

새 커맨드는 Discord에 동기화되어야 보인다:

- `config.json`의 `SYNC_COMMANDS_GLOBALLY: true`면 `on_ready`에서 자동 전역 동기화 (반영까지 최대 1시간)
- 즉시 반영하려면 봇 소유자가 `/sync guild`를 실행 (`cogs/owner.py`)

커맨드를 추가했는데 안 보인다면 이 동기화 단계를 먼저 의심한다. 코드 문제가 아닌 경우가 많다.

## discord.ui 상호작용

버튼·드롭다운이 필요하면 `cogs/fun.py`의 `RockPaperScissors` 패턴을 따른다:

- `discord.ui.View` 서브클래스에 `timeout=` 설정 (기본 180초)
- 콜백 안에서 `interaction.response.edit_message(...)`로 원본 메시지를 갱신
- View 인스턴스는 커맨드마다 새로 만든다 — 재사용하면 상태가 섞인다

## 데이터 계층 호출

`db_manager` 함수는 **위치 기반 튜플**을 반환한다. `sqlite3.Row`가 아니므로 컬럼명 접근이 불가능하다:

```python
query_result = await db_manager.get_paper(channel, teller)
for row in query_result[:5]:
    embed.add_field(name=row[5], value=row[7], inline=False)   # 5=title, 7=url
```

인덱스를 추측하지 않는다. `helpers/db_manager.py`의 해당 함수 docstring과 `database/schema.sql`의 컬럼 순서를 **직접 읽어** 확인한다. 인덱스를 틀리면 예외 없이 잘못된 값이 화면에 출력된다.

`db_manager`에 없는 함수가 필요하면 직접 만들지 않는다 — `data-engineer`에게 요청한다.

## 체크리스트

커맨드 작성 후 확인:

- [ ] 파일에 `async def setup(bot)`가 있다
- [ ] 데코레이터 순서가 `hybrid_command` → `checks` → `describe`다
- [ ] 커맨드명이 기존과 중복되지 않는다
- [ ] 3초 이상 걸릴 수 있으면 `context.defer()`를 호출한다
- [ ] `context.interaction`을 직접 쓴다면 `None` 분기가 있다
- [ ] 외부 데이터를 Embed에 넣을 때 길이를 자른다
- [ ] `except` 블록에 `self.bot.logger.error`가 있다
- [ ] `db_manager` 반환 인덱스를 실제 코드로 확인했다
- [ ] cog `__init__`에서 config 키를 읽는다면, 그 키가 `config_sample.json`에 있다
