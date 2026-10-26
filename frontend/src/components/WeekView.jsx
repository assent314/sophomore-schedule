import React, { useEffect, useMemo, useRef } from "react";
import Icon from "../icons.jsx";
import { categoryColor, KIND_LABEL, STATUS_LABEL } from "../meta.js";
import {
  WEEKDAYS,
  minutesOf,
  todayYmd,
  weekdayIndex,
  parseYmd,
  isoFromParts,
  fmtDuration,
  fmtHours,
} from "../dates.js";

const HOUR_H = 60;
const SNAP = 5;
// 过短的方块（如 10 分钟微休息）不要被压成固定最小高度，否则会和下面的方块重叠
const blockH = (s, e) => Math.max(((e - s) / 60) * HOUR_H, 10);

function layoutEvents(list) {
  const evs = list
    .map((e) => {
      const s = minutesOf(e.start);
      const en = minutesOf(e.end);
      return { ...e, _s: s, _e: Math.max(en, s + 10) };
    })
    .sort((a, b) => a._s - b._s || a._e - b._e);

  const groups = [];
  let cluster = [];
  let clusterEnd = -1;
  for (const ev of evs) {
    if (ev._s >= clusterEnd) {
      if (cluster.length) groups.push(cluster);
      cluster = [ev];
      clusterEnd = ev._e;
    } else {
      cluster.push(ev);
      clusterEnd = Math.max(clusterEnd, ev._e);
    }
  }
  if (cluster.length) groups.push(cluster);

  const out = [];
  for (const g of groups) {
    const colEnds = [];
    for (const ev of g) {
      let idx = colEnds.findIndex((end) => end <= ev._s);
      if (idx === -1) {
        idx = colEnds.length;
        colEnds.push(ev._e);
      } else {
        colEnds[idx] = ev._e;
      }
      ev._col = idx;
    }
    for (const ev of g) out.push({ ...ev, _cols: colEnds.length });
  }
  return out;
}

function EventBlock({ ev, onEventClick, onStartMove, onStartResize, suppressRef }) {
  const top = (ev._s / 60) * HOUR_H;
  const height = blockH(ev._s, ev._e);
  const widthPct = 100 / ev._cols;
  const showTitle = height >= 16;
  const showTime = height >= 30;
  const showRule = height >= 56 && ev.reason;
  const compact = height < 26;
  const statusClass =
    ev.status === "done" ? "status-done" : ev.status === "skipped" ? "status-skipped" : "";
  return (
    <div
      data-id={ev.id}
      className={`event-block ${ev.locked ? "locked" : ""} ${compact ? "compact" : ""} ${statusClass}`}
      style={{
        top,
        height,
        left: `calc(${widthPct * ev._col}% + 2px)`,
        width: `calc(${widthPct}% - 4px)`,
        background: categoryColor(ev.category),
      }}
      onPointerDown={(evt) => {
        if (evt.pointerType === "touch") return;
        if (evt.button !== 0) return;
        onStartMove(evt, ev);
      }}
      onClick={(e2) => {
        e2.stopPropagation();
        if (suppressRef.current && Date.now() - suppressRef.current < 350) return;
        onEventClick(ev);
      }}
      title={`${ev.title} ${ev.start.slice(11, 16)}–${ev.end.slice(11, 16)}（可拖动移动 / 拖底边调整时长）${
        ev.reason ? `\n依据：${ev.reason}` : ""
      }`}
    >
      <div className={`ev-title ${ev.status === "done" ? "done" : ""}`}>{showTitle ? ev.title : ""}</div>
      {showTime ? (
        <div className="ev-time">
          {ev.start.slice(11, 16)} – {ev.end.slice(11, 16)}
          {ev.status !== "planned" ? ` · ${STATUS_LABEL[ev.status] || ""}` : ""}
        </div>
      ) : null}
      {showRule ? <div className="ev-rule">{ev.reason}</div> : null}
      {!ev.locked ? (
        <div
          className="ev-resize"
          title="拖动调整时长"
          onPointerDown={(evt) => {
            if (evt.pointerType === "touch") return;
            if (evt.button !== 0) return;
            onStartResize(evt, ev);
          }}
        />
      ) : null}
    </div>
  );
}

