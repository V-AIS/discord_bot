#!/usr/bin/env python3
"""V-AIS Discord Bot 경계면 정합성 검사.

봇을 구동하지 않고 파일 간 계약 불일치를 기계적으로 대조한다.
의존성 없음 (표준 라이브러리만). 프로젝트 루트에서 실행:

    python3 .claude/skills/discord-bot-qa/scripts/check_coherence.py

종료 코드: 0 = 결함 없음, 1 = 결함 발견, 2 = 실행 오류
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 결과 수집

BLOCKING = "부팅차단"
BOUNDARY = "경계면"
RUNTIME = "런타임"
INFO = "참고"

findings: list[tuple[str, str, str]] = []  # (등급, 위치, 메시지)


def report(level: str, where: str, message: str) -> None:
    findings.append((level, where, message))


# ---------------------------------------------------------------- 공통 유틸


def parse_python(path: Path) -> ast.Module | None:
    """구문 분석. 실패는 부팅 차단 결함으로 기록하고 None 반환."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        report(BLOCKING, f"{path}:{exc.lineno}", f"구문 오류 — {exc.msg}")
        return None


def python_files(root: Path) -> list[Path]:
    skip = {".git", "__pycache__", ".claude", ".idea", "_workspace"}
    return sorted(
        p
        for p in root.rglob("*.py")
        if not any(part in skip for part in p.parts)
        and not any(part.startswith("_workspace") for part in p.parts)
    )


