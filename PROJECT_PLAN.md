# MLab AI 工具与导航平台：推荐方案与实施计划

> 目标：交付一套可直接运行、可继续扩展、接入模型 API Key 后即可使用核心 AI 能力的全栈项目。前端使用 Vue 3，后端使用 Python + FastAPI，整体视觉和交互参考用户提供的 LobeChat 风格 UI。

## 1. 项目定位与边界

MLab 是一个以 AI 对话为首页入口，集助手、任务、文稿、AI 工具导航、资源和长期记忆于一体的工作台。

### 1.1 首期必须可用的能力

1. AI 对话：首页新建对话、历史会话、多轮上下文、流式输出、停止生成、重新生成、编辑后重发、复制消息、Markdown/代码高亮。
2. 多模型接入：兼容 OpenAI API 协议，支持 OpenAI、DeepSeek、通义千问、Moonshot、智谱等兼容端点，并保留原生适配器扩展能力。
3. 助手系统：创建、编辑、删除助手；配置系统提示词、模型、参数、开场白和知识文件；助手市场一键安装。
4. 工具库：分类、搜索、收藏、评分展示、外链跳转；对于有开放 API 的工具可通过后端适配器接入对话。
5. 任务：创建、编辑、完成、删除任务；支持模板快速创建；任务可调用模型生成计划或总结。
6. 文稿：新建、编辑、自动保存、AI 改写/续写/总结、版本记录。
7. 记忆：用户可查看、编辑、关闭和删除记忆；聊天时按需注入相关记忆。
8. 设置：个人资料、主题、默认助手、模型供应商、API Key、模型参数。
9. 用户与权限：邮箱密码注册/登录、JWT 会话、个人数据隔离。
10. 工程化：Docker Compose 一键启动、数据库迁移、健康检查、日志、测试和示例数据。

### 1.2 必须明确的产品边界

- 一个大模型 API Key 只能驱动大模型相关能力，不能直接调用 Midjourney、Suno、Cursor 等独立产品。
- 第三方工具分为三种接入方式：`external_link`（外链）、`openai_tool`（模型 function calling）、`provider_api`（第三方 API 适配器）。
- 首期工具库对无公开 API 的产品提供导航、收藏和跳转；有 API 且已配置凭据的工具才显示“在对话中使用”。
- 支付订阅仅预留领域模型与接口，不在首期接真实支付渠道。管理订阅按钮先展示当前计划与额度，不制造虚假支付流程。

## 2. 推荐技术方案

### 2.1 前端

| 类别 | 选型 | 理由 |
| --- | --- | --- |
| 框架 | Vue 3 + TypeScript + Vite | 类型安全、开发体验好、部署简单 |
| 路由 | Vue Router | 官方方案，页面与鉴权守卫清晰 |
| 状态 | Pinia | 管理用户、会话、设置和 UI 状态 |
| 请求 | Axios + 封装 API Client | 统一鉴权、错误处理、刷新 Token；SSE 单独封装 |
| 样式 | Tailwind CSS + CSS Variables | 快速还原 UI，同时保留主题令牌和可维护性 |
| 组件 | Headless UI 思路，自建业务组件 | 精确匹配参考图，避免重型 UI 库造成视觉偏差 |
| 图标 | lucide-vue-next | 统一、轻量、语义明确 |
| 编辑器 | Tiptap | 文稿富文本与 AI 操作扩展成熟 |
| Markdown | markdown-it + Shiki | 稳定渲染、代码高亮和复制 |
| 表单校验 | vee-validate + Zod | 复用 schema，错误反馈一致 |
| 测试 | Vitest + Vue Test Utils + Playwright | 覆盖单元、组件和关键用户流程 |

不建议把 Element Plus 作为主 UI 框架。参考图的界面高度定制且克制，自建薄组件层更容易保证桌面端与移动端的一致性。

### 2.2 后端

