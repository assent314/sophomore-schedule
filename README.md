# 日程规划

面向电脑浏览器与 Android App 的个人学习日程工具。React 前端展示日历、待办、反馈、统计和设置；FastAPI 后端在 SQLite 中保存数据，用规则引擎或 DeepSeek API 生成排程。Codex、DeepSeek Harness 等 Agent 可通过同一个本地 MCP 接口采集聊天中明确的精力与任务信息，并触发日程调整。

![周视图](docs/screenshots/week.png)

## 主要功能

- 自然语言生成日程预览，确认后按**服务端保存的预览**应用；日程或设置变化、预览超过 30 分钟时要求重新生成。
- 日／周／月视图、待办池、课程表导入、拖拽编辑、完成状态、每日睡眠与精力反馈、28 天统计与记忆摘要。
- 排程保留手动事件、课程、锁定安排、已完成和已过去的方块。规则引擎会参考当天精力、睡眠、长期精力曲线和机动缓冲；模型不可用时可离线排程。
- 手机 App 首次启动先连接电脑；手机与电脑读取同一后端数据，并在前台与间隔同步。
- Agent MCP 提供读取日程、采集事实和查看调整记录三个工具；只持久化结构化事实，不保存完整聊天原文。

完整组件关系、数据流与边界见 [架构说明](docs/ARCHITECTURE.md)。

## 启动

### 源码启动

需要 Python 3.10+、Node.js 18+ 与 pnpm。双击 `start.bat` 会建立虚拟环境、安装后端依赖、首次构建前端并在服务就绪后打开浏览器。也可以手动运行：

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
pnpm install
pnpm build
cd ..
.venv\Scripts\python.exe backend\launcher.py
```

默认只监听本机 `127.0.0.1:8000`。不配置 API Key 时走规则引擎。若使用 DeepSeek，在 `backend\.env`（从 `backend\.env.example` 复制）填写 `DEEPSEEK_API_KEY`，或在软件的「习惯与设置 → AI 设置」中填写。

### 桌面可执行程序

运行 `tools\build_exe.bat` 生成 `日程规划.exe`；构建前先执行 `.venv\Scripts\python.exe -m pip install pyinstaller pillow`。源码与同目录的 exe 都使用仓库根目录的 `data\schedule.db`。exe 单独移到别处后，数据位于 exe 同级的 `data\`。运行日志为 `data\app.log`。构建产物和私人数据不提交到 Git。

### 手机 App

1. 在电脑的 `backend\.env` 中设 `SCHEDULE_HOST=0.0.0.0`，重启软件，并允许 Windows 防火墙的专用网络访问。
2. 电脑打开「习惯与设置 → AI 设置」，复制**手机配对密钥**。
3. 用 `tools\build_apk.bat` 构建 Android APK；首次打开 App 时输入电脑的局域网地址（例如 `http://192.168.1.10:8000`）及配对密钥。

电脑和手机应在同一可信 WiFi。HTTP 局域网连接虽有配对密钥，传输仍未加密；若需保护传输，请配置受手机信任、且证书名称与访问地址匹配的 `SCHEDULE_TLS_CERTFILE` 和 `SCHEDULE_TLS_KEYFILE`，然后用 HTTPS 地址连接。密钥保存在电脑 `data\access-token.txt` 与手机本地存储，勿加入仓库或分享。也可在手机浏览器打开后端地址，再在连接提示中填配对密钥。修改地址或密钥可从连接提示／设置页进入。

APK 构建需要 JDK 17 和 Android SDK（platforms;android-34、build-tools;34.0.0）。`frontend/android` 是 Capacitor 工程。手机 App 不运行本地后端，电脑必须保持开机和服务运行。

## Agent 接入：Codex 与 DeepSeek Harness

先运行 `tools\setup_agent.bat`。本地 MCP 入口为 `backend\agent_mcp.py`，也可执行 `tools\agent_mcp.bat`。在 Codex 的 MCP 配置中添加 stdio 服务（路径按实际克隆位置修改）：

```toml
[mcp_servers.schedule]
command = "D:\\r日程规划\\.venv\\Scripts\\python.exe"
args = ["D:\\r日程规划\\backend\\agent_mcp.py"]
```

DeepSeek Harness 在启用 `@deepseek-ai/dsh-mcp-client` 的插件清单中添加：

```yaml
- id: mcp-schedule
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: schedule
    transport: stdio
    command: 'D:\r日程规划\.venv\Scripts\python.exe'
    args: ['D:\r日程规划\backend\agent_mcp.py']
    toolCallTimeoutMs: 200000
```

两个平台都会得到 `get_schedule_context`、`capture_chat_context`、`list_schedule_captures`。本仓库的 [AGENTS.md](AGENTS.md) 和 MCP 服务说明约定：仅在用户明确谈到睡眠、精力、任务、期限或时间冲突时采集；一次疲劳不改变长期曲线；重复消息用 `message_id` 去重；调整后反馈实际结果。软件侧「Agent 调整记录」可核对写入的事实和对应排程。

**接入边界：**MCP 需要在实际使用的 Agent 环境中注册并启用。它不会在后台监听全部 Codex／DeepSeek 聊天，也不会自动读取未连接会话。当前自动采集由已连接的 Agent 在相关对话中调用工具触发；无法保证所有第三方 Agent 始终调用。其他 Agent 可调用 `POST /api/agent/capture`，局域网访问须使用 `Authorization: Bearer <配对密钥>`。请求字段详见本机 `/docs`。

## 数据、配置与开发

- 数据库：`data\schedule.db`；首次升级旧库时在 `data\backups\` 留存升级前快照。运行中备份应使用 SQLite 备份 API 或先停服务，避免只复制主文件遗漏 WAL 中的事务。
- 配置：`backend\.env.example` 给出环境变量。模型、时区、缓冲比例和超时也可在 UI 中保存到数据库设置；数据库值优先。监听地址和 TLS 文件需在启动前设定。
- 课程导入：`backend\scripts\import_courses.py --student-pdf <PDF> --dry-run` 先预览，确认后去掉 `--dry-run`。支持 `--term-start` 与 `--period-json` 调整学期和节次时间。
- 开发前端：`cd frontend && pnpm dev`；后端仍在 8000 端口，Vite 代理 `/api`。
- 接口文档：软件启动后访问 `http://127.0.0.1:8000/docs`；启用 TLS 时改用 HTTPS。
- 验证：`.venv\Scripts\python.exe -m pytest backend\tests -q` 与 `cd frontend && pnpm build`。真实模型联调需要自己的 API Key，可运行 `backend\scripts\smoke_llm.py`。

旧版 Flask 原型已移除；当前入口是 `backend\app\main.py`，规则引擎位于 `backend\app\engine.py`。
