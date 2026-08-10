---
name: discord-bot-qa
description: "V-AIS Discord Bot의 파일 간 통합 정합성을 봇 구동 없이 정적 교차 검증한다. config_sample.json↔코드 config 참조, schema.sql↔db_manager INSERT↔호출부 row 인덱스, cog 로딩 가능성(setup 누락·커맨드명 중복), hybrid_command의 context.interaction None 가정, tasks.loop 등록 누락, commit 누락, send() 키워드 누락을 대조한다. 봇 코드 구현 후 검증, 정합성 점검, 경계면 확인, 회귀 확인 시 반드시 이 스킬을 사용할 것. '봇이 안 뜬다', '커맨드가 안 보인다', '피드가 멈췄다', 'DB에 저장이 안 된다' 진단 시에도 사용. 일반적인 코드 품질 리뷰(/code-review, /security-review)를 대체하지 않으며, 그 도구들이 보지 않는 파일 간 계약 불일치를 담당한다."
---

# Discord Bot 통합 정합성 검증

V-AIS 봇은 Discord 토큰과 실제 길드 없이는 구동 검증이 불가능하다. 따라서 **정적 교차 검증이 유일한 방어선**이다.

## 이 봇에서 결함이 사는 곳

개별 파일은 거의 항상 옳다. 결함은 파일 **사이**에 있고, 대부분 **예외 없이 조용히** 나타난다:

| 증상 | 실제 원인 | 조용한 이유 |
|------|----------|-----------|
| 커맨드가 안 보임 | cog 로딩 실패 | `load_cogs()`가 예외를 삼키고 로그만 남긴다 (`bot.py:381`) |
| 화면에 엉뚱한 값 출력 | `row[N]` 인덱스 불일치 | 튜플 인덱스는 범위만 맞으면 예외가 없다 |
| DB에 저장 안 됨 | `db.commit()` 누락 | 트랜잭션이 조용히 롤백된다 |
| 피드가 어느 날부터 멈춤 | `tasks.loop` 내 미포착 예외 | 루프만 죽고 봇은 정상 기동 상태를 유지한다 |
| 새 환경에서만 커맨드 없음 | `config_sample.json` 키 누락 | cog `__init__`의 `KeyError` → 해당 cog만 로딩 실패 |

공통점: **로그를 보지 않으면 아무도 모른다.** 그래서 검증이 필요하다.

## 1단계: 자동 검사부터 돌린다

```bash
python3 .claude/skills/discord-bot-qa/scripts/check_coherence.py
```

프로젝트 루트에서 실행한다(다른 경로면 인자로 루트를 넘긴다). 표준 라이브러리만 쓰므로 설치가 필요 없다.

종료 코드: `0` 결함 없음 / `1` 조치 필요 결함 존재 / `2` 실행 오류.

검사 항목 7종:

| 검사 | 대조 대상 | 잡는 것 |
|------|----------|--------|
| config 키 | 코드의 `config[...]` 체인 ↔ `config_sample.json` | 신규 배포 환경에서의 cog 로딩 실패 |
| cog 구조 | `cogs/*.py` | `setup()` 누락, 커맨드명 중복, `__init__`의 config 접근 |
| interaction 가정 | `hybrid_command` 본문 | 프리픽스 호출 시 `AttributeError` |
| db_manager | 정의된 함수 ↔ `db_manager.X()` 호출 | 미정의 함수 호출, `commit()` 누락, 미사용 함수 |
| 스키마 | `schema.sql` ↔ `INSERT INTO` | 없는 컬럼/테이블, 컬럼-플레이스홀더 개수 불일치, 멱등성 위반 |
| 태스크 | `@tasks.loop` ↔ `.start()` | 등록 누락, `try/except` 누락 |
| send | `send()` 인자 | `embed=` 키워드 누락 |

`참고` 등급 중 `SELECT * FROM X — 반환 인덱스: 0:a, 1:b...` 출력은 **결함이 아니라 2단계 검증에 쓸 자료**다. 이 인덱스 표를 호출부의 `row[N]`과 대조하는 것이 다음 단계다.

**결함 판정 전 오탐을 배제한다.** 스크립트가 지적한 위치의 코드를 직접 열어 확인한다. 예: 그룹 서브커맨드(`@blacklist.command(name="add")`)는 최상위 이름공간을 공유하지 않으므로 중복이 아니다 — 스크립트는 이를 제외하지만, 새로운 형태의 오탐이 나타나면 스크립트를 고친다.

## 2단계: 스크립트가 못 잡는 것을 사람이 본다

자동 검사는 **이름과 개수**를 대조한다. **의미**는 대조하지 못한다. 여기가 당신의 일이다.

### 2-1. row 인덱스 의미 대조 (최우선)

가장 위험한 결함 유형. 인덱스가 범위 안에 있으면 예외가 없고, 그저 잘못된 값이 사용자 화면에 출력된다.

세 곳을 **동시에** 열어 비교한다:

1. `database/schema.sql` — 해당 테이블의 컬럼 순서
2. `helpers/db_manager.py` — 그 함수의 `SELECT` 절과 `:return:` docstring
3. `cogs/*.py` — 호출부의 `row[N]` 접근 전부

