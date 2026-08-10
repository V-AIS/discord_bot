---
name: vais-bot-orchestrator
description: "V-AIS Discord Bot의 기능 개발을 에이전트 팀으로 조율하는 오케스트레이터. 새 슬래시 커맨드/cog 추가, 기존 커맨드 수정, DB 스키마·테이블 추가, RSS·LLM·외부 API 연동, 백그라운드 주기 태스크 추가, 아카이빙 파이프라인 변경 시 반드시 이 스킬을 사용할 것. 후속 작업에도 사용: 다시 실행, 재실행, 업데이트, 수정, 보완, 이전 결과 개선, '커맨드만 다시', 'DB 쪽만 고쳐줘', 리뷰 반영. 봇이 안 뜨거나 커맨드가 안 보이는 문제 진단에도 사용. 단순 질문(파일 위치, 코드 설명)은 이 스킬 없이 직접 답한다."
---

# V-AIS Bot Orchestrator

V-AIS Discord Bot의 기능 개발을 에이전트 팀으로 조율하여, 커맨드 계층과 데이터 계층이 **서로 어긋나지 않는** 구현을 만든다.

## 실행 모드: 에이전트 팀

팀 모드를 쓰는 이유는 이 프로젝트의 결함이 전부 경계면에 있기 때문이다. `cog-developer`가 `row[5]`를 title로 읽는데 `data-engineer`가 컬럼 순서를 바꾸면, 두 사람의 코드는 각각 옳고 합쳐진 결과만 틀린다. 이 어긋남은 서로 직접 통신할 때만 실시간으로 잡힌다.

## 에이전트 구성

| 팀원 | agent_type | 역할 | 스킬 | 산출물 |
|------|-----------|------|------|--------|
| architect | `bot-architect` | 요구사항 → 구현 계약 | — | `_workspace/01_architect_design.md` |
| cog-dev | `cog-developer` | `cogs/` 커맨드 계층 | `discord-cog-development` | `cogs/*.py` + `_workspace/02_cog_developer_report.md` |
| data-eng | `data-engineer` | DB·연동·태스크 계층 | `bot-data-layer` | `helpers/`,`database/`,`utils/`,`archiving/`,`bot.py` + `_workspace/02_data_engineer_report.md` |
| qa | `integration-qa` | 경계면 교차 검증 | `discord-bot-qa` | `_workspace/03_qa_report.md` |

모든 팀원은 `model: "opus"`로 생성한다.

**파일 소유권은 배타적이다.** cog-dev는 `cogs/`만, data-eng는 그 외 코드만 편집한다. 두 에이전트가 같은 파일을 동시에 열면 나중 쓰기가 앞선 변경을 지운다.

## 워크플로우

### Phase 0: 컨텍스트 확인

작업 디렉토리는 항상 프로젝트 루트 `/home/jerry/Project/vais/discord_bot`이다.

1. `_workspace/` 존재 여부를 확인한다
2. 실행 모드를 판정한다:

