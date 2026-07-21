# MLab

MLab 是一个 Vue 3 + FastAPI 构建的 AI 工作空间，包含真实流式对话、助手市场、工具导航、任务、文稿、资源、长期记忆与模型设置。

## 功能

- OpenAI-compatible 模型接入，支持自定义 Base URL、API Key、模型名称和函数调用。
- POST SSE 真实流式消息，支持停止、编辑重发、重新生成、代码高亮、失败状态、历史持久化和 Token 用量。
- 用户注册登录、Refresh Token 轮换、账户数据隔离。
- API Key 服务端加密保存，接口只返回掩码。
- 助手创建/编辑/删除、市场安装、开场白、模型参数与知识文件；工具搜索、分类、收藏、内置执行和外链导航。
- 任务模板、AI 拆解、文稿自动保存与版本、资源、可控向量长期记忆。
- 浅色/深色/系统主题，适配桌面、平板和移动端。

## 最快启动

需要 Docker Desktop 和 Docker Compose 2。

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

把两条命令的输出分别写入 `.env` 的 `APP_SECRET_KEY` 和 `CREDENTIAL_ENCRYPTION_KEY`，然后启动：

```powershell
docker compose up --build
```

打开 <http://localhost:8080>，注册后进入“设置 -> API 密钥”：

1. 填写供应商名称，如 `deepseek`。
2. 填写 Base URL，如 `https://api.deepseek.com/v1`。
3. 填写 API Key 和模型名，如 `deepseek-chat`。
4. 点击“验证并保存”，随后返回首页开始对话。

### 无 Key 验收模式

如果暂时没有模型 API Key，可先使用服务端 Mock Provider 验证完整业务链路。它会返回确定性的流式回复，并覆盖内置计算器、任务拆解和文稿 AI 操作：

```dotenv
APP_ENV=development
MOCK_AI_ENABLED=true
```

使用 Mock 模式时不需要填写 API Key；该模式仅允许在开发环境启用，生产环境会拒绝启动。验收完成后将其改为 `false`，再在设置页保存真实的 OpenAI-compatible 凭据。

也可以在根目录创建 `.env`，以系统默认凭据运行：

```dotenv
APP_SECRET_KEY=replace-with-a-long-random-value
CREDENTIAL_ENCRYPTION_KEY=replace-with-a-valid-fernet-key
AI_BASE_URL=https://api.deepseek.com/v1
AI_API_KEY=your-api-key
DEFAULT_AI_MODEL=deepseek-chat
MOCK_AI_ENABLED=false
```

生产环境必须修改 `APP_SECRET_KEY` 和 `CREDENTIAL_ENCRYPTION_KEY`。

## 本地开发

### 后端

需要 Python 3.12。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".\backend[dev]"
python -m uvicorn app.main:app --app-dir backend --reload
```

未配置 `DATABASE_URL` 时使用当前启动目录下的 `data/mlab.db`，上传文件写入 `data/uploads`。API 文档位于 <http://localhost:8000/docs>。

### 前端

需要 Node.js 22 与 pnpm 10。

```powershell
pnpm --dir frontend install
pnpm --dir frontend dev
```

打开 <http://localhost:5173>，开发服务器会把 `/api` 代理到后端。

## 数据库迁移

开发启动会自动创建缺失表，正式环境应通过 Alembic 管理结构：

```powershell
Set-Location backend
alembic upgrade head
```

创建新迁移：

```powershell
alembic revision --autogenerate -m "描述"
```

## 质量检查

```powershell
python -m ruff check backend
python -m pytest backend/tests
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
```

## 目录

```text
backend/app/api/v1/  HTTP 接口
backend/app/ai/      模型网关与流协议
backend/app/models/  数据实体
backend/app/services 业务用例
backend/app/tasks/   后台队列
frontend/src/api/    强类型请求与 SSE
frontend/src/stores/ 页面状态
frontend/src/views/  业务页面
frontend/src/styles/ Design Tokens 与响应式样式
```

## 第三方工具边界

工具库中的 Midjourney、Suno、Cursor 等独立产品默认是导航入口。它们有独立账户和 API，不能由一个聊天模型 Key 代替授权。MLab 自身的聊天、助手、任务、文稿和记忆功能只需要一个 OpenAI-compatible 模型凭据。

## 生产建议

- 使用云 PostgreSQL、云 Redis 和 S3 兼容对象存储。
- API 与 Worker 独立扩容；外部负载均衡必须关闭 SSE 响应缓冲。
- 使用 KMS/Secret Manager 提供应用密钥，不要把 `.env` 提交到 Git。
- 配置 HTTPS、精确 CORS 域名、数据库备份、Sentry/Prometheus 和日志保留策略。
- 多实例部署时将生成中止注册表从进程内存迁移到 Redis Pub/Sub。

详细设计见 [PROJECT_PLAN.md](./PROJECT_PLAN.md)，实施状态见 [task.md](./task.md)。
