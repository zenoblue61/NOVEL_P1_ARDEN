#!/usr/bin/env python3
"""회차 집필에 필요한 설정 조각만 묶어 출력한다.

사용법:
  python scripts/extract_context.py --ep 12
  python scripts/extract_context.py --ep 12 --chars 가렌,이렌 --invent 2 --world 2.4,2.5

출력 순서: current_state → progress 최근 5행 → 직전 1~2화 → 해당 아크 절(06)
          → 문체 규칙(07) → 이번 화 복선 행(08) → [선택] 인물 행(04) / 발명 항목(05) / 세계관 절(02)
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTING = ROOT / "setting"
EPISODES = ROOT / "episodes"
TRACKER = ROOT / "tracker" / "progress.md"

# 아크 경계. 2·3아크 구간이 확정되면 여기만 고친다.
ARCS = [
    (1, 40, "1아크"),
    (41, 160, "2아크"),
    (161, 280, "3아크"),
]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def section(text: str, heading_pattern: str, level: int = 2) -> str:
    """heading_pattern(정규식)에 맞는 제목부터 같은 등급 이하 다음 제목 전까지 반환."""
    lines = text.splitlines()
    out, grab = [], False
    mark = "#" * level + " "
    for line in lines:
        if line.startswith(mark) and re.search(heading_pattern, line):
            grab = True
            out.append(line)
            continue
        if grab and re.match(r"^#{1,%d} " % level, line):
            break
        if grab:
            out.append(line)
    return "\n".join(out).strip()


def arc_of(ep: int) -> str:
    for lo, hi, name in ARCS:
        if lo <= ep <= hi:
            return name
    return "3아크"


def range_hits(cell: str, ep: int) -> bool:
    """'6~10화', '30화 전후', '1아크' 같은 셀이 회차 ep를 포함하는지."""
    for a, b in re.findall(r"(\d+)\s*[~\-]\s*(\d+)\s*화", cell):
        if int(a) <= ep <= int(b):
            return True
    for a in re.findall(r"(\d+)화 전후", cell):
        if abs(int(a) - ep) <= 2:
            return True
    for a in re.findall(r"(?<![\d~\-])(\d+)화(?! 전후)", cell):
        if int(a) == ep and not re.search(r"\d+\s*[~\-]\s*" + a, cell):
            return True
    return False


def table_rows(text: str, predicate) -> list:
    """마크다운 표에서 predicate(cells)가 참인 행을 헤더와 함께 반환."""
    out, header, sep = [], None, None
    for line in text.splitlines():
        if not line.startswith("|"):
            header, sep = None, None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            header = line
            continue
        if sep is None:
            sep = line
            continue
        if predicate(cells):
            if not out or out[-1][0] != header:
                out.append((header, sep, []))
            out[-1][2].append(line)
    blocks = []
    for h, s, rows in out:
        blocks.append("\n".join([h, s] + rows))
    return blocks


def last_rows(table_text: str, n: int) -> str:
    lines = [l for l in table_text.splitlines() if l.startswith("|")]
    if len(lines) <= 2:
        return "\n".join(lines)
    return "\n".join(lines[:2] + lines[2:][-n:])


def prev_episodes(ep: int, n: int = 2) -> str:
    parts = []
    for k in range(max(1, ep - n), ep):
        p = EPISODES / f"ep{k:03d}.md"
        t = read(p)
        parts.append(f"<!-- {p.name} -->\n{t if t else '(파일 없음)'}")
    return "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, required=True, help="집필할 회차 번호")
    ap.add_argument("--chars", default="", help="등장 인물 이름, 쉼표 구분 (04_인물.md의 ### 제목 일부)")
    ap.add_argument("--invent", default="", help="발명 번호, 쉼표 구분 (05의 5.2 표 # 열)")
    ap.add_argument("--world", default="", help="세계관 절 번호, 쉼표 구분 (예: 2.4,2.5)")
    args = ap.parse_args()
    ep = args.ep

    def emit(title: str, body: str):
        if body.strip():
            print(f"\n\n===== {title} =====\n{body.strip()}")

    emit("setting/current_state.md", read(SETTING / "current_state.md"))

    prog = read(TRACKER)
    emit("tracker/progress.md (회차 기록 최근 5행)", last_rows(section(prog, "회차 기록"), 5))

    emit(f"직전 원고 (ep{ep-2:03d}, ep{ep-1:03d})", prev_episodes(ep))

    arc = arc_of(ep)
    arcs_text = read(SETTING / "06_스토리_아크.md")
    emit(f"06_스토리_아크.md / {arc}", section(arcs_text, arc, level=2))

    emit("07_문체_규칙.md", read(SETTING / "07_문체_규칙.md"))

    fs = read(SETTING / "08_복선_장부.md")
    hits = table_rows(
        section(fs, "8.1"),
        lambda c: len(c) >= 6 and (range_hits(c[4], ep) or range_hits(c[5], ep)),
    )
    emit(f"08_복선_장부.md / {ep}화에 심거나 회수할 행", "\n\n".join(hits) or "(해당 행 없음)")

    if args.chars:
        chars = read(SETTING / "04_인물.md")
        for name in [s.strip() for s in args.chars.split(",") if s.strip()]:
            emit(f"04_인물.md / {name}", section(chars, re.escape(name), level=3))

    if args.invent:
        inv = read(SETTING / "05_마도공학_발명.md")
        emit("05_마도공학_발명.md / 공통 제작 규칙", section(inv, "5.1", level=2))
        nums = {s.strip() for s in args.invent.split(",") if s.strip()}
        rows = table_rows(section(inv, "5.2", level=2), lambda c: c and c[0] in nums)
        emit("05_마도공학_발명.md / 해당 발명", "\n\n".join(rows) or "(해당 행 없음)")

    if args.world:
        world = read(SETTING / "02_세계관_왕국.md")
        for sec in [s.strip() for s in args.world.split(",") if s.strip()]:
            emit(f"02_세계관_왕국.md / {sec}", section(world, re.escape(sec), level=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
