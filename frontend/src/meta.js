export const CATEGORIES = [
  { key: "study", label: "学习", color: "var(--cat-study)" },
  { key: "work", label: "工作", color: "var(--cat-work)" },
  { key: "exercise", label: "运动", color: "var(--cat-exercise)" },
  { key: "life", label: "生活", color: "var(--cat-life)" },
  { key: "admin", label: "事务", color: "var(--cat-admin)" },
  { key: "rest", label: "休息", color: "var(--cat-rest)" },
  { key: "social", label: "社交", color: "var(--cat-social)" },
  { key: "fixed", label: "固定安排", color: "var(--cat-fixed)" },
  { key: "meal", label: "用餐", color: "var(--cat-meal)" },
];

export const CATEGORY_MAP = Object.fromEntries(CATEGORIES.map((c) => [c.key, c]));

export function categoryColor(key) {
  return (CATEGORY_MAP[key] || CATEGORY_MAP.study).color;
}

export function categoryLabel(key) {
  return (CATEGORY_MAP[key] || CATEGORY_MAP.study).label;
}

export const KIND_LABEL = {
  focus: "深度专注",
  study: "学习",
  admin: "事务",
  exercise: "运动",
  meal: "用餐",
  rest: "休息",
  break: "微休息",
  social: "社交",
  fixed: "固定安排",
  commute: "通勤",
  buffer: "缓冲",
};

export const KIND_CATEGORY = {
  focus: "study",
  study: "study",
  admin: "admin",
  exercise: "exercise",
  meal: "meal",
  rest: "rest",
  break: "rest",
  social: "social",
  fixed: "fixed",
  commute: "life",
  buffer: "admin",
};

export const STATUS_LABEL = {
  planned: "已排入",
  done: "已完成",
  partial: "部分完成",
  skipped: "未完成",
  moved: "已顺延",
};

export const KNOWLEDGE_CATEGORY_LABEL = {
  attention: "注意与专注",
  memory: "记忆与巩固",
  rhythm: "节律与精力",
  motivation: "动机与执行",
  rest: "休息与恢复",
  exercise: "运动与认知",
  environment: "环境与媒介",
};

export const EVIDENCE_LABEL = {
  strong: "强证据",
  moderate: "中等证据",
  emerging: "初步证据",
};

export const ENERGY_PRESETS = {
  morning: [1, 1, 1, 1, 1, 2, 4, 5, 5, 4, 3, 3, 2, 2, 2, 3, 3, 3, 2, 2, 1, 1, 1, 1],
  neutral: [1, 1, 1, 1, 1, 1, 2, 3, 4, 4, 4, 4, 3, 2, 3, 4, 4, 3, 2, 2, 1, 1, 1, 1],
  evening: [1, 1, 1, 1, 1, 1, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 3, 2, 2, 1, 1, 1],
};

export function mdToHtml(md) {
  if (!md) return "";
  const esc = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const inline = (s) =>
    esc(s)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`(.+?)`/g, "<code>$1</code>")
      .replace(/\[(.+?)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
  const lines = md.split("\n");
  const out = [];
  let list = null;
  const flush = () => {
    if (list) {
      out.push(`<ul>${list.join("")}</ul>`);
      list = null;
    }
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flush();
      continue;
    }
    if (line.startsWith("### ")) {
      flush();
      out.push(`<h3>${inline(line.slice(4))}</h3>`);
    } else if (line.startsWith("## ")) {
      flush();
      out.push(`<h2>${inline(line.slice(3))}</h2>`);
    } else if (/^[-*] /.test(line)) {
      if (!list) list = [];
      list.push(`<li>${inline(line.replace(/^[-*] /, ""))}</li>`);
    } else {
      flush();
      out.push(`<p>${inline(line)}</p>`);
    }
  }
  flush();
  return out.join("");
}
