<<<<<<< HEAD
# -
=======
# 日程规划表 Demo

一个功能完整的日程规划手机App Demo，支持课程表格式的时间管理。

## 功能特性

✅ **课程表格式界面**
- 每天从 8:00 开始到 10:55 结束
- 每个时间格为 45 分钟
- 格子之间有 10 分钟休息时间

✅ **7天视图**
- 以一周为单位显示日程
- 支持前后周导航
- 显示全年日历

✅ **灵活的网格操作**
- 单击创建任务
- 多选合并任务（Ctrl/Shift + 点击）
- 拆分任务
- 编辑任务详情（标题、地点、描述）

✅ **前后端交互**
- Python Flask 后端 RESTful API
- JavaScript 前端动态交互
- SQLite 数据库持久化存储

## 技术栈

### 后端
- Python 3.x
- Flask (Web框架)
- Flask-CORS (跨域支持)
- Flask-SQLAlchemy (ORM)
- SQLite (数据库)

### 前端
- HTML5
- CSS3 (响应式设计)
- Vanilla JavaScript (ES6+)

## 项目结构

```
日程规划/
├── backend/
│   ├── app.py              # Flask 后端主文件
│   ├── requirements.txt    # Python 依赖
│   └── schedule.db        # SQLite 数据库（自动生成）
├── frontend/
│   ├── index.html         # 主页面
│   ├── styles.css         # 样式文件
│   └── app.js             # 前端逻辑
└── README.md              # 项目说明
```

## 安装与运行

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
python app.py
```

后端将在 `http://localhost:5000` 运行

### 3. 启动前端

在另一个终端窗口，使用任意 HTTP 服务器启动前端：

**方法1 - 使用 Python 内置服务器：**
```bash
cd frontend
python -m http.server 8080
```

**方法2 - 使用 Node.js http-server：**
```bash
cd frontend
npx http-server -p 8080
```

前端将在 `http://localhost:8080` 运行

### 4. 访问应用

在浏览器中打开 `http://localhost:8080`

## API 接口说明

### 任务管理

- `GET /api/tasks` - 获取所有任务
- `GET /api/tasks?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` - 获取指定日期范围的任务
- `GET /api/tasks/<id>` - 获取单个任务
- `POST /api/tasks` - 创建新任务
- `PUT /api/tasks/<id>` - 更新任务
- `DELETE /api/tasks/<id>` - 删除任务

### 任务操作

- `POST /api/tasks/merge` - 合并多个任务
- `POST /api/tasks/<id>/split` - 拆分任务

## 使用说明

### 创建任务
1. 点击任意空白时间格
2. 填写任务信息（标题、地点、描述）
3. 点击"保存"

### 合并任务
1. 按住 Ctrl/Shift 键
2. 依次点击要合并的时间格
3. 填写合并后的任务信息

### 编辑任务
1. 点击已有任务
2. 修改任务信息
3. 点击"保存"

### 拆分任务
1. 点击任务进入编辑模式
2. 点击"拆分"按钮
3. 输入要拆分的数量（2-4）

### 删除任务
1. 点击任务进入编辑模式
2. 点击"删除"按钮
3. 确认删除

## 特色功能

- 📱 响应式设计，适配手机和平板
- 🎨 现代化渐变UI设计
- 📅 周视图导航，支持快速跳转
- 🔵 今天高亮显示
- 📍 任务地点标记
- ⏱️ 灵活的时间段管理
- 💾 自动数据持久化

## 注意事项

1. 确保后端服务先启动（端口 5000）
2. 前端需要通过 HTTP 服务器访问，不能直接打开 HTML 文件
3. 首次运行会自动创建数据库文件
4. 支持现代浏览器（Chrome, Firefox, Safari, Edge）

## 开发建议

- 可以修改 `TIME_SLOTS` 配置来调整时间段
- 可以扩展数据库模型添加更多字段
- 可以添加用户认证系统
- 可以添加任务提醒功能
- 可以导出日程为 PDF/图片

## 许可证

本项目仅用于演示和学习目的。
>>>>>>> 3b023d1 (首次添加：创造原始文件)
