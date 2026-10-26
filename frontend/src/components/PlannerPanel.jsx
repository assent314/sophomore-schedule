import React, { useState } from "react";
import Icon from "../icons.jsx";
import { api } from "../api.js";
import { categoryColor, KIND_LABEL } from "../meta.js";
import { fmtDuration, todayYmd, toDatetimeLocal } from "../dates.js";

const EXAMPLES = [
  "上午复习线性代数 1.5 小时（周三考试），下午写论文 3 小时，晚上健身 1 小时，顺便取快递",
  "今天有点累，只安排 2 小时深度工作和 1 小时的阅读",
  "准备组会 PPT 2 小时，背 60 个单词，晚上和朋友吃饭",
];

const ENGINE_LABEL = {
  llm: "DeepSeek 排程",
  rule: "规则引擎（离线）",
  fallback: "规则引擎兜底",
};

export default function PlannerPanel({ date, onClose, onApplied }) {
  const [planDate, setPlanDate] = useState(date || todayYmd());
  const [text, setText] = useState("");
  const [mode, setMode] = useState("new");
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const request = {
    date: planDate,
    text: text.trim(),
    mode,
    replace_ai_blocks: true,
    keep_done: true,
  };

  const runPreview = async () => {
    if (!text.trim()) {
      setError("先写一句今天想做什么，例如：复习线代 1 小时、写论文 2 小时。");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await api.previewPlan(request);
      setResult(res);
    } catch (e) {
      setError(e.message || "排程失败");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const apply = async () => {
    if (!result) {
      setError("先点「生成预览」，确认没问题再应用。");
      return;
    }
    setApplying(true);
    setError("");
    try {
        // 服务端按预览 ID 读取原始结果，避免客户端状态变化或再次调用模型。
      const res = await api.applyPlan({
        date: planDate,
        plan_run_id: result.plan_run_id,
        mode,
        replace_ai_blocks: true,
        keep_done: true,
      });
      onApplied(res, planDate);
      setResult(null);
    } catch (e) {
      setError(e.message || "应用失败");
    } finally {
      setApplying(false);
    }
  };

  const blocks = result ? [...result.blocks].sort((a, b) => (a.start < b.start ? -1 : 1)) : [];

  return (
    <div className="drawer">
      <div className="drawer-head">
        <div className="drawer-title">
          <Icon name="sparkles" size={20} />
          AI 排程
        </div>
        <button className="icon-btn" onClick={onClose} title="关闭">
          <Icon name="close" />
        </button>
      </div>

      <div className="drawer-body">
        <div className="field">
          <label>排给哪一天</label>
          <div className="field-inline">
            <input
              className="input"
              type="date"
              value={planDate}
              onChange={(e) => {
                setPlanDate(e.target.value);
                setResult(null);
              }}
            />
            <div className="seg" style={{ flex: "0 0 auto" }}>
              <button
                className={mode === "new" ? "active" : ""}
                onClick={() => {
                  setMode("new");
                  setResult(null);
                }}
              >
                重新排
              </button>
              <button
                className={mode === "adjust" ? "active" : ""}
                onClick={() => {
                  setMode("adjust");
                  setResult(null);
                }}
              >
                临时调整
              </button>
            </div>
          </div>
          <div className="hint" style={{ marginTop: 6 }}>
            {mode === "new"
              ? "重新排会替换当天由 AI 生成的方块，已完成与锁定的安排会保留。"
              : "临时调整只改动当前时间之后的部分，适合开会、身体状态变化。"}
          </div>
        </div>

        <div className="field">
          <label>用一句话描述今天的任务与状态</label>
          <textarea
            className="textarea"
            placeholder="例如：上午复习线代 1.5 小时，下午写论文 3 小时，晚上健身 1 小时。昨晚睡了 6 小时。"
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setResult(null);
            }}
            rows={5}
          />
          <div className="chip-row" style={{ marginTop: 8 }}>
            {EXAMPLES.map((ex, i) => (
              <span
                key={i}
                className="chip"
                style={{ cursor: "pointer" }}
                onClick={() => {
                  setText(ex);
                  setResult(null);
                }}
              >
                示例 {i + 1}
              </span>
            ))}
          </div>
        </div>

        {error ? <div className="notice warn">{error}</div> : null}

        {result ? (
          <>
            <div className="engine-row">
              <span className="badge blue">{ENGINE_LABEL[result.engine] || result.engine}</span>
              <span className="badge">自由时间 {fmtDuration(result.free_min)}</span>
              {result.usage && result.usage.total_tokens ? (
                <span className="badge">{result.usage.total_tokens} tokens</span>
              ) : null}
            </div>

            {result.notes ? <div className="notice info">{result.notes}</div> : null}

            {result.adjustments?.length ? (
              <div className="notice info">
                相对你的描述做了这些调整：
                <ul>
                  {result.adjustments.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {result.questions?.length ? (
              <div className="notice question">
                需要你确认的信息：
                <ul>
                  {result.questions.map((q, i) => (
                    <li key={i}>{q}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="section-label">预览（{blocks.length} 个方块）</div>
            {blocks.map((b, i) => (
              <div
                key={i}
                className="block-card"
                style={{ borderLeftColor: categoryColor(b.category) }}
              >
                <div className="bc-head">
                  <span className="bc-time">
                    {toDatetimeLocal(b.start).slice(11)}–{toDatetimeLocal(b.end).slice(11)}
                  </span>
                  <span className="bc-title">{b.title}</span>
                  <span className="badge">{KIND_LABEL[b.kind] || b.kind}</span>
                </div>
                {b.reason ? <div className="bc-reason">{b.reason}</div> : null}
                {b.rule_ids?.length ? (
                  <div className="chip-row bc-rules">
                    {b.rule_ids.map((r) => (
                      <span key={r} className="chip rule">
                        {r}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}

            {result.deferred?.length ? (
              <div className="notice warn">
                今天时间不够、建议顺延：{result.deferred.map((d) => `${d.title}（剩 ${d.left_min} 分钟）`).join("、")}
              </div>
            ) : null}
          </>
        ) : (
          <div className="empty">
            写句话，点「生成预览」。
            <br />
            我会结合你的睡眠/精力反馈、昼夜节律与间隔重复把任务切成方块，并说明每一块的依据。
          </div>
        )}
      </div>

      <div className="drawer-foot">
        <button className="btn btn-outline" onClick={runPreview} disabled={loading || applying}>
          {loading ? "排程中…" : result ? "重新生成" : "生成预览"}
        </button>
        <button
          className="btn btn-primary"
          onClick={apply}
          disabled={!result || applying || (mode === "adjust" && false)}
        >
          {applying ? "应用中…" : "应用为日程"}
        </button>
      </div>
    </div>
  );
}