| 类别 | 选型 | 理由 |
| --- | --- | --- |
| Web | FastAPI + Pydantic v2 | 异步、类型清晰、自动 OpenAPI |
| ORM | SQLAlchemy 2.0 Async | 成熟、类型支持好、便于领域分层 |
| 迁移 | Alembic | 数据库结构可追踪、可回滚 |
| 数据库 | PostgreSQL 16 + pgvector | 业务数据、全文搜索和向量记忆统一管理 |
| 缓存/队列 | Redis 7 | 限流、短期缓存、后台任务中间件 |
| 后台任务 | ARQ | 与 asyncio/FastAPI 配合轻量，适合标题、摘要、嵌入任务 |
| 模型 SDK | LiteLLM 或自建 OpenAI-compatible adapter | 统一多供应商调用、流式输出和错误格式 |
| 文件 | 本地存储（开发）/ S3 兼容存储（生产） | 本地开箱即用，生产可切 MinIO/OSS |
| 鉴权 | JWT Access + Refresh Token | 前后端分离常规方案，支持 Token 轮换 |
| 测试 | pytest + pytest-asyncio + httpx | 覆盖服务层和 API 集成测试 |

### 2.3 部署

- 开发环境：Node.js 22、Python 3.12、PostgreSQL 16、Redis 7。
- 推荐启动方式：`docker compose up --build`，默认包含 `web`、`api`、`worker`、`postgres`、`redis`。
- 生产环境：Nginx/Caddy 反向代理，前端静态部署，API 与 Worker 独立容器。
- 默认数据库与 Redis 不暴露公网端口；API Key 只在后端加密保存，不返回完整明文。

## 3. 总体架构

```mermaid
flowchart LR
    U["Browser / Vue 3"] -->|"REST + SSE"| A["FastAPI API"]
    A --> S["Application Services"]
    S --> DB["PostgreSQL + pgvector"]
    S --> R["Redis"]
    S --> FS["Local / S3 Storage"]
    S --> G["AI Provider Gateway"]
    G --> O["OpenAI-compatible Providers"]
    G --> T["Tool Adapters"]
    R --> W["ARQ Worker"]
    W --> DB
    W --> G
```

采用模块化单体，而不是一开始拆微服务。当前业务规模下，模块化单体更容易部署、调试和保持事务一致性；模型网关、后台任务和文件存储通过接口隔离，未来可独立拆分。

## 4. 前端信息架构与页面

### 4.1 全局布局

- 桌面端：固定左侧栏 `240px`，右侧内容区自适应。
- 平板：侧栏折叠为窄图标栏。
- 手机：侧栏改为抽屉；聊天输入区固定底部；卡片单列。
- 全局支持浅色、深色、跟随系统三种主题。
- 所有颜色、阴影、边框、圆角、字号和间距使用 Design Tokens，不在组件中散落硬编码。

### 4.2 路由规划

| 路由 | 页面 | 核心能力 |
| --- | --- | --- |
| `/` | AI 首页 | 欢迎态、推荐任务、快速输入、模型选择 |
| `/chat/:id` | 对话页 | 消息流、SSE、附件、重试、停止、工具调用 |
| `/tasks` | 任务 | 筛选、状态管理、模板、AI 拆解 |
| `/documents` | 文稿 | 列表、编辑器、自动保存、AI 写作 |
| `/assistants` | 助手市场 | 搜索、分类、详情、安装 |
| `/assistants/new` | 创建助手 | Prompt、模型、参数、知识库配置 |
| `/tools` | 工具库 | 搜索、分类、收藏、跳转/接入 |
| `/resources` | 资源 | 提示词、模板、文件和知识资料 |
| `/memories` | 记忆 | 查看、编辑、删除、全局开关 |
| `/settings/profile` | 个人资料 | 名称、头像、默认助手 |
| `/settings/models` | 模型偏好 | 供应商、模型、参数、连通性测试 |
| `/settings/api-keys` | API 密钥 | 新增、校验、掩码展示、删除 |
| `/settings/appearance` | 外观主题 | 主题、语言、密度 |
| `/login`、`/register` | 认证 | 登录、注册、刷新会话 |

