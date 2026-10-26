import React, { useEffect, useState } from "react";
import Icon from "../icons.jsx";
import { api } from "../api.js";

const BLANK = {
  sleep_hours: "",
  sleep_quality: null,
  energy_morning: null,
  energy_afternoon: null,
  energy_evening: null,
  mood: null,
  notes: "",
};

const SCALES = [
  ["sleep_quality", "睡眠质量（1 很差 – 5 很好）"],
  ["energy_morning", "上午精力（1–5）"],
  ["energy_afternoon", "下午精力（1–5）"],
  ["energy_evening", "晚上精力（1–5）"],
  ["mood", "整体心情（1–5）"],
];

const PICK = Object.keys(BLANK);

function pick(row) {
  const out = {};
  for (const k of PICK) if (row[k] !== undefined) out[k] = row[k] == null ? BLANK[k] : row[k];
  return out;
}

export default function FeedbackModal({ day, onClose, onSaved }) {
  const [form, setForm] = useState(BLANK);
  const [loading, setLoading] = useState(true);
  const [parsing, setParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [hasRecord, setHasRecord] = useState(false);

  useEffect(() => {
    let alive = true;
    api
      .feedback(day)
      .then((row) => {
        if (!alive || !row) return;
        setForm({ ...BLANK, ...pick(row) });
        setHasRecord(true);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [day]);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const parseText = async () => {
    const text = form.notes.trim();
    if (!text) {
      setError("先写一句今天的状态，例如：昨晚只睡了 5 个半小时，上午还行，下午很困，效率一般。");
      return;
    }
    setParsing(true);
    setError("");
    try {
      const parsed = await api.parseFeedback(day, text);
      setForm((f) => {
        const next = { ...f };
        for (const [k, v] of Object.entries(parsed || {})) {
          if (v == null) continue;
          if (next[k] == null || next[k] === "") next[k] = v;
        }
        return next;
      });
    } catch (e) {
      setError(e.message || "解析失败");
    } finally {
      setParsing(false);
    }
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const body = {
        ...form,
        sleep_hours: form.sleep_hours === "" || form.sleep_hours == null ? null : Number(form.sleep_hours),
      };
      const row = await api.saveFeedback(day, body);
      onSaved(row);
    } catch (e) {
      setError(e.message || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal narrow">
        <div className="modal-head">
          <div>
            <div className="modal-title">今日反馈</div>
            <div className="hint" style={{ marginTop: 4 }}>
              {day} · 这些数据会直接影响明天的排程强度与时段
              {hasRecord ? "（已有记录，保存即更新）" : ""}
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
              <div className="field">
                <label>昨晚睡眠时长（小时）</label>
                <input
                  className="input"
                  type="number"
                  min="0"
                  max="16"
                  step="0.25"
                  value={form.sleep_hours}
                  onChange={(e) => set("sleep_hours", e.target.value)}
                  placeholder="例如 6.5"
                />
              </div>

              {SCALES.map(([key, label]) => (
                <div className="field" key={key}>
                  <label>{label}</label>
                  <div className="quick-status">
                    {[1, 2, 3, 4, 5].map((v) => (
                      <button
                        key={v}
                        className={`qs-btn ${form[key] === v ? "active" : ""}`}
                        onClick={() => set(key, form[key] === v ? null : v)}
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                </div>
              ))}

              <div className="field">
                <label>一句话描述状态（可自动解析成上面的数字）</label>
                <textarea
                  className="textarea"
                  rows={3}
                  value={form.notes}
                  onChange={(e) => set("notes", e.target.value)}
                  placeholder="例如：昨晚睡了 5 个半小时，上午 3 分，下午很困只有 2 分，晚上恢复一点 4 分，心情一般。"
                />
                <div style={{ marginTop: 8 }}>
                  <button className="btn btn-outline btn-sm" onClick={parseText} disabled={parsing}>
                    <Icon name="sparkles" size={15} />
                    {parsing ? "解析中…" : "解析成数字"}
                  </button>
                </div>
              </div>

              {error ? <div className="notice warn">{error}</div> : null}
              <div className="notice info">
                为什么要填：睡眠不足会改变我给你的深度块上限；精力评分用来校准你个人的昼夜节律曲线。
              </div>
            </>
          )}
        </div>
        <div className="modal-foot">
          <button className="btn btn-outline" onClick={onClose}>
            取消
          </button>
          <button className="btn btn-primary" onClick={save} disabled={saving || loading}>
            {saving ? "保存中…" : "保存反馈"}
          </button>
        </div>
      </div>
    </div>
  );
}
