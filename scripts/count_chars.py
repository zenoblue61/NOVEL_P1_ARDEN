#!/usr/bin/env python3
"""회차 원고의 본문 글자 수를 센다 (공백 포함, 제목 줄 제외).

사용법:
  python3 scripts/count_chars.py episodes/ep001.md [episodes/ep002.md ...]
  python3 scripts/count_chars.py --all

출력: 파일명, 본문 글자 수(공백 포함), 공백 제외 글자 수, 대사 비율(큰따옴표 안 글자 / 본문), 줄표(U+2014/2015) 개수, 상태창 박스 수.
목표: 본문 공백 포함 5,000~5,500자.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPISODES = ROOT / "episodes"


def analyze(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    # 제목 줄(# 제N화. ...) 제거
    body_lines = lines[1:] if lines and lines[0].startswith("#") else lines
    body = "\n".join(body_lines).strip()
    # 줄바꿈은 글자 수에서 제외, 그 외 공백은 포함
    body_flat = body.replace("\n", "")
    total = len(body_flat)
    no_space = len(re.sub(r"\s", "", body_flat))
    dialogue = sum(len(m) for m in re.findall(r"[\"“]([^\"”]*)[\"”]", body))
    ratio = (dialogue / total * 100) if total else 0.0
    dashes = body.count(chr(0x2014)) + body.count(chr(0x2015))
    boxes = len(re.findall(r"^\[감정\]", body, flags=re.M))
    ok = 5000 <= total <= 5500
    return total, no_space, ratio, dashes, boxes, ok


def main(argv):
    if "--all" in argv:
        paths = sorted(EPISODES.glob("ep*.md"))
    else:
        paths = [Path(p) for p in argv[1:]]
    if not paths:
        print(__doc__)
        return 1
    print(f"{'file':<18}{'본문(공백포함)':>14}{'공백제외':>10}{'대사%':>8}{'줄표':>6}{'상태창':>8}  판정")
    for p in paths:
        total, no_space, ratio, dashes, boxes, ok = analyze(p)
        verdict = "OK" if ok else ("짧음" if total < 5000 else "김")
        if dashes:
            verdict += " 줄표!"
        if boxes > 3:
            verdict += " 상태창>3!"
        print(f"{p.name:<18}{total:>14,}{no_space:>10,}{ratio:>7.1f}%{dashes:>6}{boxes:>8}  {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