def subscript_chain(node: ast.Subscript) -> tuple[str | None, list[str]] | None:
    """config["A"]["B"] 형태를 (base, ["A", "B"])로 펼친다.

    base는 'config' 또는 'bot.config' 같은 점 표기 문자열.
    문자열 리터럴이 아닌 첨자가 섞이면 None을 반환한다.
    """
    keys: list[str] = []
    cur: ast.expr = node
    while isinstance(cur, ast.Subscript):
        idx = cur.slice
        if not (isinstance(idx, ast.Constant) and isinstance(idx.value, str)):
            return None
        keys.insert(0, idx.value)
        cur = cur.value

    parts: list[str] = []
    while isinstance(cur, ast.Attribute):
        parts.insert(0, cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.insert(0, cur.id)
    else:
        return None
    return ".".join(parts), keys


# ---------------------------------------------------------------- 검사 1: config

def check_config_keys(root: Path) -> None:
    """코드가 읽는 config 키가 config_sample.json에 있는지 대조."""
    sample_path = root / "config_sample.json"
    if not sample_path.exists():
        report(BOUNDARY, "config_sample.json", "파일 없음 — 설정 키 대조 불가")
        return
    try:
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report(BLOCKING, f"config_sample.json:{exc.lineno}", f"JSON 파싱 실패 — {exc.msg}")
        return

    for path in python_files(root):
        tree = parse_python(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            # 중첩 Subscript의 안쪽은 바깥에서 이미 처리되므로 최외곽만 본다
            parent_is_subscript = False
            for other in ast.walk(tree):
                if isinstance(other, ast.Subscript) and other.value is node:
                    parent_is_subscript = True
                    break
            if parent_is_subscript:
                continue

            chain = subscript_chain(node)
            if chain is None:
                continue
            base, keys = chain
            if base.split(".")[-1] != "config" or not keys:
                continue

            cur = sample
            walked: list[str] = []
            for key in keys:
                walked.append(key)
                if isinstance(cur, dict) and key in cur:
                    cur = cur[key]
                else:
                    loc = f"{path.relative_to(root)}:{node.lineno}"
                    report(
                        BOUNDARY,
                        loc,
                        f'config["{'"]["'.join(keys)}"] 참조 — '
                        f"config_sample.json에 '{'.'.join(walked)}' 없음",
                    )
                    break


# ---------------------------------------------------------------- 검사 2: cog

COMMAND_DECOS = {"hybrid_command", "command", "hybrid_group", "group"}


def check_cogs(root: Path) -> None:
    """setup() 존재, 커맨드명 중복, cog __init__의 config 접근을 확인."""
    cogs_dir = root / "cogs"
    if not cogs_dir.is_dir():
        report(INFO, "cogs/", "디렉토리 없음 — cog 검사 생략")
        return

    seen: dict[str, str] = {}  # 커맨드명 -> 위치

    for path in sorted(cogs_dir.glob("*.py")):
        tree = parse_python(path)
        if tree is None:
            continue
        rel = path.relative_to(root)

        has_setup = any(
            isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == "setup"
            for n in tree.body
        )
        if not has_setup:
            report(BLOCKING, str(rel), "async def setup(bot) 없음 — cog가 로딩되지 않는다")

        for node in ast.walk(tree):
            if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue

            # 커맨드명 수집.
            # @commands.hybrid_command(name=...) 처럼 commands 모듈에 직접 달린 것만 센다.
            # @blacklist.command(name="add") 형태는 그룹 서브커맨드라 최상위 이름공간을
            # 공유하지 않으므로 중복 판정 대상이 아니다.
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                fn = deco.func
                if isinstance(fn, ast.Attribute):
                    name = fn.attr
                    owner = fn.value
                    if not (isinstance(owner, ast.Name) and owner.id == "commands"):
                        continue  # 그룹 서브커맨드
                elif isinstance(fn, ast.Name):
                    name = fn.id
                else:
                    continue
                if name not in COMMAND_DECOS:
                    continue
                for kw in deco.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        cmd = kw.value.value
                        loc = f"{rel}:{node.lineno}"
                        if cmd in seen:
                            report(
                                BLOCKING,
                                loc,
                                f"커맨드명 '{cmd}' 중복 (최초: {seen[cmd]}) — "
                                "CommandRegistrationError로 cog 로딩 실패",
                            )
                        else:
                            seen[cmd] = loc

            # cog __init__ 에서의 config 접근
            if node.name == "__init__":
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Subscript):
                        chain = subscript_chain(inner)
                        if chain and chain[0].split(".")[-1] == "config" and chain[1]:
                            report(
                                RUNTIME,
                                f"{rel}:{inner.lineno}",
                                f'__init__에서 config["{chain[1][0]}"] 접근 — '
                                "키 부재 시 cog 전체가 조용히 로딩 실패",
                            )
                            break


# ---------------------------------------------------------------- 검사 3: interaction

def check_interaction_assumption(root: Path) -> None:
    """hybrid_command에서 context.interaction을 무방비로 쓰는 곳을 찾는다."""
    cogs_dir = root / "cogs"
    if not cogs_dir.is_dir():
        return

    for path in sorted(cogs_dir.glob("*.py")):
        tree = parse_python(path)
        if tree is None:
            continue
        rel = path.relative_to(root)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            is_hybrid = any(
                isinstance(d, ast.Call)
                and (
                    (isinstance(d.func, ast.Attribute) and d.func.attr.startswith("hybrid_"))
                    or (isinstance(d.func, ast.Name) and d.func.id.startswith("hybrid_"))
                )
                for d in node.decorator_list
            )
            if not is_hybrid:
                continue

            guarded = "interaction is not None" in ast.unparse(node) or (
                "interaction is None" in ast.unparse(node)
            )
            if guarded:
                continue

            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Attribute)
                    and inner.attr == "interaction"
                    and isinstance(inner.value, ast.Name)
                    and inner.value.id in {"context", "ctx"}
                ):
                    report(
                        RUNTIME,
                        f"{rel}:{inner.lineno}",
                        f"hybrid_command '{node.name}'가 context.interaction을 "
                        "None 분기 없이 사용 — 프리픽스 호출 시 AttributeError",
                    )
                    break


# ---------------------------------------------------------------- 검사 4: db_manager

