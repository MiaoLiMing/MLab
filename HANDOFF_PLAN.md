# MLab 后续工作交接与落地操作指南

更新时间：2026-07-21

## 1. 最终目标

交付一套可以直接运行的 Vue 3 + FastAPI AI 工作台。开发环境可通过 Mock Provider 在无模型 Key 时完成全流程验收；配置 OpenAI-compatible API Key 后切换真实模型；最终部署到用户的腾讯云服务器。

完成不能只以“代码已写完”为准，必须同时满足：

1. 前端类型检查、Vitest 和 Vite 生产构建通过。
2. 前后端实际启动，四种视口完成核心业务与视觉验收。
3. 后端测试、迁移、健康检查和 Mock 端到端流程通过。
4. PostgreSQL、Redis、Worker、Web 的生产 Compose 在真实环境启动。
5. HTTPS、SSE 代理、密钥、备份和恢复策略完成配置。
6. 使用真实模型 Key 验证至少一次流式聊天和连接测试。

## 2. 当前已经完成的内容

### 2.1 后端

- 注册、登录、退出、Access/Refresh Token 轮换、Argon2 密码哈希。
- 用户资料、默认助手、主题、记忆总开关和账户数据隔离。
- Provider Credential 加密/掩码、供应商目录、模型配置和连接测试。
- OpenAI-compatible POST SSE、多轮上下文、停止、失败/部分结果持久化、Token 用量。
- 用户消息编辑重发、助手回答重新生成和旧消息分支清理。
- 文件上传/下载/删除、类型/扩展名/大小校验、聊天附件上下文。
- 助手市场、安装、创建、编辑、删除、开场白、模型参数和知识文件。
- 计算器、世界时间、OpenAI function calling、工具调用记录。
- 任务 CRUD/模板/AI 拆解，文稿 CRUD/自动保存/版本/恢复/AI 操作。
- 资源、全局搜索、用量统计、记忆 CRUD/敏感信息过滤/ARQ 提取。
- SQLite 向量回退与 PostgreSQL pgvector `VECTOR(256)` 检索。
- Redis 分布式限流及内存回退、数据库/Redis 就绪检查。
- 开发 Mock Provider；生产环境检测到 Mock 会拒绝启动。
- 5 个 Alembic 迁移版本，Compose 与 GitHub Actions。

### 2.2 前端

- Vue 3、TypeScript、Vite、Pinia、Router、Tiptap、Lucide、Markdown。
- 登录/注册、响应式 AppShell/侧栏、AI 首页、会话和真实 SSE 解析。
- 停止、失败、重试、编辑重发、附件、工具状态、代码高亮。
- 助手市场与编辑器、任务、文稿、资源、记忆、工具库、搜索和设置。
- 默认模型参数、API Key、主题、用量统计、加载/空/错误状态。
- 桌面、平板和移动端 CSS；未使用 Tailwind 或渐变。
- 已新增 Vitest SSE、Chat Store、MessageBubble 测试。

### 2.3 已取得的验证证据

```text
Ruff format/check                              通过
pytest                                         13 passed
Alembic SQLite upgrade/downgrade/re-upgrade    通过
Alembic check                                  无新增迁移
PostgreSQL 离线 SQL                            vector 扩展、VECTOR(256)、开场白字段均存在
OpenAPI                                        43 paths / 52 schemas
Mock HTTP/SSE 端到端                           注册、助手、分支重生成、工具、任务、文稿通过
/health/live 与 /health/ready                  通过
前端离线语法检查                               33 个脚本，0 错误
Vue 模板结构检查                               20 个模板，0 错误
Compose/CI YAML                                解析通过
```

Mock API 曾启动于 `http://127.0.0.1:8011` 并完成验收，交接前已关闭。接手时按本文命令重新启动，不要依赖旧 PID。

## 3. 当前工作区与进程注意事项

### 3.1 Git 工作区

