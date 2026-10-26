export const WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
export const WEEKDAYS_SHORT = ["一", "二", "三", "四", "五", "六", "日"];

const pad = (n) => String(n).padStart(2, "0");

export function ymd(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function parseYmd(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function todayYmd() {
  return ymd(new Date());
}

export function addDays(s, days) {
  const d = parseYmd(s);
  d.setDate(d.getDate() + days);
  return ymd(d);
}

export function addMonths(s, months) {
  const d = parseYmd(s);
  d.setMonth(d.getMonth() + months, 1);
  return ymd(d);
}

export function startOfWeek(s) {
  const d = parseYmd(s);
  const dow = (d.getDay() + 6) % 7; // 0=周一
  d.setDate(d.getDate() - dow);
  return ymd(d);
}

export function weekdayIndex(s) {
  return (parseYmd(s).getDay() + 6) % 7;
}

export function monthMatrix(s) {
  const d = parseYmd(s);
  const first = new Date(d.getFullYear(), d.getMonth(), 1);
  const startDow = (first.getDay() + 6) % 7;
  const start = new Date(first);
  start.setDate(first.getDate() - startDow);
  const daysInMonth = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  const rows = Math.ceil((startDow + daysInMonth) / 7);
  const cells = [];
  for (let i = 0; i < rows * 7; i += 1) {
    const cur = new Date(start);
    cur.setDate(start.getDate() + i);
    cells.push({ date: ymd(cur), day: cur.getDate(), inMonth: cur.getMonth() === d.getMonth() });
  }
  return cells;
}

export function fmtDateCn(s) {
  const d = parseYmd(s);
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`;
}

export function fmtMonthCn(s) {
  const d = parseYmd(s);
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`;
}

export function fmtWeekTitle(s) {
  const start = startOfWeek(s);
  const end = addDays(start, 6);
  const a = parseYmd(start);
  const b = parseYmd(end);
  if (a.getMonth() === b.getMonth()) {
    return `${a.getFullYear()} 年 ${a.getMonth() + 1} 月 ${a.getDate()} – ${b.getDate()} 日`;
  }
  return `${a.getFullYear()} 年 ${a.getMonth() + 1} 月 ${a.getDate()} 日 – ${b.getMonth() + 1} 月 ${b.getDate()} 日`;
}

export function fmtDayTitle(s) {
  const d = parseYmd(s);
  return `${fmtDateCn(s)} · ${WEEKDAYS[weekdayIndex(s)]}`;
}

export function timeOf(iso) {
  return (iso || "").slice(11, 16);
}

export function minutesOf(iso) {
  const t = timeOf(iso);
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

export function durationMin(startIso, endIso) {
  return Math.max(0, minutesOf(endIso) - minutesOf(startIso));
}

export function isoFromParts(dateStr, minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${dateStr}T${pad(h)}:${pad(m)}:00`;
}

export function toDatetimeLocal(iso) {
  return `${iso.slice(0, 10)}T${iso.slice(11, 16)}`;
}

export function fromDatetimeLocal(v) {
  if (!v) return "";
  return v.length === 16 ? `${v}:00` : v;
}

export function fmtDuration(min) {
  if (min == null) return "";
  if (min < 60) return `${min} 分钟`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h} 小时 ${m} 分` : `${h} 小时`;
}

export function fmtHours(min) {
  return `${(min / 60).toFixed(1)}`;
}

export function nowMinutes() {
  const d = new Date();
  return d.getHours() * 60 + d.getMinutes();
}