def check_db_manager(root: Path) -> None:
    """정의된 db_manager 함수와 실제 호출을 대조."""
    dbm_path = root / "helpers" / "db_manager.py"
    if not dbm_path.exists():
        report(INFO, "helpers/db_manager.py", "파일 없음 — DB 계층 검사 생략")
        return

    tree = parse_python(dbm_path)
    if tree is None:
        return

    defined = {
        n.name
        for n in tree.body
        if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and not n.name.startswith("_")
    }

    called: dict[str, list[str]] = {}
    for path in python_files(root):
        if path == dbm_path:
            continue
        t = parse_python(path)
        if t is None:
            continue
        for node in ast.walk(t):
            if not isinstance(node, ast.Attribute):
                continue
            owner = node.value
            owner_name = (
                owner.attr if isinstance(owner, ast.Attribute) else getattr(owner, "id", None)
            )
            if owner_name != "db_manager":
                continue
            called.setdefault(node.attr, []).append(
                f"{path.relative_to(root)}:{node.lineno}"
            )

    for fn, locs in sorted(called.items()):
        if fn not in defined:
            for loc in locs:
                report(
                    BLOCKING,
                    loc,
                    f"db_manager.{fn}() 호출 — helpers/db_manager.py에 정의 없음 (AttributeError)",
                )

    for fn in sorted(defined - set(called)):
        report(INFO, "helpers/db_manager.py", f"{fn}() 정의되었으나 호출부 없음")

    # 쓰기 함수의 commit 누락
    for node in tree.body:
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        src = ast.unparse(node)
        writes = re.search(r"\b(INSERT INTO|UPDATE |DELETE FROM)", src, re.IGNORECASE)
        if writes and "commit()" not in src:
            report(
                BOUNDARY,
                f"helpers/db_manager.py:{node.lineno}",
                f"{node.name}()가 쓰기 SQL을 실행하나 db.commit() 없음 — 데이터가 저장되지 않는다",
            )


# ---------------------------------------------------------------- 검사 5: schema

CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)[`\"]?\s*\((.*?)\n\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
COLUMN_RE = re.compile(r"^\s*[`\"]?(\w+)[`\"]?\s+\w", re.MULTILINE)
INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+[`\"]?(\w+)[`\"]?\s*\(([^)]*)\)\s*VALUES\s*\(([^)]*)\)",
    re.IGNORECASE | re.DOTALL,
)


def check_schema(root: Path) -> None:
    """schema.sql의 테이블/컬럼과 db_manager의 SQL을 대조."""
    schema_path = root / "database" / "schema.sql"
    dbm_path = root / "helpers" / "db_manager.py"
    if not schema_path.exists():
        report(INFO, "database/schema.sql", "파일 없음 — 스키마 검사 생략")
        return

    sql = schema_path.read_text(encoding="utf-8")

    for stmt in re.split(r";\s*\n", sql):
        s = stmt.strip()
        if s.upper().startswith("CREATE TABLE") and "IF NOT EXISTS" not in s.upper():
            name = re.search(r"CREATE\s+TABLE\s+[`\"]?(\w+)", s, re.IGNORECASE)
            report(
                BLOCKING,
                "database/schema.sql",
                f"CREATE TABLE {name.group(1) if name else '?'}에 IF NOT EXISTS 없음 — "
                "재부팅 시 init_db()가 실패한다",
            )
        if s and s.upper().startswith(("INSERT", "ALTER", "DROP")):
            report(
                BLOCKING,
                "database/schema.sql",
                f"멱등하지 않은 문장: {s.splitlines()[0][:60]} — 매 부팅 실행되므로 재부팅 시 실패",
            )

    tables: dict[str, list[str]] = {}
    for match in CREATE_RE.finditer(sql):
        table, body = match.group(1), match.group(2)
        cols = [
            c
            for c in COLUMN_RE.findall(body)
            if c.upper() not in {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}
        ]
        tables[table] = cols

    if not tables:
        report(INFO, "database/schema.sql", "CREATE TABLE을 파싱하지 못함")
        return

    for table, cols in tables.items():
        if cols and cols[-1] != "created_at" and "created_at" in cols:
            report(
                BOUNDARY,
                "database/schema.sql",
                f"{table}: created_at이 마지막 컬럼이 아님 — "
                "새 컬럼이 중간에 삽입되어 호출부의 row[N] 인덱스가 밀렸을 수 있다",
            )

    if not dbm_path.exists():
        return
    dbm_src = dbm_path.read_text(encoding="utf-8")
    lines = dbm_src.splitlines()

    for match in INSERT_RE.finditer(dbm_src):
        table = match.group(1)
        cols = [c.strip().strip("`\"") for c in match.group(2).split(",") if c.strip()]
        placeholders = [p.strip() for p in match.group(3).split(",") if p.strip()]
        line_no = dbm_src[: match.start()].count("\n") + 1
        loc = f"helpers/db_manager.py:{line_no}"

        if len(cols) != len(placeholders):
            report(
                BLOCKING,
                loc,
                f"INSERT INTO {table}: 컬럼 {len(cols)}개 vs 플레이스홀더 "
                f"{len(placeholders)}개 — OperationalError",
            )
        if table not in tables:
            report(
                BLOCKING,
                loc,
                f"INSERT INTO {table}: schema.sql에 없는 테이블 — no such table",
            )
            continue
        for col in cols:
            if col not in tables[table]:
                report(
                    BLOCKING,
                    loc,
                    f"INSERT INTO {table}: schema.sql에 없는 컬럼 '{col}' — no such column",
                )

    # SELECT * 사용 함수는 스키마 컬럼 순서에 인덱스가 종속된다
    for i, line in enumerate(lines, 1):
        if re.search(r"SELECT\s+\*\s+FROM\s+(\w+)", line, re.IGNORECASE):
            table = re.search(r"FROM\s+(\w+)", line, re.IGNORECASE).group(1)
            order = tables.get(table)
            if order:
                report(
                    INFO,
                    f"helpers/db_manager.py:{i}",
                    f"SELECT * FROM {table} — 반환 인덱스가 스키마 순서에 종속: "
                    + ", ".join(f"{n}:{c}" for n, c in enumerate(order)),
                )


