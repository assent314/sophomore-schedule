import React from "react";
import Icon from "../icons.jsx";

const VIEWS = [
  { key: "day", label: "日" },
  { key: "week", label: "周" },
  { key: "month", label: "月" },
  { key: "stats", label: "统计" },
];

export default function TopBar({
  view,
  setView,
  title,
  titleSub,
  onPrev,
  onNext,
  onToday,
  onPlanner,
  onFeedback,
  onOpenMemory,
  onOpenProfile,
  search,
  setSearch,
}) {
  return (
    <div className="topbar">
      <div className="topbar-left">
        <div className="logo">
          <span className="logo-mark">
            <Icon name="calendar" size={20} strokeWidth={2} />
          </span>
          <span className="logo-text">日程规划</span>
        </div>
        <button className="today-btn" onClick={onToday} title="回到今天">
          今天
        </button>
        <div className="nav-arrows">
          <button className="icon-btn" onClick={onPrev} title="上一个">
            <Icon name="chevronLeft" />
          </button>
          <button className="icon-btn" onClick={onNext} title="下一个">
            <Icon name="chevronRight" />
          </button>
        </div>
        <div className="title-block">
          <span className="title-main">{title}</span>
          {titleSub ? <span className="title-sub">{titleSub}</span> : null}
        </div>
      </div>
      <div className="topbar-spacer" />
      <div className="topbar-right">
        <div className="search-box">
          <Icon name="search" size={18} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索日程"
            aria-label="搜索日程"
          />
          {search ? (
            <button className="icon-btn" style={{ width: 24, height: 24 }} onClick={() => setSearch("")}>
              <Icon name="close" size={16} />
            </button>
          ) : null}
        </div>
        <div className="view-switch">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              className={view === v.key ? "active" : ""}
              onClick={() => setView(v.key)}
            >
              {v.label}
            </button>
          ))}
        </div>
        <button className="icon-btn" onClick={onFeedback} title="填写今日反馈（睡眠/精力）">
          <Icon name="moon" />
        </button>
        <button className="icon-btn" onClick={onOpenMemory} title="近一月记忆">
          <Icon name="book" />
        </button>
        <button className="icon-btn" onClick={onOpenProfile} title="习惯与设置">
          <Icon name="settings" />
        </button>
        <button className="btn btn-primary" onClick={onPlanner}>
          <Icon name="sparkles" size={18} />
          <span className="btn-label">规划今日</span>
        </button>
      </div>
    </div>
  );
}