예시 (`paper` 테이블):

```
schema.sql 순서: 0:channel_name 1:channel_id 2:message_author 3:message_author_id
                 4:source 5:title 6:authors 7:url 8:conference 9:year 10:created_at

db_manager.get_paper: SELECT * FROM paper  → 위 순서 그대로 반환

cogs/search.py:51: embed.add_field(name=row[5], value=row[7])
                   → 5=title, 7=url. 일치.
```

`SELECT *`가 아니라 컬럼을 명시한 함수(`SELECT title, url FROM ...`)는 **반환 인덱스가 SELECT 절 순서를 따른다.** 스키마 순서와 무관하다. 이 둘을 섞어 보면 반드시 틀린다.

인덱스가 어긋났다면 어느 쪽을 고칠지도 함께 판단한다 — 보통 호출부를 고치는 것이 안전하다. 스키마 컬럼 순서를 바꾸면 **다른 모든 호출부가 함께 밀린다.**

### 2-2. cog 로딩 실패 흔적 확인

```bash
grep -n "Failed to load extension" discord.log
```

`discord.log`는 매 부팅마다 덮어쓰기(`mode="w"`)되므로 마지막 실행 기록만 남는다. 이 줄이 있으면 그 cog의 커맨드는 전부 사라진 상태다.

로그가 없거나 오래되었다면 로딩 가능성을 정적으로 확인한다:

```bash
python3 -c "
import ast, pathlib
for p in sorted(pathlib.Path('cogs').glob('*.py')):
    t = ast.parse(p.read_text())
    ok = any(isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name=='setup' for n in t.body)
    print(('OK  ' if ok else 'FAIL'), p)
"
```

### 2-3. 커맨드 인벤토리 대조

전체 커맨드 목록을 뽑아 `도움말` 커맨드(`cogs/general.py`)의 안내 문구와 대조한다. 새 커맨드를 추가하고 도움말을 갱신하지 않는 누락이 반복적으로 발생한다.

```bash
grep -rn 'hybrid_command(name=' cogs/ | sed -E 's/(.*):.*name="([^"]+)".*/\2\t\1/' | sort
```

### 2-4. 외부 응답 형태 가정

LLM·RSS·스크래핑 응답의 형태를 코드가 어떻게 가정하는지 확인한다. `cogs/llms.py:86`의 `response["message"]["content"]`처럼 중첩 키를 무방비로 접근하면, 서버가 에러 JSON을 반환할 때 `KeyError`가 난다.

확인 항목:
- HTTP status를 확인하는가
- 응답 키 접근이 `.get()`이거나 `try` 안에 있는가
- 응답 텍스트를 Embed에 넣기 전에 길이를 자르는가 (1024/4096 제한)

### 2-5. 설계 계약 대비 이탈

`_workspace/01_architect_design.md`가 있으면 계약 표와 실제 구현을 항목별로 대조한다. 커맨드 시그니처, 함수 시그니처, 반환 인덱스 의미 세 가지가 핵심이다.

## 3단계: 보고

`_workspace/03_qa_report.md`에 기록한다. 모든 결함에 **파일:라인 + 재현 조건 + 확신도 + 담당자 + 수정 방법**을 붙인다.

조치 가능한 보고와 그렇지 않은 보고의 차이:

```
나쁨: "llms.py의 에러 처리가 미흡합니다."

좋음: cogs/llms.py:31 [런타임/확인/cog-developer]
      경계면: hybrid_command ↔ 프리픽스 호출 경로
      재현: 프리픽스로 `!gemini 안녕` 호출 → context.interaction이 None →
            AttributeError: 'NoneType' object has no attribute 'response'
      수정: context.interaction.response.defer() → await context.defer()
            51행의 context.interaction.followup.send(embed=embed) → context.send(embed=embed)
```

확신도는 두 등급만 쓴다:
- **확인** — 코드를 읽고 결함임을 확인했다
- **의심** — 정황상 의심되나 확정하지 못했다 (예: 외부 API 응답 형태에 의존)

추측을 확인으로 보고하면 팀원이 멀쩡한 코드를 고치게 된다.

## 상세 경계면 매트릭스

전체 검증 항목과 각 항목의 대조 방법은 [references/coherence-matrix.md](references/coherence-matrix.md)를 읽는다. 자동 검사에서 결함이 나왔거나, 이번 변경이 스키마·config·백그라운드 태스크를 건드렸을 때 참조한다.

## 검증 종료 조건

다음을 모두 만족하면 검증을 마친다:

- [ ] `check_coherence.py` 종료 코드가 0이거나, 남은 항목이 전부 의도된 것으로 확인됨
- [ ] 변경된 모든 `db_manager` 함수에 대해 스키마↔SELECT↔`row[N]` 3자 대조 완료
- [ ] 변경된 모든 cog에 `setup()`이 있고 커맨드명이 중복되지 않음
- [ ] 새 config 키가 `config_sample.json`에 있음
- [ ] 새 `tasks.loop`가 `on_ready`에서 `.start()`됨
- [ ] 설계서가 있다면 계약 이탈 항목을 전부 확인함
- [ ] 정적으로 확인 불가능한 항목을 "미검증"으로 명시함
