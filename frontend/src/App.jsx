import React, { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "./components/TopBar.jsx";
import Sidebar from "./components/Sidebar.jsx";
import WeekView from "./components/WeekView.jsx";
import MonthView from "./components/MonthView.jsx";
import StatsView from "./components/StatsView.jsx";
import PlannerPanel from "./components/PlannerPanel.jsx";
import EventModal from "./components/EventModal.jsx";
import FeedbackModal from "./components/FeedbackModal.jsx";
import ProfileModal from "./components/ProfileModal.jsx";
import MemoryModal from "./components/MemoryModal.jsx";
import KnowledgeModal from "./components/KnowledgeModal.jsx";
import Toast from "./components/Toast.jsx";
import ConnectionSetup from "./components/ConnectionSetup.jsx";
import AgentActivityModal from "./components/AgentActivityModal.jsx";
import { api, getApiBase, isNativeShell } from "./api.js";
import {
  addDays,
  addMonths,
  fmtDayTitle,
  fmtHours,
  fmtMonthCn,
  fmtWeekTitle,
  monthMatrix,
  startOfWeek,
  todayYmd,
} from "./dates.js";

function rangeFor(view, cursor) {  if (view === "day") return { start: cursor, end: cursor };
  if (view === "week") {
    const start = startOfWeek(cursor);
    return { start, end: addDays(start, 6) };
  }
  if (view === "month") {
    const cells = monthMatrix(cursor);
    return { start: cells[0].date, end: cells[cells.length - 1].date };
  }
  return { start: addDays(todayYmd(), -119), end: todayYmd() };
}

function minutesBetween(a, b) {
  const ms = new Date(b).getTime() - new Date(a).getTime();
  return Number.isFinite(ms) && ms > 0 ? Math.round(ms / 60000) : 0;
}

const VIEWS = ["day", "week", "month", "stats"];

function readInitialState() {
  const params = new URLSearchParams(window.location.search);
  const v = params.get("view");
  const c = params.get("cursor");
  const d = params.get("days");
  // 手机上 7 列周视图挤不下，默认进日视图
  const narrow = typeof window !== "undefined" && window.innerWidth < 720;
  return {
    view: VIEWS.includes(v) ? v : narrow ? "day" : "week",
    cursor: c && /^\d{4}-\d{2}-\d{2}$/.test(c) ? c : todayYmd(),
    statsDays: d && /^\d+$/.test(d) ? Number(d) : 28,
  };
}

export default function App() {
  const initial = useMemo(readInitialState, []);
  const [view, setView] = useState(initial.view);
  const [cursor, setCursor] = useState(initial.cursor);
  const [events, setEvents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [profile, setProfile] = useState(null);
  const [settings, setSettings] = useState(null);
  const [memory, setMemory] = useState(null);
  const [search, setSearch] = useState("");
  const [hiddenCats, setHiddenCats] = useState([]);
  const [plannerOpen, setPlannerOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [agentActivityOpen, setAgentActivityOpen] = useState(false);
  const [eventDraft, setEventDraft] = useState(null);
  const [toast, setToast] = useState(null);
  const [statsDays, setStatsDays] = useState(initial.statsDays);
  const [loading, setLoading] = useState(false);
  const [connError, setConnError] = useState("");
  const [connectionOpen, setConnectionOpen] = useState(isNativeShell() && !getApiBase());
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [syncTick, setSyncTick] = useState(0);

  const notify = useCallback((message, error = false) => {
    setToast({ message, error, id: Date.now() });
  }, []);

  useEffect(() => {
    // 先探活：手机 App 里最常见的问题是后端地址不对/电脑没开服务
    api
      .health()
      .then(() => setConnError(""))
      .catch((e) => setConnError(e.message || "连不上后端"));
    api.tasks({}).then((list) => setTasks(list || [])).catch(() => {});
    api.profile().then(setProfile).catch(() => {});
    api.settings().then(setSettings).catch(() => {});
    api.memory().then(setMemory).catch(() => {});
  }, []);

  useEffect(() => {
    if (view === "stats") return undefined;
    const r = rangeFor(view, cursor);
    let alive = true;
    setLoading(true);
    api
      .events({ start: r.start, end: r.end })
      .then((list) => {
        if (alive) setEvents(list || []);
      })
      .catch((e) => {
        if (alive) notify(e.message || "读取日程失败", true);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [view, cursor, notify]);

  const refreshRange = useCallback(async () => {
    const r = rangeFor(view, cursor);
    try {
      const list = await api.events({ start: r.start, end: r.end });
      setEvents(list || []);
    } catch (e) {
      notify(e.message || "刷新失败", true);
    }
  }, [view, cursor, notify]);

  const refreshTasks = useCallback(async () => {
    try {
      const list = await api.tasks({});
      setTasks(list || []);
    } catch { /* 网络断开时由连接提示统一说明 */ }
  }, []);

  const refreshMemory = useCallback(() => {
    api.memory().then(setMemory).catch(() => {});
  }, []);

  useEffect(() => {
    let active = true;
    const sync = async () => {
      if (document.visibilityState === "hidden") return;
      try {
        await api.health();
        if (!active) return;
        setConnError("");
        const range = rangeFor(view, cursor);
        const [ev, ta, pr, st, me] = await Promise.all([
          api.events({ start: range.start, end: range.end }),
          api.tasks({}), api.profile(), api.settings(), api.memory(),
        ]);
        if (!active) return;
        setEvents(ev || []);
        setTasks(ta || []);
        setProfile(pr);
        setSettings(st);
        setMemory(me);
        setSyncTick((n) => n + 1);
      } catch (e) {
        if (active) setConnError(e.message || "连不上后端");
      }
    };
    const onVisible = () => { if (document.visibilityState === "visible") sync(); };
    window.addEventListener("focus", sync);
    document.addEventListener("visibilitychange", onVisible);
    const timer = window.setInterval(sync, 30000);
    return () => {
      active = false;
      window.removeEventListener("focus", sync);
      document.removeEventListener("visibilitychange", onVisible);
      window.clearInterval(timer);
    };
  }, [view, cursor]);

  const filteredEvents = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return events;
    return events.filter((e) => `${e.title} ${e.notes || ""}`.toLowerCase().includes(q));
  }, [events, search]);

  const eventsByDate = useMemo(() => {
    const map = {};
    for (const ev of filteredEvents) {
      const key = ev.plan_date || (ev.start || "").slice(0, 10);
      if (!map[key]) map[key] = [];
      map[key].push(ev);
    }
    for (const key of Object.keys(map)) {
      map[key].sort((a, b) => (a.start < b.start ? -1 : 1));
    }
    return map;
  }, [filteredEvents]);

  const days = useMemo(() => {
    if (view === "day") return [cursor];
    const start = startOfWeek(cursor);
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  }, [view, cursor]);

  const visibleMin = useMemo(
    () => filteredEvents.reduce((sum, e) => sum + minutesBetween(e.start, e.end), 0),
    [filteredEvents],
  );

  const title =
    view === "stats"
      ? "学习科学统计"
      : view === "day"
        ? fmtDayTitle(cursor)
        : view === "week"
          ? fmtWeekTitle(cursor)
          : fmtMonthCn(cursor);

  const titleSub =
    view === "stats"
      ? `近 ${statsDays} 天`
      : `${fmtHours(visibleMin)} 小时已排 · ${filteredEvents.length} 个方块`;

  const step = (dir) => {
    if (view === "month") setCursor(addMonths(cursor, dir));
    else if (view === "week") setCursor(addDays(cursor, dir * 7));
    else setCursor(addDays(cursor, dir));
  };

  const toggleTask = async (task) => {
    try {
      await api.updateTask(task.id, { status: task.status === "done" ? "pending" : "done" });
      refreshTasks();
      notify(task.status === "done" ? "已标记为未完成" : "任务已完成");
    } catch (e) {
      notify(e.message || "更新任务失败", true);
    }
  };

  const addTask = async (titleText) => {
    try {
      await api.createTask({ title: titleText, category: "study", estimate_min: 45 });
      refreshTasks();
      notify("已加入待办");
    } catch (e) {
      notify(e.message || "创建任务失败", true);
    }
  };

  const toggleCat = (key) => {
    setHiddenCats((list) => (list.includes(key) ? list.filter((k) => k !== key) : [...list, key]));
  };

  const onEventClick = (ev) => setEventDraft({ mode: "edit", event: ev });
  const onSlotClick = (day, min) => setEventDraft({ mode: "create", date: day, startMin: min });
  const onDayClick = (day) => {
    setCursor(day);
    setView("day");
  };

  const handleEventSaved = async () => {
    setEventDraft(null);
    await refreshRange();
    notify("方块已保存");
  };

  const handleEventMoved = async (ev, patch) => {
    try {
      await api.updateEvent(ev.id, patch);
      await refreshRange();
      notify(`已调整为 ${patch.start.slice(11, 16)}–${patch.end.slice(11, 16)}`);
    } catch (err) {
      notify(err.message || "调整失败");
    }
  };

  const handleEventDeleted = async () => {
    setEventDraft(null);
    await refreshRange();
    notify("方块已删除");
  };

  const handlePlanApplied = async (res, planDate) => {
    setPlannerOpen(false);
    if (planDate) setCursor(planDate);
    await Promise.all([
      planDate && planDate !== cursor ? Promise.resolve() : refreshRange(),
      refreshTasks(),
      Promise.resolve(refreshMemory()),
    ]);
    notify(`已生成 ${(res && res.events && res.events.length) || 0} 个方块`);
  };

  const handleFeedbackSaved = async () => {
    setFeedbackOpen(false);
    refreshMemory();
    notify("反馈已保存，明天的排程会参考它");
  };

  const handleProfileSaved = ({ profile: p, settings: s }) => {
    if (p) setProfile(p);
    if (s) setSettings(s);
    setProfileOpen(false);
    notify("设置已保存");
  };

  const jumpTo = (day) => {
    setCursor(day);
    if (view === "stats") setView("week");
  };

  return (
    <div className="app-shell">
      <TopBar
        view={view}
        setView={setView}
        title={title}
        titleSub={titleSub}
        onPrev={() => step(-1)}
        onNext={() => step(1)}
        onToday={() => setCursor(todayYmd())}
        onPlanner={() => setPlannerOpen(true)}
        onFeedback={() => setFeedbackOpen(true)}
        onOpenMemory={() => setMemoryOpen(true)}
        onOpenProfile={() => setProfileOpen(true)}
        search={search}
        setSearch={setSearch}
        onMenu={() => setSidebarOpen(true)}
      />

      <div className="main">
        {connError ? (
          <div className="conn-banner">
            <span>
              连不上后端 <b>{getApiBase()}</b>：{connError}
              <span className="conn-hint">（手机请确认和电脑同一 WiFi、电脑端已启动「日程规划」）</span>
            </span>
            <span className="conn-actions">
              <button className="btn btn-outline btn-sm" onClick={() => setConnectionOpen(true)}>
                设置后端地址
              </button>
              <button
                className="btn btn-sm"
                onClick={() => window.location.reload()}
              >
                重试
              </button>
            </span>
          </div>
        ) : null}
        <div className="main-body">
        {sidebarOpen ? <div className="mobile-sidebar-overlay" onClick={() => setSidebarOpen(false)} /> : null}
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          cursor={cursor}
          setCursor={jumpTo}
          events={events}
          tasks={tasks}
          onToggleTask={toggleTask}
          onAddTask={addTask}
          hiddenCats={hiddenCats}
          toggleCat={toggleCat}
          onOpenMemory={() => setMemoryOpen(true)}
          onOpenFeedback={() => setFeedbackOpen(true)}
          onOpenProfile={() => setProfileOpen(true)}
          onOpenKnowledge={() => setKnowledgeOpen(true)}
          onOpenAgentActivity={() => { setSidebarOpen(false); setAgentActivityOpen(true); }}
          memoryStale={!!(memory && memory.stale)}
          onPlanner={() => setPlannerOpen(true)}
        />

        <div className="calendar-area">
          {view === "stats" ? (
            <StatsView days={statsDays} setDays={setStatsDays} refreshKey={syncTick} />
          ) : view === "month" ? (
            <MonthView
              cursor={cursor}
              eventsByDate={eventsByDate}
              hiddenCats={hiddenCats}
              onEventClick={onEventClick}
              onDayClick={onDayClick}
            />
          ) : (
            <WeekView
              days={days}
              eventsByDate={eventsByDate}
              onEventClick={onEventClick}
              onSlotClick={onSlotClick}
              onEventMoved={handleEventMoved}
              hiddenCats={hiddenCats}
              scrollHour={7}
            />
          )}
        </div>
        </div>
      </div>

      {loading ? <div className="loading-bar" /> : null}

      {plannerOpen ? (
        <>
          <div className="overlay" onClick={() => setPlannerOpen(false)} />
          <PlannerPanel
            date={cursor}
            onClose={() => setPlannerOpen(false)}
            onApplied={handlePlanApplied}
          />
        </>
      ) : null}

      {eventDraft ? (
        <EventModal
          draft={eventDraft}
          onClose={() => setEventDraft(null)}
          onSaved={handleEventSaved}
          onDeleted={handleEventDeleted}
        />
      ) : null}

      {feedbackOpen ? (
        <FeedbackModal day={cursor} onClose={() => setFeedbackOpen(false)} onSaved={handleFeedbackSaved} />
      ) : null}

      {profileOpen ? (
        <ProfileModal
          profile={profile}
          settings={settings}
          onClose={() => setProfileOpen(false)}
          onSaved={handleProfileSaved}
          onOpenConnection={() => { setProfileOpen(false); setConnectionOpen(true); }}
        />
      ) : null}

      {memoryOpen ? <MemoryModal onClose={() => setMemoryOpen(false)} onUpdated={setMemory} /> : null}

      {knowledgeOpen ? <KnowledgeModal onClose={() => setKnowledgeOpen(false)} /> : null}
      {agentActivityOpen ? <AgentActivityModal onClose={() => setAgentActivityOpen(false)} /> : null}

      {connectionOpen ? <ConnectionSetup onClose={() => setConnectionOpen(false)} /> : null}

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
