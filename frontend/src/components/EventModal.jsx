import React, { useMemo, useState } from "react";
import Icon from "../icons.jsx";
import { api } from "../api.js";
import { CATEGORIES, KIND_LABEL, STATUS_LABEL, categoryColor } from "../meta.js";
import {
  fmtDuration,
  fromDatetimeLocal,
  minutesOf,
  toDatetimeLocal,
} from "../dates.js";

const KINDS = Object.keys(KIND_LABEL);

export default function EventModal({ draft, onClose, onSaved, onDeleted }) {
  const editing = draft.mode === "edit" && draft.event;
  const ev = draft.event || {};

  const [title, setTitle] = useState(ev.title || "");
  const [category, setCategory] = useState(ev.category || "study");
  const [kind, setKind] = useState(ev.kind || "focus");
  const [start, setStart] = useState(
    ev.start ? toDatetimeLocal(ev.start) : `${draft.date}T${minutesToHm(draft.startMin || 540)}`,
  );
  const [end, setEnd] = useState(
    ev.end
      ? toDatetimeLocal(ev.end)
      : `${draft.date}T${minutesToHm((draft.startMin || 540) + 60)}`,
  );
  const [notes, setNotes] = useState(ev.notes || "");
  const [status, setStatus] = useState(ev.status || "planned");
  const [actualMin, setActualMin] = useState(ev.actual_min ?? "");
  const [quality, setQuality] = useState(ev.quality ?? 4);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const rules = useMemo(() => ev.rule_ids || [], [ev.rule_ids]);

  const plannedMin = useMemo(() => {
    if (!start || !end) return 0;
    return Math.max(0, minutesOf(fromDatetimeLocal(end)) - minutesOf(fromDatetimeLocal(start)));
  }, [start, end]);

  const save = async () => {
    if (!title.trim()) {
      setError("标题不能为空");
      return;
    }
    if (!start || !end || end <= start) {
      setError("结束时间必须晚于开始时间");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const body = {
        title: title.trim(),
        category,
        kind,
        notes,
        start: fromDatetimeLocal(start),
        end: fromDatetimeLocal(end),
        status,
      };
      if (status !== "planned") {
        body.actual_min = actualMin === "" ? Math.round(plannedMin) : Number(actualMin);
        body.quality = Number(quality);
      }
      let saved;
      if (editing) {
        saved = await api.updateEvent(ev.id, body);
      } else {
        saved = await api.createEvent(body);
      }
      onSaved(saved);
    } catch (e) {
      setError(e.message || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      await api.deleteEvent(ev.id);
      onDeleted(ev.id);
    } catch (e) {
      setError(e.message || "删除失败");
      setSaving(false);
    }
  };

  const quick = (s) => {
    setStatus(s);
    if (s !== "planned" && actualMin === "") setActualMin(Math.round(plannedMin));
  };

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-head">
          <span className="modal-title">{editing ? "编辑方块" : "新建方块"}</span>
          <button className="icon-btn" onClick={onClose}>
            <Icon name="close" />
          </button>
        </div>
        <div className="modal-body">
          <div className="field">
            <input
              className="input"
              style={{ fontSize: 16, padding: "12px 14px" }}
              placeholder="添加标题"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
            />
          </div>

          <div className="field">
            <label>时间</label>
            <div className="field-inline">
              <input
                className="input"
                type="datetime-local"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
              <input
                className="input"
                type="datetime-local"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </div>
            <div className="hint" style={{ marginTop: 6 }}>
              计划时长 {fmtDuration(plannedMin)}
              {ev.reason ? ` · 排程依据：${ev.reason}` : ""}
            </div>
          </div>

          <div className="field-inline">
            <div className="field">
              <label>类别</label>
              <select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>类型</label>
              <select className="select" value={kind} onChange={(e) => setKind(e.target.value)}>
                {KINDS.map((k) => (
                  <option key={k} value={k}>
                    {KIND_LABEL[k]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="field">
            <label>备注（可写 if-then 实施意向）</label>
            <textarea
              className="textarea"
              style={{ minHeight: 64 }}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="例如：如果卡住超过 10 分钟，就先做下一步最小动作"
            />
          </div>

          {rules.length ? (
            <div className="field">
              <label>排程依据（规则卡）</label>
              <div className="chip-row">
                {rules.map((r) => (
                  <span key={r} className="chip rule">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {editing ? (
            <div className="field">
              <label>完成情况</label>
              <div className="quick-status" style={{ marginBottom: 10 }}>
                {["planned", "done", "partial", "skipped"].map((s) => (
                  <button
                    key={s}
                    className={`qs-btn ${status === s ? "active" : ""}`}
                    onClick={() => quick(s)}
                  >
                    {STATUS_LABEL[s]}
                  </button>
                ))}
              </div>
              {status !== "planned" ? (
                <div className="field-inline">
                  <div className="field">
                    <label>实际投入（分钟）</label>
                    <input
                      className="input"
                      type="number"
                      min="0"
                      value={actualMin}
                      onChange={(e) => setActualMin(e.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label>质量（1–5）</label>
                    <input
                      className="input"
                      type="range"
                      min="1"
                      max="5"
                      value={quality}
                      onChange={(e) => setQuality(e.target.value)}
                      style={{ padding: 0 }}
                    />
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {error ? <div className="notice warn">{error}</div> : null}
        </div>
        <div className="modal-foot">
          {editing ? (
            <button className="btn btn-danger" onClick={remove} disabled={saving} style={{ marginRight: "auto" }}>
              <Icon name="trash" size={16} /> 删除
            </button>
          ) : null}
          <button className="btn btn-outline" onClick={onClose}>
            取消
          </button>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}

function minutesToHm(min) {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}
