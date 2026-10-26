import React, { useEffect, useMemo, useState } from "react";
import Icon from "../icons.jsx";
import { api } from "../api.js";
import { addDays, fmtHours } from "../dates.js";
import { categoryLabel } from "../meta.js";

const RANGES = [
  { days: 7, label: "7 天" },
  { days: 14, label: "14 天" },
  { days: 28, label: "28 天" },
  { days: 90, label: "90 天" },
];

const BUCKET_ORDER = ["上午(5-12)", "下午(12-18)", "晚上(18-24)", "深夜(0-5)"];

function fullDaily(stats) {
  const map = new Map((stats.daily || []).map((d) => [d.date, d]));
  const out = [];
  let cur = stats.period_start;
  let guard = 0;
  while (cur <= stats.period_end && guard < 400) {
    out.push(
      map.get(cur) || {
        date: cur,
        planned_min: 0,
        done_min: 0,
        completion_rate: 0,
        blocks_planned: 0,
        blocks_done: 0,
      },
    );
    cur = addDays(cur, 1);
    guard += 1;
  }
  return out;
}

function DailyChart({ series }) {
  const W = 800;
  const H = 210;
  const padL = 36;
  const padR = 10;
  const padT = 12;
  const padB = 24;
  const iw = W - padL - padR;
  const ih = H - padT - padB;
  const max = Math.max(60, ...series.map((d) => d.planned_min));
  const bw = iw / Math.max(series.length, 1);
  const y = (v) => padT + ih * (1 - v / max);
  const ticks = [0, 0.5, 1].map((f) => Math.round(max * f));
  const step = Math.max(1, Math.round(series.length / 8));

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} stroke="#eef0f2" strokeWidth="1" />
          <text x={padL - 6} y={y(t) + 4} textAnchor="end" fontSize="10" fill="#9aa0a6">
            {t}
          </text>
        </g>
      ))}
      {series.map((d, i) => {
        const x = padL + i * bw;
        const ph = Math.max(0, (d.planned_min / max) * ih);
        const dh = Math.max(0, (d.done_min / max) * ih);
        return (
          <g key={d.date}>
            <rect x={x + bw * 0.18} y={padT + ih - ph} width={bw * 0.64} height={ph} fill="#e8eaed" rx="2" />
            <rect x={x + bw * 0.18} y={padT + ih - dh} width={bw * 0.64} height={dh} fill="var(--blue)" rx="2" />
            {i % step === 0 ? (
              <text x={x + bw / 2} y={H - 8} textAnchor="middle" fontSize="9.5" fill="#9aa0a6">
                {d.date.slice(5)}
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}

function CumulativeChart({ series }) {
  const W = 800;
  const H = 190;
  const padL = 46;
  const padR = 10;
  const padT = 12;
  const padB = 22;
  const iw = W - padL - padR;
  const ih = H - padT - padB;
  const max = Math.max(60, ...series.map((d) => Math.max(d.cum_planned_min, d.cum_done_min)));
  const x = (i) => padL + (iw * i) / Math.max(series.length - 1, 1);
  const y = (v) => padT + ih * (1 - v / max);
  const line = (key) => series.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`).join(" ");
  const ticks = [0, 0.5, 1].map((f) => Math.round(max * f));
  const step = Math.max(1, Math.round(series.length / 6));

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} stroke="#eef0f2" strokeWidth="1" />
          <text x={padL - 6} y={y(t) + 4} textAnchor="end" fontSize="10" fill="#9aa0a6">
            {fmtHours(t)}h
          </text>
        </g>
      ))}
      <path d={line("cum_planned_min")} fill="none" stroke="#bdc1c6" strokeWidth="2" strokeDasharray="4 3" />
      <path d={line("cum_done_min")} fill="none" stroke="var(--blue)" strokeWidth="2.2" />
      {series.map((d, i) =>
        i % step === 0 ? (
          <text key={d.date} x={x(i)} y={H - 6} textAnchor="middle" fontSize="9.5" fill="#9aa0a6">
            {d.date.slice(5)}
          </text>
        ) : null,
      )}
    </svg>
  );
}

function SleepChart({ trend }) {
  const W = 800;
  const H = 170;
  const padL = 36;
  const padR = 10;
  const padT = 12;
  const padB = 24;
  const iw = W - padL - padR;
  const ih = H - padT - padB;
  const max = 10;
  const bw = iw / Math.max(trend.length, 1);
  const y = (v) => padT + ih * (1 - v / max);

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`}>
      {[0, 5, 10].map((t) => (
        <g key={t}>
          <line x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} stroke="#eef0f2" />
          <text x={padL - 6} y={y(t) + 4} textAnchor="end" fontSize="10" fill="#9aa0a6">
            {t}h
          </text>
        </g>
      ))}
      {trend.map((d, i) => {
        const v = d.sleep_hours || 0;
        const h = Math.max(0, (v / max) * ih);
        const tone = v < 6 ? "#d93025" : v < 7 ? "#f9ab00" : "var(--blue)";
        return (
          <g key={d.date}>
            <rect x={padL + i * bw + bw * 0.2} y={padT + ih - h} width={bw * 0.6} height={h} fill={tone} rx="2" />
            {i % Math.max(1, Math.round(trend.length / 8)) === 0 ? (
              <text x={padL + i * bw + bw / 2} y={H - 8} textAnchor="middle" fontSize="9.5" fill="#9aa0a6">
                {d.date.slice(5)}
              </text>
            ) : null}
          </g>
        );
      })}
      {!trend.length ? (
        <text x={W / 2} y={H / 2} textAnchor="middle" fontSize="12" fill="#9aa0a6">
          还没有反馈记录
        </text>
      ) : null}
    </svg>
  );
}

function BarRow({ label, rate, planned, done }) {
  return (
    <div className="bar-row">
      <span className="bl" title={label}>
        {label}
      </span>
      <div className="btrack">
        <div className="bfill" style={{ width: `${Math.max(2, Math.round(rate * 100))}%` }} />
      </div>
      <span className="bv">
        {Math.round(rate * 100)}% · {fmtHours(done)}/{fmtHours(planned)}h
      </span>
    </div>
  );
}

export default function StatsView({ days, setDays }) {
  const [stats, setStats] = useState(null);
  const [progress, setProgress] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    Promise.all([api.stats(days), api.progress(days)])
      .then(([ov, pr]) => {
        if (!alive) return;
        setStats(ov);
        setProgress((pr && pr.series) || []);
      })
      .catch((e) => alive && setError(e.message || "加载统计失败"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [days]);

  const series = useMemo(() => (stats ? fullDaily(stats) : []), [stats]);
  const daysWithBlocks = useMemo(
    () => (stats ? stats.daily.filter((d) => d.blocks_planned > 0).length : 0),
    [stats],
  );

  const bucketRows = useMemo(() => {
    if (!stats) return [];
    const order = (k) => {
      const idx = BUCKET_ORDER.indexOf(k);
      return idx === -1 ? 99 : idx;
    };
    return [...stats.by_hour_bucket].sort((a, b) => order(a.key) - order(b.key));
  }, [stats]);

  const categoryRows = useMemo(() => {
    if (!stats) return [];
    return [...stats.by_category].sort((a, b) => b.planned_min - a.planned_min).slice(0, 8);
  }, [stats]);

  const weekdayRows = useMemo(() => {
    if (!stats) return [];
    const order = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
    return [...stats.by_weekday].sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));
  }, [stats]);

  if (loading && !stats) return <div className="stats-view"><div className="empty">统计加载中…</div></div>;
  if (error) return <div className="stats-view"><div className="notice warn">{error}</div></div>;
  if (!stats) return null;

  const acc = stats.estimate_accuracy || {};
  const feedbackTrend = (stats.feedback_trend || []).filter((f) => f.sleep_hours != null);
  const avgSleep = feedbackTrend.length
    ? feedbackTrend.reduce((s, f) => s + f.sleep_hours, 0) / feedbackTrend.length
    : null;

  return (
    <div className="stats-view">
      <div className="stats-head">
        <div>
          <div className="stats-title">学习科学统计</div>
          <div className="stats-sub">
            {stats.period_start} – {stats.period_end} · 有安排的天数 {daysWithBlocks} 天
          </div>
        </div>
        <div className="seg">
          {RANGES.map((r) => (
            <button key={r.days} className={days === r.days ? "active" : ""} onClick={() => setDays(r.days)}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="stat-cards">
        <div className="stat-card">
          <div className="sc-label">总完成率</div>
          <div className="sc-value">
            {Math.round((stats.completion_rate || 0) * 100)}
            <span className="sc-unit">%</span>
          </div>
          <div className="sc-sub">
            {fmtHours(stats.total_done_min)} / {fmtHours(stats.total_planned_min)} 小时
          </div>
        </div>
        <div className="stat-card">
          <div className="sc-label">已安排专注</div>
          <div className="sc-value">
            {fmtHours(stats.total_planned_min)}
            <span className="sc-unit">小时</span>
          </div>
          <div className="sc-sub">日均 {fmtHours(stats.total_planned_min / Math.max(1, days))} 小时</div>
        </div>
        <div className="stat-card">
          <div className="sc-label">预估偏差系数</div>
          <div className="sc-value">{acc.bias_ratio != null ? `${acc.bias_ratio}×` : "—"}</div>
          <div className="sc-sub">
            {acc.samples ? `样本 ${acc.samples} 个；小于 1 表示你高估了耗时` : "填「实际投入」后开始积累"}
          </div>
        </div>
        <div className="stat-card">
          <div className="sc-label">平均睡眠</div>
          <div className="sc-value">
            {avgSleep != null ? avgSleep.toFixed(1) : "—"}
            <span className="sc-unit">小时</span>
          </div>
          <div className="sc-sub">{feedbackTrend.length} 天有睡眠反馈</div>
        </div>
      </div>

      <div className="panel-grid">
        <div className="panel">
          <div className="panel-title">每日计划 vs 实际完成</div>
          <div className="panel-sub">灰色为计划时长，蓝色为实际完成（按分钟）</div>
          <div className="legend">
            <span>
              <i style={{ background: "#e8eaed" }} />
              计划
            </span>
            <span>
              <i style={{ background: "var(--blue)" }} />
              完成
            </span>
          </div>
          <DailyChart series={series} />
        </div>
        <div className="panel">
          <div className="panel-title">自动洞察</div>
          <div className="panel-sub">基于完成率、时段与睡眠数据的规则分析</div>
          {stats.top_insights && stats.top_insights.length ? (
            <ul className="insight-list">
              {stats.top_insights.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          ) : (
            <div className="empty">记录更多天之后这里会出现洞察。</div>
          )}
        </div>
      </div>

      <div className="panel-grid">
        <div className="panel">
          <div className="panel-title">按时段完成率</div>
          <div className="panel-sub">哪个时段你最能落地？排程会优先把深任务放进去</div>
          {bucketRows.length ? (
            bucketRows.map((b) => (
              <BarRow key={b.key} label={b.key} rate={b.completion_rate} planned={b.planned_min} done={b.done_min} />
            ))
          ) : (
            <div className="empty">暂无数据</div>
          )}
        </div>
        <div className="panel">
          <div className="panel-title">按分类完成率</div>
          <div className="panel-sub">哪类任务最容易拖延</div>
          {categoryRows.length ? (
            categoryRows.map((c) => (
              <BarRow
                key={c.key}
                label={categoryLabel(c.key)}
                rate={c.completion_rate}
                planned={c.planned_min}
                done={c.done_min}
              />
            ))
          ) : (
            <div className="empty">暂无数据</div>
          )}
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="panel-title">累积完成曲线</div>
        <div className="panel-sub">虚线是累积计划时长，实线是累积完成时长；两条线的差距表示积压</div>
        <div className="legend">
          <span>
            <i style={{ background: "#bdc1c6" }} />
            累积计划
          </span>
          <span>
            <i style={{ background: "var(--blue)" }} />
            累积完成
          </span>
        </div>
        <CumulativeChart series={progress} />
      </div>

      <div className="panel-grid">
        <div className="panel">
          <div className="panel-title">睡眠反馈</div>
          <div className="panel-sub">红色 &lt; 6h，黄色 &lt; 7h；睡眠会直接改变第二天的深度块上限</div>
          <SleepChart trend={feedbackTrend} />
        </div>
        <div className="panel">
          <div className="panel-title">按星期完成率</div>
          <div className="panel-sub">看看哪天最容易掉链子</div>
          {weekdayRows.length ? (
            weekdayRows.map((w) => (
              <BarRow
                key={w.key}
                label={`${w.key} · ${w.active_days}天`}
                rate={w.completion_rate}
                planned={w.planned_min}
                done={w.done_min}
              />
            ))
          ) : (
            <div className="empty">暂无数据</div>
          )}
        </div>
      </div>
    </div>
  );
}
