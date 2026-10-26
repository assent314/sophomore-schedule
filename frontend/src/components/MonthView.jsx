import React, { useMemo } from "react";
import { categoryColor } from "../meta.js";
import { WEEKDAYS, monthMatrix, parseYmd, todayYmd } from "../dates.js";

const MAX_CHIPS = 3;

export default function MonthView({ cursor, eventsByDate, hiddenCats, onEventClick, onDayClick }) {
  const cells = useMemo(() => monthMatrix(cursor), [cursor]);
  const today = todayYmd();

  const byDate = useMemo(() => {
    const map = {};
    for (const [date, list] of Object.entries(eventsByDate)) {
      map[date] = list.filter((e) => !hiddenCats.includes(e.category));
    }
    return map;
  }, [eventsByDate, hiddenCats]);

  return (
    <>
      <div className="calendar-head" style={{ paddingBottom: 0 }}>
        <div className="month-dow-row">
          {WEEKDAYS.map((d) => (
            <div key={d} className="month-dow">
              {d}
            </div>
          ))}
        </div>
      </div>
      <div className="month-scroll">
        <div className="month-grid">
          {cells.map((c) => {
            const evs = byDate[c.date] || [];
            return (
              <div
                key={c.date}
                className={`month-cell ${c.inMonth ? "" : "dim"} ${c.date === today ? "today" : ""}`}
                onClick={() => onDayClick(c.date)}
              >
                <span className="month-daynum">{c.day}</span>
                {evs.slice(0, MAX_CHIPS).map((ev) => (
                  <div
                    key={ev.id}
                    className="event-chip"
                    style={{ background: categoryColor(ev.category) }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onEventClick(ev);
                    }}
                    title={`${ev.start.slice(11, 16)} ${ev.title}`}
                  >
                    <span className="chip-dot" />
                    <span style={{ opacity: 0.9 }}>{ev.start.slice(11, 16)}</span>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{ev.title}</span>
                  </div>
                ))}
                {evs.length > MAX_CHIPS ? (
                  <div className="more-chip" onClick={(e) => e.stopPropagation()}>
                    +{evs.length - MAX_CHIPS} 项
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