### 4.3 关键组件拆分

```text
AppShell
├── Sidebar
│   ├── UserMenu
│   ├── GlobalSearch
│   ├── PrimaryNav
│   ├── RecentChats
│   ├── AssistantList
│   └── UtilityNav
└── MainContent
    ├── ChatWelcome / ChatThread
    ├── Composer
    │   ├── AttachmentPicker
    │   ├── CapabilityMenu
    │   ├── ModelSelector
    │   └── SendButton
    └── FeaturePage
```

业务页面只组合组件；请求、状态和流式解析放在 composables/stores；API 类型集中生成或维护，避免组件直接拼 URL。

## 5. 后端模块设计

```text
backend/app/
├── api/                 # 路由、依赖注入、统一响应与异常映射
│   └── v1/
├── core/                # 配置、日志、安全、限流、生命周期
├── db/                  # Session、Base、迁移辅助
├── models/              # SQLAlchemy 持久化模型
├── schemas/             # Pydantic 请求/响应模型
├── repositories/        # 数据访问，仅处理查询与持久化
├── services/            # 用例编排、权限与事务边界
├── ai/                  # Provider、流式协议、工具调用、Token 统计
│   ├── providers/
│   └── tools/
├── tasks/               # ARQ 后台任务
└── main.py
```

分层约束：

- API 层不写业务规则，只做参数解析、鉴权和响应映射。
- Service 层负责业务流程、事务和权限。
- Repository 层不依赖 FastAPI。
- AI Provider 使用统一协议，业务层不感知具体厂商 SDK。
- 配置全部来自环境变量；密钥和敏感信息不写入日志。

## 6. 核心数据模型

所有主键使用 UUID；所有业务表带 `created_at`、`updated_at`；用户数据查询强制带 `user_id`。

| 表 | 关键字段 | 说明 |
| --- | --- | --- |
| `users` | email, password_hash, display_name, avatar_url, status | 用户账户 |
| `refresh_tokens` | user_id, token_hash, expires_at, revoked_at | 可撤销登录会话 |
| `provider_credentials` | user_id, provider, base_url, encrypted_api_key | 加密后的供应商凭据 |
| `model_configs` | user_id, provider, model_id, alias, params, is_default | 用户模型配置 |
| `assistants` | owner_id, name, description, system_prompt, visibility | 私有/市场助手 |
| `assistant_installations` | user_id, assistant_id, config_override | 已安装助手与个性化配置 |
| `conversations` | user_id, assistant_id, title, model_config_id, archived_at | 会话 |
| `messages` | conversation_id, role, content, status, token_usage, parent_id | 消息与重试分支 |
| `message_attachments` | message_id, file_id, type, metadata | 消息附件 |
| `tool_definitions` | name, slug, category, access_type, config_schema | 工具目录定义 |
| `tool_favorites` | user_id, tool_id | 用户收藏 |
| `tool_executions` | user_id, message_id, tool_id, input, output, status | 调用审计 |
| `tasks` | user_id, title, content, status, priority, due_at | 任务 |
| `task_templates` | title, description, prompt_template, is_system | 首页推荐模板 |
| `documents` | user_id, title, content_json, content_text, current_version | 文稿 |
| `document_versions` | document_id, version, snapshot, created_by | 版本历史 |
| `files` | user_id, storage_key, mime_type, size, sha256 | 上传文件 |
| `memories` | user_id, content, source_message_id, embedding, enabled | 可控长期记忆 |
| `resources` | owner_id, type, title, content, visibility | 提示词/模板/知识资源 |
| `usage_records` | user_id, provider, model, input_tokens, output_tokens, cost | 用量统计 |

建议首期保留 `JSONB` 存储模型参数、工具 schema 和结构化编辑器内容；检索字段与权限字段仍使用明确列，不把整个实体塞进 JSON。

## 7. API 设计

统一前缀：`/api/v1`。错误格式：

