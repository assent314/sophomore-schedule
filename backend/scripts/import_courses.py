"""把教务系统导出的 PDF 课表导入日历（只展示、不锁定）。

支持两种来源：
1) 个人课表（如「学生课表.pdf」）：按周次×星期展开整学期课程；
2) 微专业授课安排（如「微专业2026-2027-1授课安排1.pdf」）：表格里直接给了日期与上午/下午/全天。

用法：
    # 先看解析结果，不写库
    python backend/scripts/import_courses.py --student-pdf "C:\\...\\课表.pdf" --dry-run
    # 确认后导入（默认只导入今天及以后，避免历史统计被灌满）
    python backend/scripts/import_courses.py --student-pdf "C:\\...\\课表.pdf" --micro-pdf "C:\\...\\微专业.pdf"

说明：
- 事件打标签 plan_run_id="course-import"，重复导入会先删掉旧标签事件，不会重复堆叠；
- 事件 category/kind 都是 fixed（日历上显示成紫色的「固定安排」），locked=False 所以仍可拖动；
- 课表导入事件不计入完成率统计（见 backend/app/stats.py 的 exclude_course_import），
  但 AI 排程时仍然把它们当作「已占用的时间」；
- 节次对应的钟点是学校作息，默认值见 PERIOD_TIMES，如与实际不符可改这里或用 --period-json 覆盖。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, time, timedelta
from pathlib import Path

try:
    import pypdf
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖：先 pip install pypdf")

COURSE_TAG = "course-import"
TERM_START_DEFAULT = date(2026, 9, 21)  # 2026-2027 学年第 1 学期的第 1 周周一

# 个人课表里 7 天课程列的 x 坐标（PDF 文本坐标）
COURSE_COL_X = [104.1, 207.9, 311.8, 415.6, 519.5, 623.3, 727.1]
FONT_TITLE = 9.0
FONT_META = 8.0

# 节次 -> (开始, 结束)，浙工大教务处《学生作息时间表》
# 来源：http://www.jwc.zjut.edu.cn/2013/1103/c249a16511/page.htm
# 1-9 节在白天，10-12 节在晚上；第 8-9 节即 15:25-17:05。
PERIOD_TIMES = {
    1: ("08:00", "08:45"),
    2: ("08:55", "09:40"),
    3: ("09:55", "10:40"),
    4: ("10:50", "11:35"),
    5: ("11:45", "12:30"),
    6: ("13:30", "14:15"),
    7: ("14:25", "15:10"),
    8: ("15:25", "16:10"),
    9: ("16:20", "17:05"),
    10: ("18:30", "19:15"),
    11: ("19:25", "20:10"),
    12: ("20:20", "21:05"),
}

# 微专业：上午/下午/全天的起止（PDF 只给开始时间 9:00 / 13:30）
SLOT_TIMES = {
    "上午": ("09:00", "11:30"),
    "下午": ("13:30", "16:00"),
    "全天": ("09:00", "16:30"),
}

FLAG_CHARS = "☆★■◆◇●○△▲□"


# --------------------------------------------------------------------------- PDF 文本
def _collect(out: list, text: str, tm, font_size: float) -> None:
    text = (text or "").strip()
    if text:
        out.append((round(tm[4], 1), round(tm[5], 1), round(font_size, 1), text))


def _page_frags(pdf_path: Path) -> list[list[tuple[float, float, float, str]]]:
    reader = pypdf.PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        frags: list[tuple[float, float, float, str]] = []
        page.extract_text(visitor_text=lambda t, cm, tm, fd, fs: _collect(frags, t, tm, fs))
        pages.append(frags)
    return pages


def _nearest_col(x: float, tol: float = 8.0) -> int | None:
    best = None
    for idx, cx in enumerate(COURSE_COL_X):
        dist = abs(x - cx)
        if dist <= tol and (best is None or dist < best[0]):
            best = (dist, idx)
    return None if best is None else best[1]


# --------------------------------------------------------------------------- 个人课表
def parse_student_pdf(pdf_path: Path) -> list[dict]:
    """解析个人课表：返回 [{weekday, title, meta}]，weekday 1=周一。"""
    courses: list[dict] = []
    for frags in _page_frags(pdf_path):
        by_col: dict[int, list[tuple[float, float, str]]] = {}
        for x, y, fs, text in frags:
            col = _nearest_col(x)
            if col is None or fs not in (FONT_TITLE, FONT_META):
                continue
            by_col.setdefault(col, []).append((y, fs, text))
        for col, items in by_col.items():
            items.sort(key=lambda it: -it[0])  # 从上到下
            cur: dict | None = None
            prev_fs: float | None = None
            for _y, fs, text in items:
                if fs == FONT_TITLE:
                    if cur is None or prev_fs == FONT_META:
                        if cur:
                            courses.append(cur)
                        cur = {"weekday": col + 1, "title": text, "meta": ""}
                    else:  # 换行折断的课程名
                        cur["title"] += text
                else:
                    if cur is not None:
                        cur["meta"] += text
                prev_fs = fs
            if cur:
                courses.append(cur)
    return courses


def parse_weeks(spec: str) -> list[int]:
    """'1-16周' / '1-3周(单),4-16周' / '第3周' / '3-10周' -> 周次列表。"""
    weeks: set[int] = set()
    for part in re.split(r"[,，、]", spec or ""):
        part = part.strip()
        if not part:
            continue
        odd = "单" in part
        even = "双" in part
        m = re.search(r"第?(\d+)(?:\s*-\s*(\d+))?\s*周", part)
        if not m:
            continue
        a = int(m.group(1))
        b = int(m.group(2) or a)
        for w in range(a, b + 1):
            if odd and w % 2 == 0:
                continue
            if even and w % 2 == 1:
                continue
            weeks.add(w)
    return sorted(weeks)


def _clean_title(raw: str) -> tuple[str, str]:
    """从「生物信息学◆」这种带类型符号的标题里拆出课程名与符号。"""
    title = raw.strip()
    flag = ""
    while title and title[-1] in FLAG_CHARS:
        flag = title[-1] + flag
        title = title[:-1].strip()
    return title, flag


def _period_runs(j1: int, j2: int) -> list[tuple[str, str]]:
    """把「第 j1-j2 节」拆成连续时间段；课间休息 >30 分钟（午休/晚饭）时拆成多段。"""
    def _dt(hhmm: str) -> datetime:
        return datetime.combine(date(2000, 1, 1), time.fromisoformat(hhmm))

    runs: list[tuple[str, str]] = []
    start = PERIOD_TIMES[j1][0]
    prev_end = PERIOD_TIMES[j1][1]
    for j in range(j1 + 1, j2 + 1):
        if (_dt(PERIOD_TIMES[j][0]) - _dt(prev_end)).total_seconds() > 30 * 60:
            runs.append((start, prev_end))
            start = PERIOD_TIMES[j][0]
        prev_end = PERIOD_TIMES[j][1]
    runs.append((start, prev_end))
    return runs


def expand_student(courses: list[dict], term_start: date, max_week: int) -> list[dict]:
    items: list[dict] = []
    for c in courses:
        meta = c.get("meta") or ""
        if not meta:
            continue
        m = re.search(r"\((\d+)(?:\s*-\s*(\d+))?节\)", meta)
        if not m:
            continue
        j1 = int(m.group(1))
        j2 = int(m.group(2) or j1)
        if j1 not in PERIOD_TIMES or j2 not in PERIOD_TIMES:
            continue
        rest = meta[m.end():]
        wm = re.match(r"([^/]+)/", rest)
        weeks = [w for w in parse_weeks(wm.group(1) if wm else "") if 1 <= w <= max_week]
        if not weeks:
            continue
        title, flag = _clean_title(c["title"])
        if not title:
            continue
        room = re.search(r"/场地:([^/]+)", meta)
        teacher = re.search(r"/教师:([^/]+)", meta)
        klass = re.search(r"/教学班:([^/]+)", meta)
        campus = re.search(r"校区:([^/]+)", meta)
        notes = " · ".join(
            x
            for x in [
                "地点：" + (room.group(1) if room else "未排地点"),
                "教师：" + (teacher.group(1) if teacher else ""),
                "教学班：" + (klass.group(1) if klass else ""),
            ]
            if x and not x.endswith("：")
        )
        runs = _period_runs(j1, j2)
        for w in weeks:
            d = term_start + timedelta(days=(w - 1) * 7 + (c["weekday"] - 1))
            for s_hhmm, e_hhmm in runs:
                start = datetime.combine(d, time.fromisoformat(s_hhmm))
                end = datetime.combine(d, time.fromisoformat(e_hhmm))
                items.append(
                    {
                        "title": title,
                        "notes": notes,
                        "start": start,
                        "end": end,
                        "week": w,
                        "source": "student",
                        "flag": flag,
                        "campus": campus.group(1) if campus else "",
                    }
                )
    return items


# --------------------------------------------------------------------------- 微专业
def parse_micro_pdf(pdf_path: Path) -> list[dict]:
    """解析微专业授课安排表：返回 [{date, slot, course, content, teacher}]。"""
    rows: list[dict] = []
    for frags in _page_frags(pdf_path):
        if not frags:
            continue
        grouped: dict[float, list[tuple[float, str]]] = {}
        for x, y, fs, text in frags:
            if fs < 10:  # 页脚联系人等
                continue
            key = None
            for exist in grouped:
                if abs(exist - y) <= 3.0:
                    key = exist
                    break
            if key is None:
                key = y
                grouped[key] = []
            grouped[key].append((x, text))
        for y in sorted(grouped, reverse=True):
            cells = {"week": "", "date": "", "course": "", "content": "", "teacher": ""}
            for x, text in sorted(grouped[y]):
                if x < 120:
                    cells["week"] += text
                elif x < 235:
                    cells["date"] += text
                elif x < 380:
                    cells["course"] += text
                elif x < 545:
                    cells["content"] += text
                else:
                    cells["teacher"] += text
            rows.append(cells)
    out: list[dict] = []
    for cells in rows:
        dm = re.search(r"(\d{1,2})\.(\d{1,2})", cells["date"])
        if not dm:
            continue
        slot = next((s for s in SLOT_TIMES if s in cells["date"]), None)
        if slot is None:
            slot = next((s for s in SLOT_TIMES if s in cells["week"]), None)
        if slot is None:
            continue
        out.append(
            {
                "month": int(dm.group(1)),
                "day": int(dm.group(2)),
                "slot": slot,
                "title": cells["course"].strip(),
                "content": cells["content"].strip(),
                "teacher": cells["teacher"].strip(),
                "week": cells["week"].strip(),
            }
        )
    return out


def expand_micro(rows: list[dict], year: int) -> list[dict]:
    items: list[dict] = []
    for r in rows:
        try:
            d = date(year, r["month"], r["day"])
        except ValueError:
            continue
        start = datetime.combine(d, time.fromisoformat(SLOT_TIMES[r["slot"]][0]))
        end = datetime.combine(d, time.fromisoformat(SLOT_TIMES[r["slot"]][1]))
        notes = " · ".join(
            x
            for x in [
                "微专业 · " + r["slot"],
                ("内容：" + r["content"]) if r["content"] else "",
                ("教师：" + r["teacher"]) if r["teacher"] else "",
                "地点：莫干山校区生工楼 C406",
            ]
            if x
        )
        items.append(
            {
                "title": r["title"] or "微专业课程",
                "notes": notes,
                "start": start,
                "end": end,
                "source": "micro",
                "flag": "",
                "campus": "莫干山校区",
            }
        )
    return items


# --------------------------------------------------------------------------- API
def _request(method: str, url: str, payload: dict | None = None) -> object:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        return json.loads(body.decode("utf-8")) if body else None


def clear_imported(api: str, start: date, end: date) -> int:
    url = f"{api}/api/events?start={start.isoformat()}&end={end.isoformat()}"
    events = _request("GET", url) or []
    removed = 0
    for ev in events:
        if ev.get("plan_run_id") == COURSE_TAG:
            _request("DELETE", f"{api}/api/events/{ev['id']}")
            removed += 1
    return removed


def post_events(api: str, items: list[dict], dry_run: bool) -> int:
    created = 0
    for it in items:
        payload = {
            "title": it["title"],
            "notes": it["notes"],
            "category": "fixed",
            "kind": "fixed",
            "start": it["start"].isoformat(),
            "end": it["end"].isoformat(),
            "locked": False,
            "reason": "课程表导入",
            "plan_run_id": COURSE_TAG,
        }
        if dry_run:
            print(
                f"  [dry-run] {it['start']:%Y-%m-%d %a %H:%M}-{it['end']:%H:%M} {it['title']} "
                f"({'第%s周' % it['week'] if it.get('week') else it.get('source')})"
            )
        else:
            try:
                _request("POST", f"{api}/api/events", payload)
                created += 1
            except urllib.error.HTTPError as exc:
                print(f"  ! 创建失败 {it['title']}: {exc.code} {exc.read()[:200]}")
        if not dry_run and created % 20 == 0:
            print(f"  …已写入 {created}")
    return created


# --------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="把教务 PDF 课表导入日历")
    ap.add_argument("--student-pdf", default=None, help="个人课表 PDF")
    ap.add_argument("--micro-pdf", default=None, help="微专业授课安排 PDF")
    ap.add_argument("--micro-json", default=None, help="微专业授课安排 JSON（PDF 丢失时的备用输入）")
    ap.add_argument("--api-url", default="http://127.0.0.1:8000", help="后端地址")
    ap.add_argument("--term-start", default=TERM_START_DEFAULT.isoformat(), help="第 1 周周一，YYYY-MM-DD")
    ap.add_argument("--max-week", type=int, default=16, help="最大周次")
    ap.add_argument("--include-past", action="store_true", help="连今天之前的课也导入")
    ap.add_argument("--dry-run", action="store_true", help="只打印解析结果，不写库")
    ap.add_argument("--period-json", default=None, help="自定义节次时间 JSON 文件")
    args = ap.parse_args(argv)

    global PERIOD_TIMES
    if args.period_json:
        PERIOD_TIMES = {int(k): tuple(v) for k, v in json.loads(Path(args.period_json).read_text("utf-8")).items()}

    term_start = date.fromisoformat(args.term_start)
    today = date.today()
    from_date = term_start if args.include_past else today

    items: list[dict] = []
    if args.student_pdf:
        courses = parse_student_pdf(Path(args.student_pdf))
        print(f"个人课表：解析到 {len(courses)} 条课程块")
        items += expand_student(courses, term_start, args.max_week)
    if args.micro_pdf:
        rows = parse_micro_pdf(Path(args.micro_pdf))
        print(f"微专业：解析到 {len(rows)} 条授课安排")
        items += expand_micro(rows, term_start.year)
    if args.micro_json:
        rows = json.loads(Path(args.micro_json).read_text("utf-8"))
        print(f"微专业（JSON）：读到 {len(rows)} 条授课安排")
        items += expand_micro(rows, term_start.year)

    items = [it for it in items if it["start"].date() >= from_date]
    items.sort(key=lambda it: it["start"])
    if not items:
        print("没有需要导入的课程")
        return 0

    print(f"共 {len(items)} 个课次（{items[0]['start']:%Y-%m-%d} ~ {items[-1]['start']:%Y-%m-%d}）")
    if args.dry_run:
        post_events(args.api_url, items, dry_run=True)
        return 0

    end = items[-1]["start"].date()
    removed = clear_imported(args.api_url, from_date, end)
    if removed:
        print(f"已清理旧的课表导入事件 {removed} 个")
    created = post_events(args.api_url, items, dry_run=False)
    print(f"导入完成：新增 {created} 个课表事件（标签 {COURSE_TAG}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