# ---------------------------------------------------------------- 검사 6: 태스크

def check_tasks(root: Path) -> None:
    """@tasks.loop 정의와 on_ready의 .start() 호출을 대조."""
    bot_path = root / "bot.py"
    if not bot_path.exists():
        report(INFO, "bot.py", "파일 없음 — 태스크 검사 생략")
        return
    tree = parse_python(bot_path)
    if tree is None:
        return

    src = bot_path.read_text(encoding="utf-8")
    loops: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for deco in node.decorator_list:
            target = deco.func if isinstance(deco, ast.Call) else deco
            if isinstance(target, ast.Attribute) and target.attr == "loop":
                loops.append((node.name, node.lineno))
                body = ast.unparse(node)
                if "try" not in body:
                    report(
                        RUNTIME,
                        f"bot.py:{node.lineno}",
                        f"@tasks.loop {node.name}()에 try/except 없음 — "
                        "예외 발생 시 루프가 영구 정지하고 봇은 정상으로 보인다",
                    )
                if isinstance(deco, ast.Call):
                    for kw in deco.keywords:
                        if kw.arg == "seconds" and isinstance(kw.value, ast.Constant):
                            if kw.value.value <= 1:
                                report(
                                    INFO,
                                    f"bot.py:{node.lineno}",
                                    f"{node.name}()가 매 {kw.value.value}초 폴링 — "
                                    "정시 실행이 목적이면 tasks.loop(time=...)가 안전하다",
                                )

    for name, lineno in loops:
        if not re.search(rf"\b{re.escape(name)}\.start\(\)", src):
            report(
                BOUNDARY,
                f"bot.py:{lineno}",
                f"@tasks.loop {name}()이 정의되었으나 .start() 호출 없음 — 실행되지 않는다",
            )


# ---------------------------------------------------------------- 검사 7: 초기화 순서