- 工作区包含大量未提交实现，属于当前项目成果，禁止 `git reset --hard`、`git checkout --` 或批量清理。
- `README.md` 当前同时存在已暂存和未暂存修改（`MM`）；不要用旧暂存区覆盖工作树。
- 用户真实 `.env` 被忽略。禁止读取、打印、覆盖或提交其中的密钥。
- 尚未要求创建 Commit；如后续要提交，先完整验证并使用 Conventional Commit 中文描述。

### 3.2 pnpm 安装当前状态

交接前已主动终止慢速 pnpm 安装，并关闭本轮启动的 Registry 与 Mock API。当前确定状态：

```text
frontend/node_modules    不存在
frontend/pnpm-lock.yaml  不存在
端口 19080/19081/8011    无本项目监听
```

接手后仍建议先执行：

```powershell
Get-Process node,pnpm -ErrorAction SilentlyContinue | Select-Object Id,CPU,StartTime,Path
Test-Path frontend\node_modules
Test-Path frontend\pnpm-lock.yaml
```

如果发现新安装进程，先确认是否由其他 Agent 启动；不要并发启动第二次安装。

### 3.3 临时 npm Registry 网关

本机 DNS 不响应，Node TLS 又被运行环境重置，因此临时创建了：

```text
scripts/npm-connect-proxy.mjs
scripts/npm-connect-proxy.py
scripts/npm-curl-registry.py
```

当前可工作的元数据方案是 `npm-curl-registry.py`：pnpm 请求本地 `http://127.0.0.1:19081`，Python 调用 curl 通过固定 IP 获取 npm 内容。已验证 `/vue` 可返回约 2MB 元数据，但速度很慢，完整安装尚未跑完。它只用于本地安装，不能提交或带入生产。优先尝试恢复正常 DNS/npm 网络；只有正常网络仍不可用时才使用该网关。

安装完成或确定放弃该方案后：

1. 停止监听 `19080/19081` 的本项目临时进程。
2. 使用 `apply_patch` 删除以上三个临时脚本。
3. 确认 `package.json` 与 `pnpm-lock.yaml` 中没有本地 Registry URL。

用户已授权并已结束异常 PID `4108`。不要再次操作其他不属于本项目的进程。

## 4. P0：必须优先完成的本地验收

### 步骤 1：完成前端依赖安装

先检查当前安装结果。若 `node_modules` 和锁文件不存在且没有安装进程，可重启本地 Registry：

```powershell
$registry = Start-Process `
  -FilePath '.\.venv\Scripts\python.exe' `
  -ArgumentList 'scripts/npm-curl-registry.py' `
  -WorkingDirectory (Resolve-Path .) `
  -WindowStyle Hidden `
  -PassThru
```

加载 Codex 随附 Node 路径，然后安装：

```powershell
$nodeBin = 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin'
$pnpmBin = 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback'
$env:PATH = "$nodeBin;$pnpmBin;$env:PATH"
$env:HTTP_PROXY = ''
$env:HTTPS_PROXY = ''

pnpm --dir frontend install `
  --registry=http://127.0.0.1:19081 `
  --config.proxy='' `
  --config.https-proxy='' `
  --fetch-timeout 120000 `
  --fetch-retries 2
```

该网关首次获取大包元数据可能需要 20 秒以上。成功标准：

- `frontend/node_modules` 存在。
- `frontend/pnpm-lock.yaml` 存在。
- 锁文件没有 `127.0.0.1`、固定 Registry IP 或真实密钥。

### 步骤 2：正式前端质量检查

```powershell
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
```

必须修复所有类型、测试和构建错误，不能用关闭 strict、跳过测试或扩大 `any` 来绕过。

重点检查可能首次暴露的问题：

- `highlight.js` 按需语言导入类型。
- `MessageBubble.test.ts` 的组件事件类型。
- `chat.test.ts` 的泛型 Mock 类型。
- `vitest.config.ts` 的 Node 类型和 Windows alias。
- `AssistantEditorView.vue` 的嵌套 `model_config` 类型。
- `SettingsView.vue` 的 Promise 元组、参数输入和模板事件类型。

构建成功后将 CI 的安装命令从 `--no-frozen-lockfile` 改为 `--frozen-lockfile`，再次解析 YAML。

### 步骤 3：重新启动 Mock API

