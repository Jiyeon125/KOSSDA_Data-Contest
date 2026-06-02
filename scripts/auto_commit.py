# -*- coding: utf-8 -*-
"""안전점검 통과 시에만 커밋하고 PROGRESS.md 로그를 갱신하는 자동화.

흐름:
    1) PROGRESS.md '커밋 로그' 표에 (시각/메시지/프롬프트) 한 줄 추가
    2) scripts/precommit_check.run_checks() 로 GitHub 업로드 안전점검
    3) 통과 + 변경 있음 일 때만 git add -A && git commit
    4) 위반/오류 시 커밋하지 않고 종료(비0)

사용:
    python scripts/auto_commit.py -m "feat: 청년삶 2024 분석 전처리" \
        --prompt "문서 기반 전처리 코드 작성 + 자동 커밋 점검"
    python scripts/auto_commit.py -m "..." --check-only   # 점검만(커밋X)

원격(push)은 하지 않는다. 푸시는 사용자가 직접 수행한다.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.precommit_check import run_checks  # noqa: E402

PROGRESS = PROJECT_ROOT / "PROGRESS.md"
LOG_MARKER = "<!-- AUTO-LOG:"
KST = timezone(timedelta(hours=9))


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8",
    )


def has_changes() -> bool:
    return bool(_git(["status", "--porcelain", "-uall"]).stdout.strip())


def append_log(message: str, prompt: str) -> bool:
    """PROGRESS.md 의 자동 로그 표에 한 줄 추가한다."""
    if not PROGRESS.exists():
        print("[auto_commit] PROGRESS.md 가 없어 로그를 건너뜁니다.")
        return False
    ts = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    safe_msg = message.replace("|", "/").strip()
    safe_prompt = (prompt or "-").replace("|", "/").replace("\n", " ").strip()
    row = f"| {ts} | {safe_msg} | {safe_prompt} |\n"

    lines = PROGRESS.read_text(encoding="utf-8").splitlines(keepends=True)
    out, inserted = [], False
    for i, line in enumerate(lines):
        out.append(line)
        # 헤더 구분줄(| --- | --- | --- |) 다음에 새 행을 삽입
        if (not inserted and line.lstrip().startswith("| ---")
                and i >= 1 and lines[i - 1].lstrip().startswith("| 시각")):
            out.append(row)
            inserted = True
    if not inserted:           # 표를 못 찾으면 맨 끝에 추가
        out.append(row)
    PROGRESS.write_text("".join(out), encoding="utf-8")
    print(f"[auto_commit] 로그 추가: {ts} | {safe_msg}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="안전점검 후 커밋 + 로그 갱신")
    ap.add_argument("-m", "--message", required=True, help="커밋 메시지")
    ap.add_argument("--prompt", default="", help="이번 작업의 프롬프트 요약")
    ap.add_argument("--check-only", action="store_true",
                    help="안전점검만 수행하고 커밋하지 않음")
    args = ap.parse_args()

    # 1) 로그 먼저 갱신(이번 커밋에 함께 포함)
    if not args.check_only:
        append_log(args.message, args.prompt)

    # 2) 안전점검
    ok, problems = run_checks(verbose=True)
    if not ok:
        print("[auto_commit] [STOP] 안전점검 실패 -> 커밋하지 않습니다.")
        return 1

    if args.check_only:
        print("[auto_commit] 점검만 수행(--check-only). 커밋하지 않습니다.")
        return 0

    if not has_changes():
        print("[auto_commit] 변경 사항이 없어 커밋하지 않습니다.")
        return 0

    # 3) 스테이징 + 커밋 (push 안 함)
    add = _git(["add", "-A"])
    if add.returncode != 0:
        print(f"[auto_commit] git add 실패: {add.stderr.strip()}")
        return 1
    commit = _git(["commit", "-m", args.message])
    if commit.returncode != 0:
        print(f"[auto_commit] git commit 실패: {commit.stderr.strip() or commit.stdout.strip()}")
        return 1
    print(commit.stdout.strip())
    head = _git(["rev-parse", "--short", "HEAD"]).stdout.strip()
    print(f"[auto_commit] [OK] 커밋 완료: {head} (원격 push 는 수동)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
