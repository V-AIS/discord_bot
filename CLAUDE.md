# V-AIS Discord Bot

## 하네스: Discord Bot 기능 개발

**목표:** 커맨드 계층(`cogs/`)과 데이터 계층(`helpers/`·`database/`·`utils/`)이 경계면에서 어긋나지 않는 구현을 만든다. 이 봇은 실구동 검증이 불가능하므로 정적 교차 검증이 유일한 방어선이다.

**트리거:** 커맨드 추가·수정, 스키마·DB 함수 변경, 외부 연동, 백그라운드 태스크, "봇이 안 뜬다/커맨드가 안 보인다" 진단 요청 시 `vais-bot-orchestrator` 스킬을 사용하라. 파일 위치나 코드 설명 같은 단순 질문은 직접 답한다.

**항상 지킬 것:**
- `config.json`은 비밀 파일이다. 읽지도, 수정하지도, 출력하지도 않는다. 설정 키는 `config_sample.json`으로만 다룬다.
- `database/database.db`는 운영 데이터다. 스키마 문제를 삭제로 해결하지 않는다.
- 코드 변경 후 `python3 .claude/skills/discord-bot-qa/scripts/check_coherence.py`를 실행한다.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-08-09 | 초기 구성 (에이전트 4 + 스킬 4) | 전체 | - |
| 2026-08-09 | 초기화 순서 검사 추가 (검사 8종) | skills/discord-bot-qa/scripts | 전체 기능 검증에서 자동 검사가 `bot.py`의 init_db 이전 DB 접근을 놓침 |