```json
{
  "error": {
    "code": "MODEL_AUTH_FAILED",
    "message": "模型供应商鉴权失败",
    "request_id": "uuid",
    "details": null
  }
}
```

### 7.1 主要接口

| 方法与路径 | 用途 |
| --- | --- |
| `POST /auth/register` | 注册 |
| `POST /auth/login` | 登录并签发 Token |
| `POST /auth/refresh` | Access Token 轮换 |
| `GET /users/me`、`PATCH /users/me` | 当前用户资料 |
| `GET /providers` | 支持的供应商与模型能力 |
| `POST /provider-credentials` | 保存加密 API Key |
| `POST /provider-credentials/test` | 测试模型连接 |
| `GET /model-configs`、`POST /model-configs` | 模型配置 |
| `GET /conversations`、`POST /conversations` | 会话列表/新建 |
| `GET /conversations/{id}`、`DELETE /conversations/{id}` | 会话详情/删除 |
| `POST /conversations/{id}/messages` | 发送消息并建立 SSE 流 |
| `POST /messages/{id}/stop` | 停止生成 |
| `POST /messages/{id}/regenerate` | 重新生成 |
| `GET /assistants`、`POST /assistants` | 助手市场/创建 |
| `POST /assistants/{id}/install` | 安装助手 |
| `GET /tools`、`POST /tools/{id}/favorite` | 工具搜索/收藏 |
| `GET /tasks`、`POST /tasks`、`PATCH /tasks/{id}` | 任务管理 |
| `GET /documents`、`POST /documents`、`PATCH /documents/{id}` | 文稿管理 |
| `POST /documents/{id}/ai-actions` | 改写、续写、总结 |
| `GET /memories`、`PATCH /memories/{id}`、`DELETE /memories/{id}` | 记忆控制 |
| `POST /files` | 文件上传 |
| `GET /search?q=` | 跨会话、文稿、任务和资源搜索 |

列表接口统一游标分页；所有修改接口支持明确的 401/403/404/409/422 响应。

### 7.2 SSE 流式协议

使用 `text/event-stream`，事件统一为：

```text
event: message.start
data: {"message_id":"..."}

event: message.delta
data: {"content":"增量文本"}

event: tool.call
data: {"tool_call_id":"...","name":"search","arguments":{}}

event: tool.result
data: {"tool_call_id":"...","result":{}}

event: message.done
data: {"usage":{"input_tokens":10,"output_tokens":20}}

event: error
data: {"code":"PROVIDER_TIMEOUT","message":"..."}
```

客户端按事件类型更新状态，不解析厂商原始流。断开连接时后端取消上游请求；已生成内容仍落库，状态标记为 `stopped` 或 `failed`。

## 8. 模型与工具网关

### 8.1 Provider 接口

```python
class ChatProvider(Protocol):
    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[ChatEvent]: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def validate_credentials(self) -> CredentialCheck: ...
```

首期实现 `OpenAICompatibleProvider`，通过 `base_url + api_key + model` 覆盖多数国内外模型。特有能力再增加独立适配器，避免大量 `if provider == ...`。

### 8.2 API Key 策略

- 支持系统级 Key（服务器环境变量）和用户级 Key（数据库加密）两种模式。
- 优先级：用户指定凭据 > 系统默认凭据。
- 数据库使用 AES-GCM/Fernet 类方案加密，主密钥来自 `CREDENTIAL_ENCRYPTION_KEY`。
- API 响应只返回掩码，如 `sk-****3x9a`；日志过滤 Authorization 和 Key。
- 保存前允许调用一次供应商 models/chat 接口进行连通性验证。

### 8.3 记忆策略

1. 对话结束后由 Worker 提取候选记忆。
2. 过滤敏感内容与低价值临时信息。
3. 写入文本和 embedding，默认向用户可见且可删除。
4. 新对话按用户、相似度和启用状态检索少量记忆。
5. 将记忆作为独立上下文块注入，并设置 Token 上限。

不自动保存密码、API Key、身份证号、银行卡等敏感信息。

