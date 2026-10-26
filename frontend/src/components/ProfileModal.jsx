import React, { useEffect, useMemo, useState } from "react";
import Icon from "../icons.jsx";
import { api, getApiBase, setApiBase } from "../api.js";
import { ENERGY_PRESETS } from "../meta.js";

const TABS = [
  ["habits", "作息与精力"],
  ["commit", "固定安排"],
  ["prefs", "偏好与目标"],
  ["ai", "AI 设置"],
];

const CHRONOTYPES = [
  ["morning", "晨型"],
  ["neutral", "中性"],
  ["evening", "夜型"],
];

const WD = ["一", "二", "三", "四", "五", "六", "日"];

const hm = (v, fallback) => (v && String(v).length >= 5 ? String(v).slice(0, 5) : fallback);

const EMPTY_COMMIT = { title: "", weekdays: [], start: "09:00", end: "10:00", category: "fixed", kind: "fixed" };

export default function ProfileModal({ profile, settings, onClose, onSaved }) {
  const [tab, setTab] = useState("habits");
  const [form, setForm] = useState(null);
  const [ai, setAi] = useState(null);
  const [apiKey, setApiKey] = useState("");
  const [serverAddr, setServerAddr] = useState(getApiBase());
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!profile) return;
    setForm({
      wake_time: hm(profile.wake_time, "07:30"),
      sleep_time: hm(profile.sleep_time, "23:30"),
      chronotype: profile.chronotype || "neutral",
      max_focus_min: profile.max_focus_min ?? 90,
      preferred_block_min: profile.preferred_block_min ?? 50,
      break_min: profile.break_min ?? 10,
      lunch_start: hm(profile.lunch_start, "12:00"),
      lunch_end: hm(profile.lunch_end, "13:00"),
      dinner_start: hm(profile.dinner_start, "18:30"),
      dinner_end: hm(profile.dinner_end, "19:30"),
      energy_curve:
        Array.isArray(profile.energy_curve) && profile.energy_curve.length === 24
          ? profile.energy_curve.map((v) => Math.max(1, Math.min(5, Number(v) || 3)))
          : [...ENERGY_PRESETS.neutral],
      fixed_commitments: (profile.fixed_commitments || []).map((c) => ({
        title: c.title || "",
        weekdays: Array.isArray(c.weekdays) ? c.weekdays : [],
        start: hm(c.start, "09:00"),
        end: hm(c.end, "10:00"),
        category: c.category || "fixed",
        kind: c.kind || "fixed",
      })),
      preferences: (profile.preferences || []).join("\n"),
      goals: (profile.goals || []).join("\n"),
      notes: profile.notes || "",
    });
  }, [profile]);

  useEffect(() => {
    if (!settings) return;
    setAi({
      llm_model: settings.llm_model || "",
      llm_base_url: settings.llm_base_url || "",
      timezone: settings.timezone || "Asia/Shanghai",
      plan_buffer_ratio: settings.plan_buffer_ratio || "0.15",
      llm_timeout_seconds: settings.llm_timeout_seconds || "150",
      api_key_preview: settings.api_key_preview || "",
      has_api_key: !!settings.has_api_key,
    });
  }, [settings]);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const setA = (key, value) => setAi((f) => ({ ...f, [key]: value }));

  const commitList = (form && form.fixed_commitments) || [];

  const updateCommit = (idx, patch) => {
    setForm((f) => ({
      ...f,
      fixed_commitments: f.fixed_commitments.map((c, i) => (i === idx ? { ...c, ...patch } : c)),
    }));
  };

  const toggleWeekday = (idx, wd) => {
    const cur = commitList[idx].weekdays || [];
    const next = cur.includes(wd) ? cur.filter((x) => x !== wd) : [...cur, wd].sort();
    updateCommit(idx, { weekdays: next });
  };

  const addCommit = () => {
    setForm((f) => ({ ...f, fixed_commitments: [...f.fixed_commitments, { ...EMPTY_COMMIT }] }));
  };

  const removeCommit = (idx) => {
    setForm((f) => ({ ...f, fixed_commitments: f.fixed_commitments.filter((_, i) => i !== idx) }));
  };

  const levelOf = (i) => Math.max(form.energy_curve[2 * i], form.energy_curve[2 * i + 1]);

  const cycleLevel = (i) => {
    const cur = levelOf(i);
    const next = cur >= 5 ? 1 : cur + 1;
    setForm((f) => {
      const curve = [...f.energy_curve];
      curve[2 * i] = next;
      curve[2 * i + 1] = next;
      return { ...f, energy_curve: curve };
    });
  };

  const applyPreset = (key) => {
    setForm((f) => ({ ...f, energy_curve: [...ENERGY_PRESETS[key]], chronotype: key }));
  };

  const save = async () => {
    if (!form || !ai) return;
    setSaving(true);
    setError("");
    try {
      const savedProfile = await api.saveProfile({
        wake_time: form.wake_time,
        sleep_time: form.sleep_time,
        chronotype: form.chronotype,
        max_focus_min: Number(form.max_focus_min) || 90,
        preferred_block_min: Number(form.preferred_block_min) || 50,
        break_min: Number(form.break_min) || 10,
        lunch_start: form.lunch_start,
        lunch_end: form.lunch_end,
        dinner_start: form.dinner_start,
        dinner_end: form.dinner_end,
        energy_curve: form.energy_curve,
        fixed_commitments: form.fixed_commitments
          .filter((c) => c.title.trim())
          .map((c) => ({ ...c, title: c.title.trim(), weekdays: c.weekdays || [] })),
        preferences: form.preferences
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        goals: form.goals
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        notes: form.notes,
      });
      const settingsBody = {
        llm_model: ai.llm_model,
        llm_base_url: ai.llm_base_url,
        timezone: ai.timezone,
        plan_buffer_ratio: String(ai.plan_buffer_ratio || "0.15"),
        llm_timeout_seconds: String(ai.llm_timeout_seconds || "150"),
      };
      if (apiKey.trim()) settingsBody.llm_api_key = apiKey.trim();
      const savedSettings = await api.saveSettings(settingsBody);
      const nextBase = (serverAddr || "").trim();
      if (nextBase !== getApiBase()) {
        setApiBase(nextBase);
        window.location.reload();
        return;
      }
      onSaved({ profile: savedProfile, settings: savedSettings });
    } catch (e) {
      setError(e.message || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testSettings();
      setTestResult(res);
    } catch (e) {
      setTestResult({ ok: false, error: e.message || "测试失败" });
    } finally {
      setTesting(false);
    }
  };

  const modelOptions = useMemo(() => {
    const base = ["deepseek-chat", "deepseek-reasoner"];
    if (ai && ai.llm_model && !base.includes(ai.llm_model)) base.unshift(ai.llm_model);
    return base;
  }, [ai]);

  const body = !form || !ai ? (
    <div className="empty">读取中…</div>
  ) : tab === "habits" ? (
    <>
      <div className="field-inline">
        <div className="field">
          <label>通常起床</label>
          <input className="input" type="time" value={form.wake_time} onChange={(e) => set("wake_time", e.target.value)} />
        </div>
        <div className="field">
          <label>通常入睡</label>
          <input className="input" type="time" value={form.sleep_time} onChange={(e) => set("sleep_time", e.target.value)} />
        </div>
      </div>

      <div className="field">
        <label>节律类型（可点预设，再微调下面曲线）</label>
        <div className="seg">
          {CHRONOTYPES.map(([k, label]) => (
            <button key={k} className={form.chronotype === k ? "active" : ""} onClick={() => applyPreset(k)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <label>一天中的精力曲线（点击每根柱子循环调整，0–23 点，2 小时一列）</label>
        <div className="energy-grid">
          {Array.from({ length: 12 }).map((_, i) => {
            const level = levelOf(i);
            return (
              <div className="energy-col" key={i}>
                <div
                  className="energy-bars"
                  onClick={() => cycleLevel(i)}
                  title={`${2 * i}:00–${2 * i + 2}:00 精力 ${level}/5`}
                >
                  {[1, 2, 3, 4, 5].map((step) => (
                    <div
                      key={step}
                      className={`energy-step ${level >= step ? "on" : ""} ${level >= 4 && step >= 4 ? "hi" : ""}`}
                    />
                  ))}
                </div>
                <span>{2 * i}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="field-inline">
        <div className="field">
          <label>单块最长专注（分钟）</label>
          <input
            className="input"
            type="number"
            min="20"
            max="180"
            value={form.max_focus_min}
            onChange={(e) => set("max_focus_min", e.target.value)}
          />
        </div>
        <div className="field">
          <label>偏好方块长度（分钟）</label>
          <input
            className="input"
            type="number"
            min="15"
            max="120"
            value={form.preferred_block_min}
            onChange={(e) => set("preferred_block_min", e.target.value)}
          />
        </div>
        <div className="field">
          <label>块间休息（分钟）</label>
          <input
            className="input"
            type="number"
            min="0"
            max="60"
            value={form.break_min}
            onChange={(e) => set("break_min", e.target.value)}
          />
        </div>
      </div>

      <div className="field-inline">
        <div className="field">
          <label>午餐开始</label>
          <input className="input" type="time" value={form.lunch_start} onChange={(e) => set("lunch_start", e.target.value)} />
        </div>
        <div className="field">
          <label>午餐结束</label>
          <input className="input" type="time" value={form.lunch_end} onChange={(e) => set("lunch_end", e.target.value)} />
        </div>
        <div className="field">
          <label>晚餐开始</label>
          <input className="input" type="time" value={form.dinner_start} onChange={(e) => set("dinner_start", e.target.value)} />
        </div>
        <div className="field">
          <label>晚餐结束</label>
          <input className="input" type="time" value={form.dinner_end} onChange={(e) => set("dinner_end", e.target.value)} />
        </div>
      </div>

      <div className="field">
        <label>补充说明（会写进排程上下文）</label>
        <textarea className="textarea" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
      </div>
    </>
  ) : tab === "commit" ? (
    <>
      <div className="hint" style={{ marginBottom: 10 }}>
        固定安排会在每天规划时自动占位（如课程、例会、健身课）。周几留空 = 每天。
      </div>
      {commitList.map((c, idx) => (
        <div className="commit-row" key={idx}>
          <input
            className="input"
            placeholder="名称，例如 组会"
            value={c.title}
            onChange={(e) => updateCommit(idx, { title: e.target.value })}
          />
          <div className="wd-row">
            {WD.map((label, wd) => (
              <button
                key={wd}
                className={`wd-btn ${(c.weekdays || []).includes(wd) ? "on" : ""}`}
                onClick={() => toggleWeekday(idx, wd)}
                title={`周${label}`}
              >
                {label}
              </button>
            ))}
          </div>
          <input className="input" type="time" value={c.start} onChange={(e) => updateCommit(idx, { start: e.target.value })} />
          <input className="input" type="time" value={c.end} onChange={(e) => updateCommit(idx, { end: e.target.value })} />
          <button className="icon-btn del" onClick={() => removeCommit(idx)} title="删除">
            <Icon name="trash" size={16} />
          </button>
        </div>
      ))}
      <button className="btn btn-outline btn-sm" onClick={addCommit} style={{ marginTop: 6 }}>
        <Icon name="plus" size={15} /> 添加固定安排
      </button>
    </>
  ) : tab === "prefs" ? (
    <>
      <div className="field">
        <label>个人偏好（一行一条，排程时会优先满足）</label>
        <textarea
          className="textarea"
          rows={5}
          value={form.preferences}
          onChange={(e) => set("preferences", e.target.value)}
          placeholder={"例如：\n早上先做最难的事\n晚上 9 点后不安排需要动脑的任务\n周末留半天完全不排"}
        />
      </div>
      <div className="field">
        <label>近期目标（一行一条）</label>
        <textarea
          className="textarea"
          rows={4}
          value={form.goals}
          onChange={(e) => set("goals", e.target.value)}
          placeholder={"例如：\n11 月前完成论文初稿\n每周运动 3 次"}
        />
      </div>
    </>
  ) : (
    <>
      <div className="field">
        <label>后端地址（手机 App 用）</label>
        <input
          className="input"
          value={serverAddr}
          onChange={(e) => setServerAddr(e.target.value)}
          placeholder="http://192.168.5.237:8000"
        />
        <div className="hint" style={{ marginTop: 6 }}>
          浏览器里打开时不用改（自动同源）；安卓 App 里填电脑的局域网地址，保存后会重新连接。
        </div>
      </div>
      <div className="field">
        <label>模型</label>
        <select className="select" value={ai.llm_model} onChange={(e) => setA("llm_model", e.target.value)}>
          {modelOptions.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <div className="hint" style={{ marginTop: 6 }}>
          deepseek-chat 更快；deepseek-reasoner 更会推理但更慢、更贵。
        </div>
      </div>
      <div className="field">
        <label>API Base URL</label>
        <input className="input" value={ai.llm_base_url} onChange={(e) => setA("llm_base_url", e.target.value)} />
      </div>
      <div className="field">
        <label>API Key</label>
        <input
          className="input"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={ai.has_api_key ? `已配置（${ai.api_key_preview}），留空则不修改` : "填 sk-... 后保存"}
        />
      </div>
      <div className="field-inline">
        <div className="field">
          <label>时区</label>
          <input className="input" value={ai.timezone} onChange={(e) => setA("timezone", e.target.value)} />
        </div>
        <div className="field">
          <label>缓冲比例（0–1）</label>
          <input className="input" value={ai.plan_buffer_ratio} onChange={(e) => setA("plan_buffer_ratio", e.target.value)} />
        </div>
        <div className="field">
          <label>LLM 超时（秒）</label>
          <input className="input" value={ai.llm_timeout_seconds} onChange={(e) => setA("llm_timeout_seconds", e.target.value)} />
        </div>
      </div>
      <div style={{ marginTop: 4 }}>
        <button className="btn btn-outline btn-sm" onClick={testConnection} disabled={testing}>
          <Icon name="zap" size={15} />
          {testing ? "测试中…" : "测试 API 连接"}
        </button>
      </div>
      {testResult ? (
        testResult.ok ? (
          <div className="notice ok" style={{ marginTop: 10 }}>
            连接成功，可用模型：{(testResult.models || []).join("、") || "未知"}。
          </div>
        ) : (
          <div className="notice warn" style={{ marginTop: 10 }}>
            连接失败：{testResult.error || "未知错误"}
          </div>
        )
      ) : null}
    </>
  );

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal wide">
        <div className="modal-head">
          <div>
            <div className="modal-title">习惯与设置</div>
            <div className="hint" style={{ marginTop: 4 }}>
              这里的每个参数都会进入排程上下文；改完立刻对下一次规划生效
            </div>
          </div>
          <button className="icon-btn" onClick={onClose} title="关闭">
            <Icon name="close" />
          </button>
        </div>
        <div className="modal-body">
          <div className="seg" style={{ marginBottom: 16 }}>
            {TABS.map(([k, label]) => (
              <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>
                {label}
              </button>
            ))}
          </div>
          {body}
          {error ? <div className="notice warn">{error}</div> : null}
        </div>
        <div className="modal-foot">
          <button className="btn btn-outline" onClick={onClose}>
            取消
          </button>
          <button className="btn btn-primary" onClick={save} disabled={saving || !form || !ai}>
            {saving ? "保存中…" : "保存设置"}
          </button>
        </div>
      </div>
    </div>
  );
}