Vite 开发代理当前指向 `localhost:8000`，所以浏览器验收应在 8000 启动 API：

```powershell
$env:APP_ENV = 'development'
$env:MOCK_AI_ENABLED = 'true'
$env:DATABASE_URL = 'sqlite+aiosqlite:///./backend/data/mock-browser.db'

.\.venv\Scripts\python.exe -m uvicorn app.main:app `
  --app-dir backend `
  --host 127.0.0.1 `
  --port 8000
```

检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

### 步骤 4：启动前端

```powershell
pnpm --dir frontend dev
```

打开 `http://127.0.0.1:5173`。前后端服务都应保持运行，完成验收前不要结束进程。

### 步骤 5：浏览器业务验收

使用 Playwright 或浏览器自动化完成以下流程：

1. 注册新用户、退出、重新登录。
2. 首页发送普通问题，确认真实 SSE 增量和历史恢复。
3. 发送 `calculate 6 * 7`，确认工具调用状态与结果。
4. 发送“给我一段 Python 代码”，确认 Markdown 与语法高亮。
5. 停止一条生成中的回复，刷新后状态仍为 `stopped`。
6. 编辑用户消息后重新生成，确认旧分支被清理且只保留两条对应消息。
7. 上传 TXT/Markdown 附件，确认聊天中显示文件名且模型能读取内容。
8. 安装系统助手；创建自定义助手，设置开场白、模型参数和知识文件；编辑后删除。
9. 工具搜索/分类/收藏；执行计算器和世界时间；打开外链工具。
10. 创建/编辑/完成/删除任务，并执行 AI 拆解。
11. 创建文稿，验证自动保存、手工版本、恢复、改写/续写/总结。
12. 创建/编辑/关闭/删除记忆，切换全局记忆开关。
13. 创建、复制、搜索和删除资源；验证全局搜索能跳转。
14. 修改资料、默认助手、主题和模型参数；刷新后设置保持。
15. 验证错误提示、空状态、加载状态和无模型配置提示。

### 步骤 6：四种视口视觉验收

必须分别截图并检查：

```text
1440 x 900
1920 x 1080
768 x 1024
390 x 844
```

检查项：

- 首页第一屏构图、输入框和推荐项与参考图风格一致。
- 桌面侧栏固定，内容区无横向滚动。
- 平板/手机侧栏改为抽屉，遮罩和关闭按钮可用。
- Composer、模型选择、附件、发送/停止按钮不重叠。
- 工具/助手卡片在各断点稳定换列，最长中文和英文不会溢出。
- 设置导航、模型参数、文稿编辑器和弹窗在手机上可操作。
- Markdown 长代码、长 URL、表格和附件名不会撑破消息区。
- 深色主题的文字、边框、代码高亮具有足够对比度。

发现问题后修改 CSS，再重新执行 `lint/test/build` 和对应截图。

## 5. P1：生产部署前必须处理

### 5.1 Compose 密钥与数据库凭据

当前 `compose.yaml` 中 PostgreSQL 用户、数据库名和密码仍为固定的 `mlab`，`DATABASE_URL` 也硬编码。正式部署前必须改为环境变量，例如：

```dotenv
POSTGRES_DB=mlab
POSTGRES_USER=mlab
POSTGRES_PASSWORD=<随机强密码>
DATABASE_URL=postgresql+asyncpg://mlab:<URL编码后的密码>@postgres:5432/mlab
```

不要把真实值写入 Compose、README、Git 或聊天记录。应用密钥必须在服务器生成：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 5.2 必须补做的生产集成验证

- 使用真实 PostgreSQL + pgvector 执行 `alembic upgrade head` 和 `alembic check`。
- 使用真实 Redis 验证就绪检查、分布式限流和 ARQ Worker。
- 启动 Compose 五个服务并检查日志中没有密钥或 Authorization。
- 验证 API/Worker 重启后数据、上传文件和任务仍存在。
- 对 PostgreSQL 和上传卷执行一次备份与恢复演练。

当前本机没有 Docker CLI，因此这些工作必须在安装 Docker 的机器或腾讯云完成。

