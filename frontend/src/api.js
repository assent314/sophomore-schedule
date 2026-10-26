/**
 * 后端地址：
 * - 浏览器里打开（http/https 同源部署）时用相对路径 ""，零配置；
 * - 安卓 APK / 桌面壳里打开时（capacitor://、file:// 等非 http 协议）用一个可配置的地址，
 *   默认取上次保存的 localStorage.api_base，否则用 APK 打包时写入的默认地址。
 */
export const DEFAULT_REMOTE_BASE =
  (typeof window !== "undefined" && window.__SCHEDULE_DEFAULT_API__) || "";

/** 是否运行在安卓/桌面壳里（Capacitor 下页面地址是 https://localhost，不能靠协议判断） */
export function isNativeShell() {
  if (typeof window === "undefined") return false;
  const cap = window.Capacitor;
  if (cap && typeof cap.isNativePlatform === "function") return cap.isNativePlatform();
  if (cap && typeof cap.getPlatform === "function") return cap.getPlatform() !== "web";
  return window.location.protocol === "capacitor:" || window.location.protocol === "file:";
}

function resolveBase() {
  if (typeof window === "undefined") return "";
  const saved = window.localStorage.getItem("api_base");
  if (saved && saved.trim()) return saved.trim().replace(/\/+$/, "");
  if (isNativeShell()) return DEFAULT_REMOTE_BASE.replace(/\/+$/, "");
  if (window.location.protocol === "http:" || window.location.protocol === "https:") return "";
  return DEFAULT_REMOTE_BASE.replace(/\/+$/, "");
}

let BASE = resolveBase();

export function setApiBase(base) {
  const clean = (base || "").trim().replace(/\/+$/, "");
  if (clean && !/^https?:\/\/[^/]+$/i.test(clean)) throw new Error("请输入完整的 http:// 或 https:// 地址");
  if (clean) window.localStorage.setItem("api_base", clean);
  else window.localStorage.removeItem("api_base");
  BASE = resolveBase();
}

export function getApiBase() {
  return BASE || (isNativeShell() ? "" : window.location.origin);
}

export function getAccessToken() {
  return window.localStorage.getItem("access_token") || "";
}

export function setAccessToken(value) {
  const clean = (value || "").trim();
  if (clean) window.localStorage.setItem("access_token", clean);
  else window.localStorage.removeItem("access_token");
}

async function request(path, options = {}) {
  if (isNativeShell() && !BASE) throw new Error("请先设置电脑后端地址和配对密钥");
  const { headers = {}, ...rest } = options;
  const token = getAccessToken();
  const res = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });
  if (res.status === 204) return null;
  let data = null;
  const text = await res.text();
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const detail = data && typeof data === "object" ? data.detail || data.message : data;
    // 后端连不上 / 地址填错时，网关或静态服务器常返回一页 HTML，直接展示会很长
    if (typeof detail === "string" && /^\s*</.test(detail)) {
      throw new Error(`无法连接后端（HTTP ${res.status}），请检查地址与电脑端服务`);
    }
    throw new Error(typeof detail === "string" ? detail : `请求失败（${res.status}）`);
  }
  return data;
}

const qs = (params = {}) => {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.set(k, v);
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
};

export const api = {
  health: () => request("/api/health"),
  pairing: () => request("/api/pairing"),
  agentCaptures: (limit = 20) => request(`/api/agent/captures${qs({ limit })}`),

  events: (params) => request(`/api/events${qs(params)}`),
  createEvent: (body) => request("/api/events", { method: "POST", body: JSON.stringify(body) }),
  updateEvent: (id, body) => request(`/api/events/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  completeEvent: (id, params) => request(`/api/events/${id}/complete${qs(params)}`, { method: "POST" }),
  deleteEvent: (id) => request(`/api/events/${id}`, { method: "DELETE" }),

  tasks: (params) => request(`/api/tasks${qs(params)}`),
  createTask: (body) => request("/api/tasks", { method: "POST", body: JSON.stringify(body) }),
  updateTask: (id, body) => request(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTask: (id) => request(`/api/tasks/${id}`, { method: "DELETE" }),

  profile: () => request("/api/profile"),
  saveProfile: (body) => request("/api/profile", { method: "PUT", body: JSON.stringify(body) }),

  feedbackList: (params) => request(`/api/feedback${qs(params)}`),
  feedback: (day) => request(`/api/feedback/${day}`),
  saveFeedback: (day, body) => request(`/api/feedback/${day}`, { method: "PUT", body: JSON.stringify(body) }),
  parseFeedback: (day, text) =>
    request(`/api/feedback/${day}/parse${qs({ text })}`, { method: "POST" }),

  previewPlan: (body) => request("/api/plan/preview", { method: "POST", body: JSON.stringify(body) }),
  applyPlan: (body) => request("/api/plan/apply", { method: "POST", body: JSON.stringify(body) }),
  commitPlan: (body) => request("/api/plan", { method: "POST", body: JSON.stringify(body) }),
  runs: (params) => request(`/api/plan/runs${qs(params)}`),

  stats: (days) => request(`/api/stats/overview${qs({ days })}`),
  progress: (days) => request(`/api/stats/progress${qs({ days })}`),

  memory: () => request("/api/memory"),
  refreshMemory: (useLlm = true) =>
    request(`/api/memory/refresh${qs({ use_llm: useLlm })}`, { method: "POST" }),

  rules: () => request("/api/knowledge/rules"),
  rule: (id) => request(`/api/knowledge/rules/${id}`),
  knowledgeMeta: () => request("/api/knowledge/meta"),

  settings: () => request("/api/settings"),
  saveSettings: (body) => request("/api/settings", { method: "PUT", body: JSON.stringify(body) }),
  testSettings: () => request("/api/settings/test", { method: "POST" }),
};