export default function WeekView({
  days,
  eventsByDate,
  onEventClick,
  onSlotClick,
  onEventMoved,
  hiddenCats,
  scrollHour = 7,
}) {
  const scrollRef = useRef(null);
  const dragRef = useRef(null);
  const suppressRef = useRef(0);
  const daysRef = useRef(days);
  const movedRef = useRef(onEventMoved);
  daysRef.current = days;
  movedRef.current = onEventMoved;

  const today = todayYmd();
  const now = new Date();
  const nowMin = now.getHours() * 60 + now.getMinutes();

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || el.dataset.scrolled) return;
    const includesToday = days.includes(today);
    const target = includesToday ? Math.max(0, nowMin - 150) : Math.max(0, (scrollHour - 1) * HOUR_H);
    el.scrollTop = target;
    el.dataset.scrolled = "1";
  }, [scrollHour, days, nowMin, today]);

  const byDay = useMemo(() => {
    const map = {};
    for (const d of days) {
      const list = (eventsByDate[d] || []).filter((e) => !hiddenCats.includes(e.category));
      map[d] = layoutEvents(list);
    }
    return map;
  }, [days, eventsByDate, hiddenCats]);

  const single = days.length === 1;

  const startDrag = (evt, ev, mode) => {
    if (ev.locked) return;
    const el = evt.currentTarget;
    const gridEl = el.closest(".days-grid");
    if (!gridEl) return;
    evt.preventDefault();
    evt.stopPropagation();
    const gridRect = gridEl.getBoundingClientRect();
    const list = daysRef.current;
    const colW = gridRect.width / list.length;
    const s0 = minutesOf(ev.start);
    const e0 = Math.max(minutesOf(ev.end), s0 + 10);
    const dayIdx = list.indexOf(ev.start.slice(0, 10));
    const st = {
      el,
      ev,
      mode,
      s: s0,
      e: e0,
      s0,
      e0,
      day: ev.start.slice(0, 10),
      origIdx: dayIdx === -1 ? 0 : dayIdx,
      idx: dayIdx === -1 ? 0 : dayIdx,
      startY: evt.clientY,
      startX: evt.clientX,
      gridRect,
      colW,
      moved: false,
    };
    dragRef.current = st;
    el.classList.add("dragging");
  };

  useEffect(() => {
    const render = (d) => {
      const el = d.el;
      el.style.top = `${(d.s / 60) * HOUR_H}px`;
      el.style.height = `${blockH(d.s, d.e)}px`;
      el.style.transform = `translateX(${(d.idx - d.origIdx) * d.colW}px)`;
      const label = el.querySelector(".ev-time");
      const fmt = (m) =>
        `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
      if (label) label.textContent = `${fmt(d.s)} – ${fmt(d.e)}`;
    };
    const onMove = (evt) => {
      const d = dragRef.current;
      if (!d) return;
      const dy = evt.clientY - d.startY;
      const deltaMin = Math.round(dy / SNAP) * SNAP;
      if (Math.abs(dy) > 3 || Math.abs(evt.clientX - d.startX) > 3) d.moved = true;
      const list = daysRef.current;
      if (d.mode === "move") {
        const dur = d.e0 - d.s0;
        d.s = Math.min(Math.max(d.s0 + deltaMin, 0), 24 * 60 - dur);
        d.e = d.s + dur;
        const col = Math.floor((evt.clientX - d.gridRect.left) / d.colW);
        d.idx = Math.min(Math.max(col, 0), list.length - 1);
        d.day = list[d.idx];
      } else {
        d.e = Math.min(Math.max(d.e0 + deltaMin, d.s0 + 15), 24 * 60);
      }
      render(d);
    };
    const finish = (cancelled = false) => {
      const d = dragRef.current;
      dragRef.current = null;
      if (!d) return;
      d.el.classList.remove("dragging");
      d.el.style.zIndex = "";
      d.el.style.transform = "";
      const s = Math.round(d.s / SNAP) * SNAP;
      const e = Math.round(d.e / SNAP) * SNAP;
      const changed = !cancelled && d.moved && (s !== d.s0 || e !== d.e0 || d.day !== d.ev.start.slice(0, 10));
      if (d.moved) suppressRef.current = Date.now();
      if (!changed) {
        d.el.style.top = `${(d.s0 / 60) * HOUR_H}px`;
        d.el.style.height = `${blockH(d.s0, d.e0)}px`;
        return;
      }
      if (movedRef.current) {
        movedRef.current(d.ev, {
          start: isoFromParts(d.day, s),
          end: isoFromParts(d.day, e),
        });
      }
    };
    window.addEventListener("pointermove", onMove);
    const onUp = () => finish(false);
    const onCancel = () => finish(true);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onCancel);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onCancel);
    };
  }, []);

  const handleColumnClick = (day, e) => {
    if (suppressRef.current && Date.now() - suppressRef.current < 350) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const minutes = Math.max(0, Math.min(23 * 60 + 30, Math.round(y / HOUR_H * 60 / 15) * 15));
    onSlotClick(day, minutes);
  };

  return (
    <>
      <div className={`calendar-scroll ${single ? "single-day" : "seven-day"}`} ref={scrollRef}>
        <div className="calendar-head sticky">
          <div className="week-head-row">
            {days.map((d) => {
              const isToday = d === today;
              const parsed = parseYmd(d);
              const dayMin = (eventsByDate[d] || [])
                .filter((e) => !hiddenCats.includes(e.category))
                .reduce((acc, e) => acc + Math.max(0, minutesOf(e.end) - minutesOf(e.start)), 0);
              return (
                <div key={d} className={`week-head-cell ${isToday ? "today" : ""}`}>
                  <div className={`dow-label ${isToday ? "today" : ""}`}>
                    {WEEKDAYS[weekdayIndex(d)]}
                  </div>
                  <div className="day-num-row">
                    <span className="day-num">{parsed.getDate()}</span>
                  </div>
                  <div className="slot-count">{dayMin ? `${fmtHours(dayMin)}h` : ""}</div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="time-grid">
          <div className="time-labels">
            {Array.from({ length: 24 }).map((_, h) => (
              <div key={h} className="time-label">
                <span>{h === 0 ? "" : `${h}:00`}</span>
              </div>
            ))}
          </div>
          <div className="days-grid">
            {days.map((d) => {
              const isToday = d === today;
              return (
                <div
                  key={d}
                  className={`day-col ${isToday ? "today" : ""}`}
                  onClick={(e) => handleColumnClick(d, e)}
                >
                  {Array.from({ length: 24 }).map((_, h) => (
                    <div key={h} className="hour-row" />
                  ))}
                  {isToday ? (
                    <div className="now-line" style={{ top: (nowMin / 60) * HOUR_H }} />
                  ) : null}
                  {(byDay[d] || []).map((ev) => (
                    <EventBlock
                      key={ev.id}
                      ev={ev}
                      onEventClick={onEventClick}
                      onStartMove={(e2, ev2) => startDrag(e2, ev2, "move")}
                      onStartResize={(e2, ev2) => startDrag(e2, ev2, "resize")}
                      suppressRef={suppressRef}
                    />
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}

export { HOUR_H, EventBlock };
