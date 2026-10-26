"""自然语言的规则化解析（离线兜底）。

LLM 可用时以 LLM 抽取为准；此模块用于：
1. 没有 API Key / 调用失败时先跑通流程；
2. 给 LLM 的输入做预处理（切分语句、预判耗时与类别）；
3. 把用户反馈里的零散描述粗分类。
"""

from __future__ import annotations

import re

_CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

_SPLIT_RE = re.compile(r"[。；;\n]+|，然后|,然后|然后")
_HOUR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:个)?\s*(?:小时|h|H|hour)")
_HALF_HOUR_RE = re.compile(r"[半个]?\s*(?:个)?\s*半小时")
_MIN_RE = re.compile(r"(\d+)\s*(?:分钟|min|mins|m\b)")

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "study": ["复习", "学习", "背", "单词", "刷题", "看书", "阅读", "论文", "课", "作业", "考试", "prep",
              "写论文", "实验", "笔记", "预习", "网课", "听课", "patent", "文献"],
    "work": ["工作", "项目", "会议", "汇报", "写代码", "开发", "debug", "上线", "需求", "客户", "报告", "ppt",
             "原型", "测试", "部署", "面试", "实习"],
    "exercise": ["跑步", "健身", "运动", "瑜伽", "游泳", "骑车", "散步", "拉伸", "训练", "打球", "步行"],
    "life": ["吃饭", "午饭", "晚饭", "早饭", "买菜", "做饭", "打扫", "洗澡", "洗衣", "购物", "取快递", "缴费",
             "看牙", "看病", "理发"],
    "admin": ["回邮件", "回消息", "填表", "报销", "整理", "归档", "报名", "打印", "签字", "预约", "打电话"],
    "rest": ["睡", "午睡", "小睡", "休息", "冥想", "放松", "发呆"],
    "social": ["见", "约", "聚餐", "朋友", "家人", "电话", "生日", "聚会"],
}

DEEP_KEYWORDS = ["论文", "写", "推导", "编程", "写代码", "复习", "刷题", "数学", "算法", "实验", "设计", "考试"]
SHALLOW_KEYWORDS = ["整理", "回消息", "回邮件", "填表", "打印", "买菜", "打扫", "归档", "缴费", "预约", "打电话"]


def cn_num(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    if token in _CN_NUM:
        return _CN_NUM[token]
    return None


def parse_duration_min(text: str) -> int | None:
    """从一句中文里抽出预估耗时（分钟）。"""
    m = _HOUR_RE.search(text)
    if m:
        return int(round(float(m.group(1)) * 60))
    if _HALF_HOUR_RE.search(text):
        return 30
    m = _MIN_RE.search(text)
    if m:
        return int(m.group(1))
    m = re.search(r"([一两二三四五六七八九十])\s*小时", text)
    if m:
        n = cn_num(m.group(1))
        if n:
            return n * 60
    return None


def detect_category(text: str) -> str:
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in text for k in kws):
            return cat
    return "study"


def detect_cognitive(text: str) -> str:
    cat = detect_category(text)
    if cat == "exercise":
        return "physical"
    if cat == "rest":
        return "rest"
    if cat == "social":
        return "social"
    if any(k in text for k in SHALLOW_KEYWORDS):
        return "shallow"
    if any(k in text for k in DEEP_KEYWORDS):
        return "deep"
    return "deep" if cat in {"study", "work"} else "shallow"


def split_statements(text: str) -> list[str]:
    parts = [p.strip(" ，,、\t") for p in _SPLIT_RE.split(text or "")]
    return [p for p in parts if len(p) >= 2]


def parse_tasks_offline(text: str) -> list[dict]:
    """规则化抽取任务列表。返回 [{title, estimate_min, category, cognitive_type, priority, notes}]"""
    tasks: list[dict] = []
    for stmt in split_statements(text):
        est = parse_duration_min(stmt) or 45
        cat = detect_category(stmt)
        cog = detect_cognitive(stmt)
        priority = 2 if "重要" in stmt or "必须" in stmt or "截止" in stmt else 3
        energy = "high" if cog == "deep" else ("medium" if cog == "shallow" else "low")
        title = re.sub(r"\s*(\d+(?:\.\d+)?\s*(?:小时|分钟|h|min)|大约|大概)\s*", "", stmt).strip(" ，,、")
        title = title or stmt
        tasks.append(
            {
                "title": title[:100],
                "estimate_min": max(10, min(est, 240)),
                "category": cat,
                "cognitive_type": cog,
                "energy_demand": energy,
                "priority": priority,
                "notes": stmt if title != stmt else "",
                "project": "",
                "due_date": None,
                "tags": [],
            }
        )
    return tasks


def parse_feedback_offline(text: str) -> dict:
    """从一句反馈里粗抽睡眠/精力/情绪。"""
    out: dict = {}
    m = re.search(r"睡[了眠]?\s*(\d+(?:\.\d+)?)\s*(?:个)?\s*小时", text)
    if m:
        out["sleep_hours"] = float(m.group(1))
    m = re.search(r"(\d{1,2})\s*点\s*[睡起]", text)
    for key, words in (
        ("energy_morning", ["早上", "上午"]),
        ("energy_afternoon", ["下午"]),
        ("energy_evening", ["晚上", "傍晚"]),
    ):
        for w in words:
            if w in text:
                m2 = re.search(rf"{w}[^。，,]{{0,12}}?(\d)\s*分", text)
                if m2:
                    out[key] = int(m2.group(1))
    if any(k in text for k in ["困", "累", "疲惫", "没精神", "低效"]):
        out.setdefault("mood", 2)
    return out