## 9. 推荐目录结构

```text
MLab/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── assets/
│   │   ├── components/{base,layout,chat,business}/
│   │   ├── composables/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── styles/
│   │   ├── types/
│   │   ├── utils/
│   │   └── views/
│   ├── tests/
│   └── package.json
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
├── deploy/
│   ├── nginx/
│   └── scripts/
├── docs/
├── .env.example
├── compose.yaml
├── Makefile
└── README.md
```

## 10. 环境变量

```dotenv
APP_ENV=development
APP_SECRET_KEY=replace-with-random-secret
CREDENTIAL_ENCRYPTION_KEY=replace-with-fernet-compatible-key
DATABASE_URL=postgresql+asyncpg://mlab:mlab@postgres:5432/mlab
REDIS_URL=redis://redis:6379/0

# 系统默认模型，可只配置一个 OpenAI-compatible 供应商
DEFAULT_AI_PROVIDER=deepseek
DEFAULT_AI_MODEL=deepseek-chat
AI_API_KEY=
AI_BASE_URL=https://api.deepseek.com/v1

# 文件存储：local 或 s3
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=/data/uploads
S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=

JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=30
CORS_ORIGINS=http://localhost:5173
```

`.env.example` 只放占位值；真实 `.env` 必须在 `.gitignore` 中。

## 11. 安全、稳定性与可观测性

- 密码使用 Argon2id；Refresh Token 只存哈希并支持撤销。
- API 做用户级限流、上传大小限制、MIME/扩展名双重校验。
- Markdown 输出默认消毒，禁止任意 HTML 和脚本执行。
- 工具调用使用允许列表，参数按 JSON Schema 校验；不执行模型输出的任意代码或 Shell。
- CORS 生产环境使用精确域名，禁止通配凭据。
- 每个请求生成 `request_id`；结构化 JSON 日志关联用户、会话和上游耗时，但不记录消息正文和密钥。
- AI 调用设置连接、首 Token、总时长三类超时；只对安全的瞬时错误做有限重试。
- 用量按供应商、模型、用户记录 Token；价格未知时只记录 Token，不伪造成本。
- 提供 `/health/live` 与 `/health/ready`，就绪检查数据库和 Redis。

## 12. 测试策略

### 12.1 后端

- 单元测试：权限判断、Token 轮换、模型参数合并、SSE 事件转换、记忆过滤。
- 集成测试：注册登录、会话隔离、消息流、助手安装、任务/文稿 CRUD、Key 掩码。
- Provider 使用录制或 Fake Adapter，不在 CI 中消耗真实 API。
- 数据库迁移测试：空库升级到最新版本、主要约束生效。

### 12.2 前端

- 组件测试：Composer、ModelSelector、MessageItem、Sidebar、表单错误态。
- Store 测试：登录刷新、流式消息拼接、中止生成、乐观更新回滚。
- Playwright：注册登录 -> 配置 Key -> 新建对话 -> 收到流式回复；安装助手；创建任务；编辑文稿。
- 视觉检查：1440×900、1920×1080、768×1024、390×844；重点验证侧栏、输入框、长文本和弹窗不重叠。

## 13. 分阶段实施计划

以下按一个开发者的有效工作日估算，实际时间取决于 UI 还原精度和接入的模型供应商数量。

### 阶段 0：脚手架与规范（1 天）

- 建立前后端工程、Docker Compose、环境变量和 Makefile。
- 配置 ESLint、Prettier、Ruff、MyPy、Pytest、提交前检查。
- 建立统一错误格式、日志、数据库 Session 和基础 Design Tokens。

验收：一条命令启动前端、API、Worker、PostgreSQL、Redis；健康检查通过。

### 阶段 1：认证、布局与设置（2-3 天）

- 用户注册登录、JWT 刷新、个人资料。
- 还原响应式侧栏、导航、设置页和主题。
- Provider 凭据加密存储、模型配置、连通性测试。

