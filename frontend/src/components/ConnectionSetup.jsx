import React, { useState } from "react";
import { api, getAccessToken, getApiBase, isNativeShell, setAccessToken, setApiBase } from "../api.js";

export default function ConnectionSetup({ onClose }) {
  const [address, setAddress] = useState(getApiBase());
  const [token, setToken] = useState(getAccessToken());
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState("");

  const connect = async () => {
    setTesting(true);
    setError("");
    try {
      if (isNativeShell() && !address.trim()) throw new Error("请填写电脑的后端地址");
      setApiBase(address);
      setAccessToken(token);
      await api.health();
      window.location.reload();
    } catch (e) {
      setError(e.message || "连接失败");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="modal-overlay connection-overlay">
      <div className="modal connection-modal">
        <div className="modal-head">
          <div className="modal-title">连接日程电脑</div>
          {onClose ? <button className="icon-btn" onClick={onClose} title="关闭">×</button> : null}
        </div>
        <div className="modal-body">
          <p>在电脑上启动日程规划，然后在「习惯与设置 → AI 设置」查看配对密钥。</p>
          <div className="field">
            <label>电脑地址</label>
            <input className="input" value={address} onChange={(e) => setAddress(e.target.value)}
              placeholder="http://192.168.1.10:8000" autoComplete="url" />
          </div>
          <div className="field">
            <label>配对密钥</label>
            <input className="input" type="password" value={token} onChange={(e) => setToken(e.target.value)}
              placeholder="从电脑设置复制" autoComplete="off" />
          </div>
          {error ? <div className="notice warn">{error}</div> : null}
        </div>
        <div className="modal-foot">
          <button className="btn btn-primary" disabled={testing} onClick={connect}>
            {testing ? "正在连接…" : "保存并连接"}
          </button>
        </div>
      </div>
    </div>
  );
}
