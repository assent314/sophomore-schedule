import React, { useEffect, useMemo, useState } from "react";
import Icon from "../icons.jsx";
import { api } from "../api.js";
import { EVIDENCE_LABEL, KNOWLEDGE_CATEGORY_LABEL } from "../meta.js";

const STRENGTH_CLASS = { strong: "green", moderate: "blue", emerging: "amber" };

export default function KnowledgeModal({ onClose }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("all");

  useEffect(() => {
    let alive = true;
    api
      .rules()
      .then((list) => {
        if (alive) setRules(Array.isArray(list) ? list : []);
      })
      .catch((e) => alive && setError(e.message || "读取规则失败"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const categories = useMemo(() => {
    const seen = [];
    for (const r of rules) if (!seen.includes(r.category)) seen.push(r.category);
    return seen;
  }, [rules]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return rules.filter((r) => {
      if (cat !== "all" && r.category !== cat) return false;
      if (!needle) return true;
      return `${r.id} ${r.name} ${r.summary} ${r.mechanism}`.toLowerCase().includes(needle);
    });
  }, [rules, cat, q]);

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal wide">
        <div className="modal-head">
          <div>
            <div className="modal-title">排程依据 · 学习科学规则卡</div>
            <div className="hint" style={{ marginTop: 4 }}>
              每条规则都能在排程方块的「依据」里被引用；链接为文献检索入口（PubMed / Google Scholar）
            </div>
          </div>
          <button className="icon-btn" onClick={onClose} title="关闭">
            <Icon name="close" />
          </button>
        </div>
        <div className="modal-body">
          <div className="field-inline" style={{ marginBottom: 10 }}>
            <input
              className="input"
              placeholder="搜索规则（如 间隔重复、睡眠、番茄）"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div className="chip-row" style={{ marginBottom: 14 }}>
            <span
              className={`chip ${cat === "all" ? "rule" : ""}`}
              style={{ cursor: "pointer" }}
              onClick={() => setCat("all")}
            >
              全部 {rules.length}
            </span>
            {categories.map((c) => (
              <span
                key={c}
                className={`chip ${cat === c ? "rule" : ""}`}
                style={{ cursor: "pointer" }}
                onClick={() => setCat(c)}
              >
                {KNOWLEDGE_CATEGORY_LABEL[c] || c}
              </span>
            ))}
          </div>

          {loading ? (
            <div className="empty">读取中…</div>
          ) : error ? (
            <div className="notice warn">{error}</div>
          ) : (
            <>
              <div className="section-label">
                {filtered.length} 条规则
                {q ? `（匹配“${q}”）` : ""}
              </div>
              {filtered.map((r) => (
                <div className="rule-card" key={r.id}>
                  <div className="rule-head">
                    <span className="rule-name">{r.name}</span>
                    <span className={`badge ${STRENGTH_CLASS[r.evidence_strength] || ""}`}>
                      {EVIDENCE_LABEL[r.evidence_strength] || r.evidence_strength}
                    </span>
                    <span className="chip rule">{r.id}</span>
                  </div>
                  <div className="rule-summary">{r.summary}</div>
                  <div className="rule-detail">机制：{r.mechanism}</div>
                  {r.scheduling_effect && r.scheduling_effect.length ? (
                    <div className="rule-detail">
                      排程上会这样用：
                      <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                        {r.scheduling_effect.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {r.citations && r.citations.length ? (
                    <div className="rule-cites">
                      {(r.citations || []).map((c, i) => (
                        <span key={i} style={{ display: "block", marginTop: 3 }}>
                          [{i + 1}] {c.authors}, {c.year}. {c.title}. <i>{c.venue}</i>.{" "}
                          <a href={c.search_url} target="_blank" rel="noreferrer">
                            PubMed
                          </a>
                          <a href={c.scholar_url} target="_blank" rel="noreferrer">
                            Scholar
                          </a>
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              {!filtered.length ? <div className="empty">没有匹配的规则。</div> : null}
            </>
          )}
        </div>
        <div className="modal-foot">
          <span className="hint" style={{ marginRight: "auto" }}>
            共 {rules.length} 条规则，全部来自神经科学与认知心理学文献
          </span>
          <button className="btn btn-outline" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