| 상황 | 모드 | 처리 |
|------|------|------|
| `_workspace/` 없음 | **초기 실행** | Phase 1로 진행 |
| `_workspace/` 있음 + 기존 결과에 대한 수정 요청 | **부분 재실행** | `_workspace/` 유지. 해당 팀원만 재호출하며 이전 산출물 경로를 프롬프트에 포함 |
| `_workspace/` 있음 + 새로운 기능 요청 | **새 실행** | `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 이동 후 Phase 1 |

판단이 애매하면 사용자에게 묻는다. 이전 산출물을 잘못 덮어쓰는 것이 되묻는 비용보다 비싸다.

3. **부분 재실행이면 Phase 2의 팀 구성을 축소한다.** 예: "커맨드 응답 문구만 고쳐줘" → cog-dev + qa 2명만 생성. architect와 data-eng를 부르지 않는다.

### Phase 1: 준비

1. 사용자 요구사항을 분석한다 — 커맨드 추가인가, 데이터 계층 변경인가, 둘 다인가, 진단인가
2. `_workspace/` 디렉토리를 생성한다
3. 참고 자료(스펙 문서, 에러 로그, 스크린샷 등)가 있으면 `_workspace/00_input/`에 저장한다
4. **베이스라인 QA를 먼저 돌린다:**

```bash
python3 .claude/skills/discord-bot-qa/scripts/check_coherence.py > _workspace/00_baseline_qa.txt 2>&1
```

이 파일이 작업 전 상태다. 작업 후 QA 결과와 비교해야 **이번 변경이 만든 결함**과 **원래 있던 결함**을 구분할 수 있다. 이 단계를 빠뜨리면 QA가 기존 결함을 신규 결함으로 보고한다.

### Phase 2: 팀 구성

```
TeamCreate(
  team_name: "vais-bot-team",
  members: [
    { name: "architect", agent_type: "bot-architect",   model: "opus",
      prompt: "요구사항: {원문}. _workspace/01_architect_design.md에 구현 계약을 작성하라.
               커맨드 시그니처, db_manager 함수 시그니처, 반환 튜플의 인덱스 의미,
               필요한 config 키를 문자열 수준까지 확정하라.
               완료 시 cog-dev와 data-eng 양쪽에 SendMessage로 각자 담당 계약을 전달하고,
               qa에게 회귀 위험 목록을 전달하라." },
    { name: "cog-dev",   agent_type: "cog-developer",  model: "opus",
      prompt: "architect의 커맨드 계약대로 cogs/ 를 구현하라.
               작업 전 discord-cog-development 스킬을 Skill 도구로 호출하라.
               cogs/ 외 파일은 편집하지 말고 data-eng에게 요청하라.
               커맨드 완성 즉시 qa에게 알려라." },
    { name: "data-eng",  agent_type: "data-engineer",  model: "opus",
      prompt: "architect의 데이터 계약대로 구현하라.
               작업 전 bot-data-layer 스킬을 Skill 도구로 호출하라.
               cogs/ 는 편집하지 말라.
               DB 함수 완성 즉시 최종 시그니처와 반환 인덱스 의미를 cog-dev에게 SendMessage로 보내라." },
    { name: "qa",        agent_type: "integration-qa", model: "opus",
      prompt: "경계면을 교차 검증하라. 작업 전 discord-bot-qa 스킬을 Skill 도구로 호출하라.
               _workspace/00_baseline_qa.txt가 작업 전 상태다. 이번 변경이 만든 결함만 보고하라.
               전체 완성을 기다리지 말고 모듈 완료 알림을 받는 즉시 해당 경계면을 검증하라.
               직접 수정하지 말고 담당자에게 수정을 요청하라." }
  ]
)
```

작업 등록:

```
TaskCreate(tasks: [
  { title: "구현 계약 설계",        assignee: "architect" },
  { title: "커맨드 계층 구현",      assignee: "cog-dev",  depends_on: ["구현 계약 설계"] },
  { title: "데이터 계층 구현",      assignee: "data-eng", depends_on: ["구현 계약 설계"] },
  { title: "경계면 점진 검증",      assignee: "qa",       depends_on: ["구현 계약 설계"] },
  { title: "결함 수정",            assignee: "cog-dev",  depends_on: ["경계면 점진 검증"] },
  { title: "최종 정합성 검증",      assignee: "qa",       depends_on: ["커맨드 계층 구현", "데이터 계층 구현"] }
])
```

`qa`의 "경계면 점진 검증"이 구현 작업에 의존하지 **않는** 것은 의도적이다. QA는 구현이 끝나기를 기다리지 않고 모듈 단위로 검증한다.

### Phase 3: 설계

architect가 단독으로 실행한다. 다른 팀원은 대기한다.

설계 완료 조건: `_workspace/01_architect_design.md`에 커맨드 계약·데이터 계약·인덱스 의미·config 키가 전부 채워짐.

**리더 개입 지점**: 설계서의 "관찰된 기존 결함" 절을 읽고, 이번 범위에 포함할지 판단한다. 사용자가 요청하지 않은 수정을 임의로 범위에 넣지 않는다 — 발견 사실만 최종 보고에 포함한다.

### Phase 4: 병렬 구현 + 점진 검증

cog-dev와 data-eng가 동시에 작업한다. qa는 완료 알림이 올 때마다 해당 경계면을 검증한다.

**필수 통신 규칙** — 이것을 지키지 않으면 팀 모드를 쓸 이유가 없다:

| 발신 | 수신 | 내용 | 시점 |
|------|------|------|------|
| data-eng | cog-dev | DB 함수 최종 시그니처 + 반환 인덱스 의미 | 함수 완성 즉시 |
| cog-dev | data-eng | 필요한 DB 함수 요청 | 구현 착수 전 |
| cog-dev / data-eng | qa | 모듈 완료 | 모듈마다 |
| qa | 담당자 | 파일:라인 + 재현 조건 + 수정 방법 | 결함 발견 즉시 |
| qa | 양쪽 모두 | 경계면 결함 | 어느 쪽을 고칠지 제안과 함께 |
| 누구든 | architect | 계약대로 구현 불가 | 즉시 |

**cog-dev는 db_manager 함수가 없는 상태에서 호출부를 추측해 작성하지 않는다.** 함수를 요청하고, 그 사이 다른 커맨드를 먼저 처리한다.

**리더 모니터링**: `TaskGet`으로 진행률을 확인한다. 팀원이 유휴 상태가 되면 알림이 온다. 특정 팀원이 막혔으면 `SendMessage`로 개입한다.

### Phase 5: 최종 검증

1. 모든 구현 작업 완료를 `TaskGet`으로 확인한다
2. qa에게 최종 전수 검증을 요청한다:
   - `check_coherence.py` 재실행 후 `_workspace/00_baseline_qa.txt`와 diff
   - 변경된 모든 `db_manager` 함수에 대한 스키마↔SELECT↔`row[N]` 3자 대조
   - 설계 계약 대비 이탈 확인
3. `부팅 차단` 또는 `경계면` 등급 결함이 남아 있으면 Phase 4로 돌아가 수정을 지시한다
4. **수정 왕복은 최대 2회.** 2회 후에도 남으면 미해결로 기록하고 사용자에게 판단을 넘긴다. 무한 루프를 만들지 않는다

### Phase 6: 정리

1. 팀원들에게 종료를 알리고 `TeamDelete`로 팀을 정리한다
2. `_workspace/`는 **삭제하지 않는다** — 사후 검증과 부분 재실행의 입력이다
3. 사용자에게 보고한다:
   - 변경된 파일 목록
   - 추가/수정된 커맨드와 그 사용법
   - 스키마 변경이 있었다면 **기존 `database/database.db`에 대한 영향과 마이그레이션 여부**
   - `config_sample.json` 변경이 있었다면 사용자가 실제 `config.json`에 추가해야 할 키
   - QA 미해결 항목과 미검증 항목
   - 설계 중 발견된 기존 결함 (범위 밖으로 남긴 것)

**실환경 검증은 사용자 몫임을 명시한다.** 이 팀은 봇을 구동하지 않는다. 커맨드 반영에는 `/sync guild` 실행이 필요할 수 있다는 점을 함께 안내한다.

4. 피드백을 요청한다: "결과에서 고칠 부분이나, 팀 구성·워크플로우에 바꾸고 싶은 점이 있나요?"

## 데이터 흐름

```
사용자 요구사항
      ↓
[리더] Phase 1: 베이스라인 QA → _workspace/00_baseline_qa.txt
      ↓ TeamCreate
[architect] → _workspace/01_architect_design.md
      │
      ├── SendMessage(계약) ──→ [cog-dev]  ←──SendMessage(시그니처+인덱스)──┐
      │                              ↓                                      │
      │                          cogs/*.py                                  │
      ├── SendMessage(계약) ──→ [data-eng] ────────────────────────────────┘
      │                              ↓
      │                    helpers/ database/ utils/ bot.py
      │                              ↓
      └── SendMessage(회귀위험) → [qa] ← 모듈 완료 알림 (양쪽에서 수시)
                                    ↓
                          _workspace/03_qa_report.md
                                    ↓ 결함 → SendMessage → 담당자 (최대 2회 왕복)
                                    ↓
                            [리더] 최종 보고
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| architect가 요구사항을 확정 못함 | 리더가 사용자에게 질의. 임의 가정으로 진행하지 않는다 |
| 팀원 1명 실패/중지 | `SendMessage`로 상태 확인 → 1회 재시작 → 실패 시 작업을 리더가 직접 수행하고 보고서에 명시 |
| cog-dev와 data-eng의 인덱스 해석 충돌 | architect에게 판정 요청. 설계서가 단일 진실 원천이다 |
| QA 결함이 2회 왕복 후에도 남음 | 미해결로 기록하고 사용자에게 보고. 강제로 넘어가지 않는다 |
| 스키마 변경이 기존 DB와 충돌 | **`database/database.db`를 삭제하지 않는다.** 운영 데이터다. 마이그레이션 경로를 설계하고 없으면 사용자에게 확인 |
| 파일 편집 충돌 | 소유권 규칙 위반. 해당 팀원에게 재읽기 후 병합 지시 |
| 외부 API 검증 불가 | 코드는 완성하되 "실환경 검증 미완"으로 보고 |
| `config.json` 접근 요구 | 거부한다. 비밀 파일이다. `config_sample.json`만 다룬다 |

## 테스트 시나리오

### 정상 흐름 — 커맨드 + 스키마 동시 변경

1. 사용자: "회원들이 공유한 유튜브 영상을 채널별로 검색하는 커맨드를 만들어줘"
2. Phase 1: 베이스라인 QA 저장 (기존 결함 13건 기록)
3. Phase 2: 팀 4명 + 작업 6개 생성
4. Phase 3: architect가 `/유튜브검색` 커맨드 계약과 `get_youtube_video_by_channel(channel: str) -> list` 반환 인덱스를 확정
5. Phase 4: data-eng가 함수 구현 후 인덱스 의미를 cog-dev에 전달 → cog-dev가 `row[2]`(video_link)로 Embed 구성 → qa가 3자 대조
6. Phase 5: `check_coherence.py` 결과가 베이스라인과 동일(신규 결함 0)
7. Phase 6: 팀 정리, `/sync guild` 필요 안내
8. 예상 결과: `cogs/search.py`에 커맨드 추가, `helpers/db_manager.py`에 함수 추가, 신규 결함 없음

### 에러 흐름 — 경계면 어긋남 발생

1. Phase 4에서 data-eng가 설계와 다르게 `SELECT channel_name, video_link`로 컬럼을 명시해 구현 (반환 인덱스가 스키마 순서와 달라짐)
2. cog-dev는 설계서 인덱스(`row[2]`)를 그대로 사용 → 잘못된 값 참조
3. qa가 모듈 완료 알림을 받고 3자 대조 → `row[2]`가 범위를 벗어남을 발견
4. qa가 **양쪽 모두**에게 결함 전달: "data-eng가 `SELECT *`로 되돌리거나, cog-dev가 `row[1]`로 변경. 전자를 권장 — 설계 계약 유지"
5. data-eng 수정 → qa 재검증 통과
6. 최종 보고에 계약 이탈이 있었음과 해소 방법을 기록

### 부분 재실행 흐름

1. 사용자: "커맨드 응답 문구를 더 친근하게 바꿔줘"
2. Phase 0: `_workspace/` 존재 + 기존 결과 수정 요청 → **부분 재실행** 판정
3. Phase 2: cog-dev + qa 2명만 생성. architect·data-eng 생략
4. cog-dev가 `_workspace/02_cog_developer_report.md`를 읽고 해당 커맨드만 수정
5. qa가 Embed 길이 제한과 기존 인덱스 사용에 회귀가 없는지 확인
6. `_workspace/`는 덮어쓰지 않고 갱신
