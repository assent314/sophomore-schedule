"""DeepSeek API 客户端（OpenAI 兼容 chat/completions，JSON 模式）。"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx

from . import config


class LLMError(RuntimeError):
    """LLM 调用失败。"""


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str) -> dict[str, Any]:
    """从模型输出中尽量稳健地抠出 JSON 对象。"""
    text = (text or "").strip()
    if not text:
        raise LLMError("empty response")
    m = _FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            # 常见问题：尾逗号
            candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                data = json.loads(candidate)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError as exc:
                raise LLMError(f"JSON 解析失败: {exc}") from exc
    raise LLMError("响应中没有 JSON 对象")


class DeepSeekClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 timeout: float | None = None) -> None:
        self.api_key = (api_key if api_key is not None else config.DEEPSEEK_API_KEY).strip()
        self.base_url = (base_url or config.DEEPSEEK_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else float(config.DEFAULT_SETTINGS["llm_timeout_seconds"])

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    async def models(self) -> list[str]:
        if not self.configured:
            raise LLMError("未配置 API Key")
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(self._url("/models"), headers={"Authorization": f"Bearer {self.api_key}"})
        if resp.status_code >= 400:
            raise LLMError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        return [m.get("id", "") for m in data.get("data", []) if isinstance(m, dict)]

    async def chat_json(
        self,
        system: str,
        user: str,
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        retries: int = 2,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """返回 (JSON 字典, usage 信息)。失败抛 LLMError。"""
        if not self.configured:
            raise LLMError("未配置 DeepSeek API Key（可在设置页填写）")
        payload = {
            "model": model or config.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(self._url("/chat/completions"), json=payload, headers=headers)
                if resp.status_code >= 400:
                    body = resp.text[:500]
                    # JSON 模式不被支持时降级重试
                    if resp.status_code == 400 and "response_format" in body:
                        payload.pop("response_format", None)
                        try:
                            async with httpx.AsyncClient(timeout=self.timeout) as client:
                                resp = await client.post(
                                    self._url("/chat/completions"), json=payload, headers=headers
                                )
                        except httpx.HTTPError as exc:
                            raise LLMError(f"网络错误: {exc}") from exc
                    if resp.status_code >= 400:
                        raise LLMError(f"HTTP {resp.status_code}: {body}")
                data = resp.json()
                choice = (data.get("choices") or [{}])[0]
                content = (choice.get("message") or {}).get("content") or ""
                parsed = extract_json(content)
                usage = data.get("usage") or {}
                return parsed, {
                    "model": data.get("model") or payload["model"],
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
            except (httpx.HTTPError, LLMError, asyncio.TimeoutError) as exc:
                last_err = exc
                if attempt < retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
        raise LLMError(str(last_err) if last_err else "未知错误")
