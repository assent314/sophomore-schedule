import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const FEEDBACK_LABELS = {
  sleep_hours: "睡眠时长", sleep_quality: "睡眠质量",
  energy_morning: "上午精力", energy_afternoon: "下午精力",
  energy_evening: "晚上精力", mood: "心情",
};

export default function AgentActivityModal({ onClose }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api.agentCaptures().then((rows) => { if (active) setItems(rows || []); })
      .catch((e) => { if (active) setError(e.message || "读取失败"); });
    return () => { active = false; };
  }, []);

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal wide">
        <div className="modal-head">
          <div className="modal-title">Agent 调整记录</div>
          <button className="icon-btn" onClick={onClose} aria-label="关闭">×</button>
        </div>
        <div className="modal-body">
          <p className="hint">这里只保存从对话中提取的结构化事实和调整结果，不保存完整聊天。</p>
          {error ? <div className="notice warn">{error}</div> : null}
          {!error && !items.length ? <div className="empty">暂无 Agent 记录</div> : null}
          {items.map((item) => {
            const facts = item.facts || {};
            const changes = [
              ...Object.entries(facts.feedback || {}).map(([key, value]) =>
                `${FEEDBACK_LABELS[key] || key}：${value}${key === "sleep_hours" ? " 小时" : ""}`),
              ...(facts.tasks_created || []).map((task) => `任务：${task.title}`),
              ...(facts.habitual_energy_curve_changed ? ["更新了长期精力曲线"] : []),
              ...(facts.constraints || []).map((value) => `约束：${value}`),
            ];
            return (
              <div className="rule-card" key={item.id}>
                <div className="rule-head">
                  <strong>{item.day}</strong><span className="badge">{item.source}</span>
                  <span className="hint">{item.created_at?.replace("T", " ")}</span>
                </div>
                <div>{changes.join(" · ") || "未提取到需要保存的事实"}</div>
                <div className="hint" style={{ marginTop: 6 }}>
                  {facts.adjust_error ? `调整失败：${facts.adjust_error}` : item.plan_run_id ? "已根据这些信息调整日程" : "未调整日程"}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
