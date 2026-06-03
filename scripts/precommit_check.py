# -*- coding: utf-8 -*-
"""커밋 전 안전점검 (GitHub 업로드 가능 여부 세부 점검).

이 스크립트는 "지금 커밋하면 GitHub 에 올라갈 파일"을 시뮬레이션하고,
원본/가공 데이터, DB, 코드북, 비밀정보, 초대형 파일이 섞여 있지 않은지
세세하게 점검한다. 하나라도 위반이면 종료코드 1 을 반환한다(=커밋 금지).

단독 실행:
    python scripts/precommit_check.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

try:  # Windows 콘솔(cp949)에서도 한글/기호 출력이 깨지거나 죽지 않도록
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ── 금지 규칙 ──────────────────────────────────────────────────────────
# 데이터/DB/코드북 폴더 (이 안의 파일은 .gitkeep 외에는 커밋 금지)
FORBIDDEN_DIRS = ("data/raw/", "data/processed/", "data/db/", "data/codebook/")
# 데이터/바이너리 확장자 (어디에 있든 커밋 금지)
FORBIDDEN_EXTS = (
    ".csv", ".xlsx", ".xls", ".sav", ".dta", ".parquet",
    ".sqlite", ".sqlite3", ".db",
)
# 비밀정보로 보이는 파일명 패턴
SECRET_PATTERNS = (
    re.compile(r"(^|/)\.env(\.|$)"),
    re.compile(r"(^|/)secrets?\."),
    re.compile(r"\.key$"),
    re.compile(r"\.pem$"),
    re.compile(r"(^|/)credentials"),
    re.compile(r"\.streamlit/secrets\.toml$"),
)
# 비밀정보로 보이는 내용 패턴 (작은 텍스트 파일만 스캔)
SECRET_CONTENT = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),               # AWS access key
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*['\"][^'\"]{8,}"),
)
ALLOWED_BASENAMES = {".gitkeep"}
MAX_FILE_MB = 5.0
CONTENT_SCAN_MAX_KB = 256
TEXT_EXTS = (".py", ".md", ".txt", ".toml", ".cfg", ".ini", ".json",
            ".yml", ".yaml", ".mdc", ".gitignore")

# ── 문서 동기화 규칙 (코드 변경 시 함께 갱신을 권장하는 텍스트) ───────────
# 분석 결과/화면이 바뀌는 코드 (이게 바뀌면 발표 대본·설명 문서도 검토 필요)
CODE_TRIGGER_EXACT = ("app.py",)
CODE_TRIGGER_PREFIX = ("src/",)
# 코드 변경 시 함께 갱신을 검토해야 하는 '서술형' 문서
# (PROGRESS.md 는 auto_commit 이 매번 자동 갱신하므로 제외)
NARRATIVE_DOCS = (
    "발표_대본.md",
    "docs/visualization_strategy.md",
    "docs/research_design.md",
    "docs/project_context.md",
    "README.md",
)


def _git(args: list[str]) -> str:
    """git 명령 실행 (비ASCII 경로 보존)."""
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    if out.returncode != 0 and out.stderr.strip():
        print(f"[precommit] git 경고: {' '.join(args)} -> {out.stderr.strip()}")
    return out.stdout


def candidate_files() -> list[str]:
    """`git add -A` 시 커밋 후보가 되는 (무시되지 않은) 파일 목록."""
    raw = _git(["status", "--porcelain", "-uall"])
    files: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:        # 리네임: 새 경로만
            path = path.split(" -> ", 1)[1]
        path = path.strip().strip('"')
        if path.endswith("/"):    # 디렉터리 표기는 건너뜀
            continue
        files.append(path)
    return files


def check_forbidden(files: list[str]) -> list[str]:
    problems: list[str] = []
    for f in files:
        base = f.rsplit("/", 1)[-1]
        low = f.lower()
        if base in ALLOWED_BASENAMES:
            continue
        if any(f.startswith(d) for d in FORBIDDEN_DIRS):
            problems.append(f"[데이터폴더] {f}")
        if low.endswith(FORBIDDEN_EXTS):
            problems.append(f"[데이터확장자] {f}")
        for pat in SECRET_PATTERNS:
            if pat.search(f):
                problems.append(f"[비밀정보] {f}")
                break
    return problems


def check_sizes(files: list[str]) -> list[str]:
    problems: list[str] = []
    for f in files:
        p = PROJECT_ROOT / f
        if p.is_file():
            mb = p.stat().st_size / (1024 * 1024)
            if mb > MAX_FILE_MB:
                problems.append(f"[대용량 {mb:.1f}MB > {MAX_FILE_MB}MB] {f}")
    return problems


def check_secret_content(files: list[str]) -> list[str]:
    problems: list[str] = []
    for f in files:
        if not f.lower().endswith(TEXT_EXTS):
            continue
        p = PROJECT_ROOT / f
        if not p.is_file() or p.stat().st_size > CONTENT_SCAN_MAX_KB * 1024:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in SECRET_CONTENT:
            if pat.search(text):
                problems.append(f"[내용상 비밀정보 의심] {f} ({pat.pattern[:30]}...)")
                break
    return problems


def check_tracked_forbidden() -> list[str]:
    """이미 git 이 '추적 중'인 파일 중 금지 대상이 있는지 검증.

    (과거에 실수로 커밋된 데이터/DB/비밀정보를 잡아낸다.)
    """
    problems: list[str] = []
    tracked = [ln.strip().strip('"')
               for ln in _git(["ls-files"]).splitlines() if ln.strip()]
    for f in tracked:
        base = f.rsplit("/", 1)[-1]
        low = f.lower()
        if base in ALLOWED_BASENAMES:
            continue
        if any(f.startswith(d) for d in FORBIDDEN_DIRS):
            problems.append(f"[추적중 데이터폴더] {f}")
        elif low.endswith(FORBIDDEN_EXTS):
            problems.append(f"[추적중 데이터확장자] {f}")
        else:
            for pat in SECRET_PATTERNS:
                if pat.search(f):
                    problems.append(f"[추적중 비밀정보] {f}")
                    break
    return problems


def check_data_dir_ignored() -> list[str]:
    """data/ 내 실제 데이터 파일이 .gitignore 로 무시되는지 git 으로 검증.

    git check-ignore -q 의 종료코드로 판정한다(0=무시됨, 1=무시 안 됨).
    """
    problems: list[str] = []
    data_dir = PROJECT_ROOT / "data"
    if not data_dir.exists():
        return problems
    real = [p for p in data_dir.rglob("*")
            if p.is_file() and p.name not in ALLOWED_BASENAMES]
    for p in real:
        rel = p.relative_to(PROJECT_ROOT).as_posix()
        proc = subprocess.run(
            ["git", "check-ignore", "-q", rel],
            cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        if proc.returncode != 0:   # 0 이 아니면 무시되지 않음
            problems.append(f"[무시되지 않는 데이터 파일] {rel}")
    return problems


def check_docs_sync(files: list[str]) -> list[str]:
    """코드가 바뀌었는데 관련 서술형 문서/대본이 함께 갱신되지 않았는지 점검.

    하드 실패가 아니라 '경고(주의)'로만 반환한다(사소한 수정까지 막지 않기 위함).
    분석 화면/결과에 영향을 주는 코드(app.py, src/*)가 후보에 있는데
    NARRATIVE_DOCS 중 아무것도 바뀌지 않았다면 검토하라고 알린다.
    """
    def _is_code(f: str) -> bool:
        return (f in CODE_TRIGGER_EXACT
                or any(f.startswith(p) for p in CODE_TRIGGER_PREFIX)) and f.endswith(".py")

    code_changed = [f for f in files if _is_code(f) or f in CODE_TRIGGER_EXACT]
    if not code_changed:
        return []
    docs_changed = [f for f in files if f in NARRATIVE_DOCS]
    if docs_changed:
        return []
    warnings = [
        "코드가 변경되었는데 관련 설명 문서·대본이 함께 갱신되지 않았습니다.",
        f"   변경 코드: {', '.join(code_changed[:6])}"
        + (" 등" if len(code_changed) > 6 else ""),
        "   아래 문서에 반영이 필요한지 검토하세요(불필요하면 무시 가능):",
    ]
    warnings += [f"     - {d}" for d in NARRATIVE_DOCS]
    return warnings


def check_gitignore_sanity() -> list[str]:
    gi = PROJECT_ROOT / ".gitignore"
    if not gi.exists():
        return ["[.gitignore 없음] 데이터 차단 규칙을 먼저 만드세요."]
    text = gi.read_text(encoding="utf-8", errors="ignore")
    needed = ["data/raw/", "data/processed/", "data/db/", "*.csv", "*.sqlite3"]
    missing = [n for n in needed if n not in text]
    return [f"[.gitignore 규칙 누락] {missing}"] if missing else []


def run_checks(verbose: bool = True) -> tuple[bool, list[str]]:
    files = candidate_files()
    problems: list[str] = []
    problems += check_gitignore_sanity()
    problems += check_forbidden(files)
    problems += check_sizes(files)
    problems += check_secret_content(files)
    problems += check_tracked_forbidden()
    problems += check_data_dir_ignored()

    warnings = check_docs_sync(files)  # 경고(커밋 차단 아님)

    if verbose:
        print("=" * 60)
        print("[precommit] 커밋 후보 파일 점검")
        print("=" * 60)
        if files:
            for f in files:
                print(f"  + {f}")
        else:
            print("  (커밋할 변경 없음)")
        print("-" * 60)
        if warnings:
            print("[precommit] [주의] 문서 동기화 점검")
            for w in warnings:
                print(f"   {w}")
            print("-" * 60)
        if problems:
            print(f"[precommit] [FAIL] 위반 {len(problems)}건 - 커밋 금지")
            for p in problems:
                print(f"   {p}")
        else:
            print("[precommit] [OK] 안전: GitHub 업로드 금지 대상 없음")
        print("=" * 60)
    return (len(problems) == 0), problems


if __name__ == "__main__":
    ok, _ = run_checks()
    sys.exit(0 if ok else 1)