def check_init_order(root: Path) -> None:
    """init_db() 보다 먼저 DB를 읽는 모듈 최상위 코드를 찾는다.

    bot.py 는 모듈 최상위에서 객체를 만든 뒤 한참 아래에서 init_db() 를 부른다.
    생성자가 DB를 읽으면 신규 배포(테이블 없음)에서 봇이 기동하지 못한다.
    """
    bot_path = root / "bot.py"
    if not bot_path.exists():
        return
    tree = parse_python(bot_path)
    if tree is None:
        return

    # init_db() 호출 위치
    init_line = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and "init_db" in ast.unparse(node):
            init_line = node.lineno
            break
    if init_line is None:
        return

    # 생성자에서 DB를 건드리는 클래스 수집 (utils/, archiving/, helpers/)
    risky: dict[str, str] = {}
    for pkg in ("utils", "archiving", "helpers"):
        pkg_dir = root / pkg
        if not pkg_dir.is_dir():
            continue
        for path in sorted(pkg_dir.glob("*.py")):
            t = parse_python(path)
            if t is None:
                continue
            for node in ast.walk(t):
                if not isinstance(node, ast.ClassDef):
                    continue
                for item in node.body:
                    if not isinstance(item, (ast.AsyncFunctionDef, ast.FunctionDef)):
                        continue
                    if item.name != "__init__":
                        continue
                    body = ast.unparse(item)
                    if "db_manager" in body or "aiosqlite" in body:
                        risky[node.name] = f"{path.relative_to(root)}:{item.lineno}"
                    if "asyncio.run" in body:
                        report(
                            RUNTIME,
                            f"{path.relative_to(root)}:{item.lineno}",
                            f"{node.name}.__init__ 이 asyncio.run() 호출 — "
                            "이미 실행 중인 이벤트 루프 안에서 생성하면 RuntimeError",
                        )

    # init_db() 이전의 모듈 최상위 객체 생성 검사
    for node in tree.body:
        if node.lineno >= init_line:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            fn = inner.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name in risky:
                report(
                    BLOCKING,
                    f"bot.py:{node.lineno}",
                    f"{name}() 생성이 init_db()(bot.py:{init_line}) 보다 먼저 실행됨 — "
                    f"생성자가 DB를 읽는다({risky[name]}). "
                    "신규 배포 시 no such table 로 봇이 기동하지 못한다",
                )


# ---------------------------------------------------------------- 검사 8: send

def check_send_kwargs(root: Path) -> None:
    """context.send(embed) 처럼 키워드가 빠진 호출을 찾는다."""
    for path in python_files(root):
        tree = parse_python(path)
        if tree is None:
            continue
        rel = path.relative_to(root)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not (isinstance(fn, ast.Attribute) and fn.attr == "send"):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Name) and arg.id in {"embed", "embeds", "file", "view"}:
                    report(
                        RUNTIME,
                        f"{rel}:{node.lineno}",
                        f"send({arg.id}) — '{arg.id}=' 키워드 누락. "
                        "Embed 객체가 content로 전달되어 HTTPException",
                    )


# ---------------------------------------------------------------- 출력

ORDER = {BLOCKING: 0, BOUNDARY: 1, RUNTIME: 2, INFO: 3}


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not (root / "bot.py").exists() and not (root / "cogs").is_dir():
        print(f"[오류] 프로젝트 루트가 아닙니다: {root}", file=sys.stderr)
        print("사용법: python3 check_coherence.py [프로젝트_루트]", file=sys.stderr)
        return 2

    for check in (
        check_config_keys,
        check_cogs,
        check_interaction_assumption,
        check_db_manager,
        check_schema,
        check_tasks,
        check_init_order,
        check_send_kwargs,
    ):
        try:
            check(root)
        except Exception as exc:  # 한 검사의 실패가 나머지를 막지 않는다
            report(INFO, check.__name__, f"검사 실행 실패: {type(exc).__name__}: {exc}")

    findings.sort(key=lambda f: (ORDER.get(f[0], 9), f[1]))

    counts = {level: 0 for level in ORDER}
    for level, _, _ in findings:
        counts[level] = counts.get(level, 0) + 1

    print(f"=== 경계면 정합성 검사: {root} ===\n")
    if not findings:
        print("결함 없음.")
        return 0

    current = None
    for level, where, message in findings:
        if level != current:
            print(f"\n--- [{level}] ---")
            current = level
        print(f"  {where}\n    {message}")

    print("\n=== 요약 ===")
    for level in (BLOCKING, BOUNDARY, RUNTIME, INFO):
        print(f"  {level}: {counts.get(level, 0)}건")

    actionable = counts.get(BLOCKING, 0) + counts.get(BOUNDARY, 0) + counts.get(RUNTIME, 0)
    return 1 if actionable else 0


if __name__ == "__main__":
    sys.exit(main())
