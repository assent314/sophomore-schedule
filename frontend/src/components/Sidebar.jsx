import React, { useMemo, useState } from "react";
import Icon from "../icons.jsx";
import { CATEGORIES, categoryColor } from "../meta.js";
import {
  WEEKDAYS_SHORT,
  addMonths,
  fmtMonthCn,
  monthMatrix,
  parseYmd,
  todayYmd,
  ymd,
} from "../dates.js";

function MiniCalendar({ cursor, onSelect }) {
  const [month, setMonth] = useState(cursor.slice(0, 7) + "-01");
  const cells = useMemo(() => monthMatrix(month), [month]);
  const today = todayYmd();

  return (
    <div className="mini-cal">
      <div className="mini-head">
        <span className="mini-title">{fmtMonthCn(month)}</span>
        <div className="mini-nav">
          <button
            className="icon-btn"
            onClick={() => setMonth(addMonths(month, -1))}
            title="上个月"
          >
            <Icon name="chevronLeft" size={18} />
          </button>
          <button
            className="icon-btn"
            onClick={() => setMonth(addMonths(month, 1))}
            title="下个月"
          >
            <Icon name="chevronRight" size={18} />
          </button>
        </div>
      </div>
      <div className="mini-grid">
        {WEEKDAYS_SHORT.map((d) => (
          <div key={d} className="mini-dow">
            {d}
          </div>
        ))}
        {cells.map((c) => (
          <div
            key={c.date}
            className={[
              "mini-day",
              c.inMonth ? "" : "dim",
              c.date === today ? "today" : "",
              c.date === cursor ? "selected" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => {
              onSelect(c.date);
              setMonth(ymd(parseYmd(c.date)) && c.date);
            }}
            role="button"
          >
            {c.day}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Sidebar({
  cursor,
  setCursor,
  events,
  tasks,
  onToggleTask,
  onAddTask,
  hiddenCats,
  toggleCat,
  onOpenMemory,
  onOpenFeedback,
  onOpenProfile,
  onOpenKnowledge,
  memoryStale,
  onPlanner,
}) {
  const [newTask, setNewTask] = useState("");

  const counts = useMemo(() => {
    const m = {};
    for (const ev of events) m[ev.category] = (m[ev.category] || 0) + 1;
    return m;
  }, [events]);

  const openTasks = tasks.filter((t) => t.status !== "done" && t.status !== "cancelled");

  const submitTask = (e) => {
    e.preventDefault();
    const title = newTask.trim();
    if (!title) return;
    onAddTask(title);
    setNewTask("");
  };

  return (
    <aside className="sidebar">
      <button className="create-btn" onClick={onPlanner}>
        <span className="plus">+</span>
        <span>用一句话排程</span>
      </button>

      <MiniCalendar cursor={cursor} onSelect={setCursor} />

      <div className="side-section">
        <div className="side-section-head">
          <span>我的日历</span>
        </div>
        {CATEGORIES.map((c) => {
          const off = hiddenCats.includes(c.key);
          return (
            <div
              key={c.key}
              className={`side-item ${off ? "off" : ""}`}
              onClick={() => toggleCat(c.key)}
              title={off ? "点击显示" : "点击隐藏"}
            >
              <span className={`check ${off ? "" : "on"}`}>
                <Icon name="check" size={12} strokeWidth={3} />
              </span>
              <span className="dot" style={{ background: c.color }} />
              <span>{c.label}</span>
              <span className="count">{counts[c.key] || ""}</span>
            </div>
          );
        })}
      </div>

      <div className="side-section">
        <div className="side-section-head">
          <span>待办任务</span>
          <span className="count">{openTasks.length}</span>
        </div>
        <form onSubmit={submitTask} style={{ display: "flex", gap: 6, padding: "0 2px 6px" }}>
          <input
            className="input"
            style={{ height: 30, padding: "4px 10px", fontSize: 12 }}
            placeholder="＋ 添加任务，回车保存"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
          />
        </form>
        {openTasks.slice(0, 8).map((t) => (
          <div key={t.id} className="task-row" onClick={() => onToggleTask(t)}>
            <span className="check" style={{ marginTop: 1 }}>
              <Icon name="check" size={12} strokeWidth={3} />
            </span>
            <span>
              {t.title}
              <span className="task-meta">
                {t.estimate_min ? `${t.estimate_min} 分钟` : ""}
                {t.due_date ? ` · 截止 ${t.due_date.slice(5)}` : ""}
                {t.priority <= 2 ? " · 高优先" : ""}
              </span>
            </span>
          </div>
        ))}
        {!openTasks.length ? <div className="hint" style={{ padding: "2px 10px" }}>暂无待办</div> : null}
      </div>

      <div className="side-section">
        <div className="side-section-head">
          <span>学习科学</span>
        </div>
        <div className="side-link" onClick={onOpenFeedback}>
          <Icon name="moon" size={18} /> <span>今日反馈 / 状态</span>
        </div>
        <div className="side-link" onClick={onOpenMemory}>
          <Icon name="book" size={18} />
          <span>近一月记忆</span>
          {memoryStale ? <span className="badge amber">待更新</span> : null}
        </div>
        <div className="side-link" onClick={onOpenKnowledge}>
          <Icon name="zap" size={18} /> <span>排程依据（规则卡）</span>
        </div>
        <div className="side-link" onClick={onOpenProfile}>
          <Icon name="settings" size={18} /> <span>习惯与偏好</span>
        </div>
      </div>

      <div className="side-note">
        提示：先写「今天做什么 + 大概多久」，我会按睡眠、昼夜节律和间隔重复自动切块。
      </div>
    </aside>
  );
}