验收：用户能登录、保存 Key、选择默认模型；用户之间数据不可见。

### 阶段 2：核心聊天闭环（3-4 天）

- 会话/消息数据模型与历史列表。
- OpenAI-compatible Provider、SSE 流式输出、中止/重试/错误状态。
- Markdown、代码高亮、复制、消息编辑、自动标题。
- 首页欢迎态、推荐模板、模型选择与附件入口。

验收：配置 API Key 后可稳定完成多轮流式对话，刷新后历史完整恢复。

### 阶段 3：助手与工具体系（3 天）

- 助手创建、编辑、安装、市场搜索和分类。
- 工具库搜索、分类、收藏、外链与 Tool Adapter 协议。
- 至少实现 2 个内置工具示例，如时间/计算器或受控网页检索（是否启用取决于外部 API）。

验收：安装的助手可直接发起对话；模型能以统一协议调用已启用工具。

### 阶段 4：任务、文稿、资源与记忆（4-5 天）

- 任务 CRUD、模板和 AI 拆解。
- Tiptap 文稿、自动保存、版本历史、AI 写作操作。
- 资源列表与跨模块搜索。
- pgvector 记忆提取、检索、注入和用户控制。

验收：参考图中的主要导航均有真实数据与完整操作闭环，不存在纯静态占位页。

### 阶段 5：质量与交付（2-3 天）

- 完成响应式、加载/空/错误/离线状态和无障碍细节。
- 补齐关键测试、迁移测试、限流与日志脱敏。
- 编写 README、部署文档、API 文档和常见故障排查。
- 在四种视口完成视觉回归和端到端验收。

验收：新环境按 README 可在 15 分钟内启动；填入 Key 后核心功能可用；自动化测试通过。

总估算：15-19 个有效工作日。若首版只做“聊天 + 助手 + 工具导航 + 设置”，可在 8-11 个有效工作日形成可交付 MVP。

## 14. 代码质量约定

- 前后端开启严格类型检查；禁止无原因的 `any` 和裸 `except`。
- 公共组件只抽离稳定复用的 UI/行为，不为单次使用制造抽象。
- 注释解释约束、取舍和非直观逻辑，不逐行复述代码。
- 后端函数保持单一职责；事务边界放在 Service 层。
- API schema 与 ORM model 分离，禁止直接返回 ORM 实体。
- 使用 Conventional Commits；每个阶段保持数据库迁移、实现和测试同步提交。

## 15. 首期验收清单

- [ ] `docker compose up --build` 可启动全部服务。
- [ ] 可注册、登录、退出并自动刷新 Token。
- [ ] 可配置 OpenAI-compatible `base_url`、`api_key`、`model` 并验证连接。
- [ ] AI 回复为真实 SSE 流，不是假打字机效果。
- [ ] 支持停止、重试、编辑重发，异常时保留已生成内容。
- [ ] 会话、助手、任务、文稿、记忆均持久化并严格按用户隔离。
- [ ] 工具库明确区分外链工具和可调用工具。
- [ ] API Key 加密存储、掩码返回、日志脱敏。
- [ ] 桌面、平板、手机均无明显溢出、遮挡和不可操作区域。
- [ ] README 包含本地启动、Docker 启动、迁移、测试和生产部署说明。
- [ ] 后端关键用例与前端关键流程测试通过。

## 16. 推荐执行顺序

实施时严格先打通“认证 -> 模型配置 -> SSE 对话”这一条纵向闭环，再扩展助手、任务和文稿。这样在第二阶段结束时就已经有一个能真实使用的产品，而不是一组完成度不一致的静态页面。

建议首个可运行版本使用：

- PostgreSQL + Redis 均由 Docker 提供；
- 供应商采用 OpenAI-compatible 配置，默认示例使用 DeepSeek；
- 文件开发环境存本地卷，生产再切 S3；
- 工具市场先使用内置种子数据，后台管理功能后续增加；
- 支付、多人团队、公开分享、联网搜索作为第二期，不阻塞首期交付。
