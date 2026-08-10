"""컨테이너 HEALTHCHECK.

이 봇의 전형적 장애는 프로세스가 죽는 것이 아니라 tasks.loop 안에서 예외가 나
해당 루프만 영구 정지하는 형태다. 그때 컨테이너는 계속 "Up" 으로 보인다.
그래서 프로세스 생존이 아니라 각 태스크의 마지막 성공 시각을 본다.

정상 종료 코드 0, 비정상 1.
"""

import os
import sys
import time

HEARTBEAT_DIR = "/tmp/bot_heartbeat"

# (파일명, 허용 지연 초). 루프 주기의 3배 남짓으로 잡아 일시적 지연은 넘긴다.
CHECKS = [
    ("status", 300),    # status_task: 1분 주기
    ("youtube", 900),   # youtube_feed: 2.5분 주기
]


def main() -> int:
    now = time.time()
    problems = []

    for name, max_age in CHECKS:
        path = os.path.join(HEARTBEAT_DIR, name)
        if not os.path.exists(path):
            # 기동 직후에는 아직 하트비트가 없다. start-period 가 이 구간을 덮는다.
            problems.append(f"{name}: 하트비트 없음")
            continue
        age = now - os.path.getmtime(path)
        if age > max_age:
            problems.append(f"{name}: {int(age)}초째 갱신 없음 (허용 {max_age}초)")

    if problems:
        print("UNHEALTHY — " + "; ".join(problems))
        return 1

    print("healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