### 5.3 安全加固复核

以下项目在公开部署前必须复核或完善：

- Provider URL 当前会阻止 literal 私网 IP，但域名解析后的私网地址与 DNS rebinding 防护仍需加强。
- CORS 必须改为真实 HTTPS 域名，不能使用通配符。
- Mock 必须为 `false`；生产配置已内置误开启拒绝启动。
- Refresh Token 当前保存在浏览器 localStorage。公开业务建议迁移为 Secure + HttpOnly + SameSite Cookie。
- 多实例时停止生成注册表仍在进程内；需要 Redis Pub/Sub 或明确保持 API 单实例。
- 上传文件生产环境当前使用本地持久卷。单机可用，但必须备份；多实例应实现 S3/COS 适配。
- 增加登录、凭据测试、文件上传、工具执行的限流回归测试。
- 评估日志采集、Sentry/Prometheus、保留周期和告警。

## 6. 腾讯云部署流程

只有 P0 本地浏览器验收全部通过后，再向用户获取服务器信息。推荐使用 SSH Key，不要求用户在聊天中发送明文密码。

### 6.1 需要用户提供

- 腾讯云公网 IP。
- SSH 用户名（建议独立部署用户或 `ubuntu`）。
- SSH 私钥在本机的路径，或用户已配置好的 SSH Host Alias。
- 准备使用的域名及 DNS 管理方式。
- 操作系统版本、CPU/内存/磁盘规格。
- 是否允许安装 Docker、开放 80/443、调整安全组。

### 6.2 服务器准备

1. 更新系统安全补丁。
2. 创建非 root 部署用户并配置 SSH Key。
3. 安装 Docker Engine 与 Compose v2。
4. 腾讯云安全组仅开放 22、80、443；数据库和 Redis 不开放公网。
5. 配置防火墙、时区、NTP 和磁盘空间告警。
6. 准备 `/opt/mlab`、备份目录和持久卷。

### 6.3 部署应用

1. 通过私有 Git 或安全传输上传已验证代码。
2. 在服务器生成 `.env` 密钥和数据库强密码。
3. 设置 `APP_ENV=production`、`MOCK_AI_ENABLED=false`、精确 CORS 域名。
4. 执行 `docker compose build`。
5. 执行 API 镜像内的 `alembic upgrade head`。
6. 执行 `docker compose up -d`。
7. 检查 `postgres`、`redis`、`api`、`worker`、`web` 全部健康。
8. 注册测试账户并配置真实模型 Key。

### 6.4 HTTPS 与 SSE

推荐在 Compose 前增加 Caddy 或宿主机 Nginx：

- 80 自动跳转 443。
- API 和静态前端使用同域，减少 CORS 风险。
- SSE 路由关闭代理缓冲与响应缓存。
- 增大 AI 请求读取超时，但保留连接超时。
- 配置 HSTS、基础安全响应头和证书自动续期。

### 6.5 上线验收

- HTTPS、注册、登录、刷新和退出。
- 真实 API Key 连接测试和至少一次多轮 SSE 对话。
- 工具调用、附件、助手知识文件、任务、文稿、记忆。
- Worker 任务、Redis、pgvector 检索。
- 手机公网访问和四种视口抽查。
- 容器重启、服务器重启、数据库与上传卷持久化。
- 备份任务、日志轮转、磁盘和健康告警。

## 7. 最终收尾

全部通过后：

1. 删除临时 npm Registry 脚本并停止相关进程。
2. 更新 `task.md`，仅在真实通过后勾选前端构建、视觉验收和部署项。
3. 更新 `walkthrough.md`，写入实际命令、测试数量、构建结果、截图和生产 URL。
4. 更新 README 的最终启动与部署命令。
5. 运行 `git diff --check`，确认无冲突标记、密钥、临时数据库、日志或截图垃圾。
6. 审查暂存区与工作树，确认没有覆盖用户修改。
7. 用户要求后再创建 Conventional Commit，例如：

   ```text
   feat(platform): 完成 AI 工作台全栈实现与部署配置
   ```

只有上述证据齐全时，才可以声明“全部落地完成”。
