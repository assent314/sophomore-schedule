import React, { useEffect, useState } from "react";
import Icon from "../icons.jsx";
import { api } from "../api.js";
import { mdToHtml } from "../meta.js";
import { fmtHours } from "../dates.js";

export default function MemoryModal({ onClose, onUpdated }) {
  const [memory, setMemory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const m = await api.memory();
      setMemory(m);
    } catch (e) {
      setError(e.message || "读取记忆失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refresh = async (useLlm) => {
    setRefreshing(true);
    setError("");
    try {
      const m = await api.refreshMemory(useLlm);
      setMemory(m);
      onUpdated?.(m);
    } catch (e) {
      setError(e.message || "生成记忆失败");
    } finally {
      setRefreshing(false);
    }
  };

  const stats = (memory && memory.stats) || {};
  const hasText = memory && memory.summary_md && memory.summary_md.trim();

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-head">
          <div>
            <div className="modal-title">近一月记忆</div>
            <div className="hint" style={{ marginTop: 4 }}>
              每次 AI 排程都会读这段复盘，使规划延续你的真实节奏
            </div>
          </div>
          <button className="icon-btn" onClick={onClose} title="关闭">
            <Icon name="close" />
          </button>
        </div>
        <div className="modal-body">
          {loading ? (
            <div className="empty">读取中…</div>
          ) : (
            <>
              <div className="engine-row">
                <span className={`badge ${memory.stale ? "amber" : "green"}`}>
                  {memory.stale ? "待更新" : "最新"}
                </span>
                <span className="badge">{memory.period_start} – {memory.period_end}</span>
                <span className="badge blue">{memory.engine === "llm" ? "DeepSeek 复盘" : "规则复盘"}</span>
                {memory.created_at ? (
                  <span className="badge">生成于 {memory.created_at.slice(0, 16).replace("T", " ")}</span>
                ) : null}
              </div>

              {stats.total_planned_min != null ? (
                <div className="stat-cards" style={{ marginBottom: 14 }}>
                  <div className="stat-card">
                    <div className="sc-label">近一月完成率</div>
                    <div className="sc-value">
                      {Math.round((stats.completion_rate || 0) * 100)}
                      <span className="sc-unit">%</span>
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="sc-label">已计划 / 已完成</div>
                    <div className="sc-value">
                      {fmtHours(stats.total_done_min || 0)}
                      <span className="sc-unit">/ {fmtHours(stats.total_planned_min || 0)} 小时</span>
                    </div>
                  </div>
                </div>
              ) : null}

              {hasText ? (
                <div className="md" dangerouslySetInnerHTML={{ __html: mdToHtml(memory.summary_md) }} />
              ) : (
                <div className="empty">
                  还没有复盘记忆。
                  <br />
                  点下面的按钮，把最近 28 天的完成情况与反馈归纳成一段记忆。
                </div>
              )}

              {error ? <div className="notice warn">{error}</div> : null}
            </>
          )}
        </div>
        <div className="modal-foot">
          <button className="btn btn-outline" onClick={() => refresh(false)} disabled={refreshing}>
            <Icon name="refresh" size={16} />
            仅统计生成
          </button>
          <button className="btn btn-primary" onClick={() => refresh(true)} disabled={refreshing}>
            <Icon name="sparkles" size={16} />
            {refreshing ? "生成中…" : hasText ? "用 AI 重新复盘" : "用 AI 生成复盘"}
          </button>
        </div>
      </div>
    </div>
  );
}
