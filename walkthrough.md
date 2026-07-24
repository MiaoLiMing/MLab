# MLab 实施结果

更新时间：2026-07-21

## 已完成

- 建立 Vue 3 + TypeScript + Vite 前端和 FastAPI + SQLAlchemy Async 后端单仓。
- 建立 Docker Compose：PostgreSQL/pgvector、Redis、API、ARQ Worker、Nginx 前端镜像。
- 建立用户注册、登录、Refresh Token 轮换、资料更新和数据隔离。
- 建立供应商凭据加密、掩码返回、模型配置和兼容端点连接测试。
- 建立真实 OpenAI-compatible POST SSE 对话：消息与附件持久化、流式增量、停止、失败状态、Token 用量、内置工具函数调用及调用审计。
- 建立助手市场/创建/编辑/删除、开场白、模型参数和知识文件，工具分类/搜索/收藏/外链，任务模板、AI 拆解，文稿自动保存/版本/AI 操作，资源和文件上传。
- 建立 ARQ 记忆提取、敏感信息过滤、全局开关，以及 SQLite 余弦回退和 PostgreSQL pgvector 检索。
- 建立首页、对话、助手、工具、任务、文稿、资源、记忆、设置、登录和注册页面；样式使用 Vanilla CSS Design Tokens，覆盖移动端布局。
- 建立 API 文档、环境变量示例、Alembic、Ruff、Pytest、前端 SSE 单元测试和 README。
- 建立 5 个 Alembic 迁移版本；SQLite 完成升级、降级、再升级，PostgreSQL 离线 SQL 已验证创建 vector 扩展、`VECTOR(256)` 与助手开场白字段。
- 建立 GitHub Actions，覆盖 PostgreSQL/Redis 下的迁移、后端测试及前端类型检查、测试和构建。
- 增加开发环境 Mock Provider：无需模型 Key 即可验证真实 REST、SSE、工具调用、任务拆解和文稿 AI 链路；生产环境强制禁用。

## 已验证

执行命令：

```text
python -m ruff format app tests alembic/versions  通过
python -m ruff check app tests alembic/versions   通过
python -m pytest -q                              13 passed
alembic check（SQLite）                          无新增迁移
OpenAPI                                          43 paths / 52 schemas
Mock Provider 端到端验收                         通过（注册、助手编辑、分支重生成、SSE 工具调用、任务、文稿）
Uvicorn /health/live 与 /health/ready            通过
前端 TypeScript/Vue/配置脚本离线语法编译          33 个脚本，0 错误
前端 Vue 模板结构检查                            20 个模板，0 错误
前端 SSE 解析器离线运行                          2 个事件，结果通过
Compose 与 GitHub Actions YAML                    解析通过
```

后端测试覆盖：注册/登录/刷新、认证拦截和数据隔离、附件与知识文件、编辑重发、SSE、函数调用、Mock Provider、工具安全、任务 AI 拆解、文稿版本、资源与向量记忆。

## 当前环境限制

- 当前机器未安装 Docker CLI，因此无法在本机启动 Compose 容器；Compose 文件和镜像构建配置已经写入。
- 当前机器访问 npm Registry 时返回 `ENOTFOUND`，且 pnpm 离线缓存为空。前端依赖安装尚未完成，因此尚未执行正式 `vue-tsc`、Vite build、Vitest 和浏览器截图验证，也尚未生成 `pnpm-lock.yaml`。
- 后端依赖通过清华 PyPI 镜像安装成功，测试使用 SQLite；生产 Compose 使用 PostgreSQL/Redis。

## 启动交付

在可访问 npm/PyPI 且安装 Docker 的环境运行：

```powershell
docker compose up --build
```

然后访问 `http://localhost:8080`，注册账户并在设置页配置模型 API Key。无 Docker 时分别启动后端 Uvicorn 和前端 Vite，命令见 `README.md`。

---

## 2026-07-23 专业化体验完善

### 本轮交付

- 左上角账号区域已成为完整入口：可查看账户、用量和订阅信息，并进入个人资料、模型设置或退出登录；侧栏底部重复入口已移除。
- 最近对话支持新建、重命名、归档和删除；侧栏与对话页标题保持同步，删除使用二次确认。
- 点击侧栏助手会创建绑定该助手的新对话；公共助手可移除，自建助手可编辑或删除，列表会即时刷新。
- API 凭据与模型配置已分离，一份凭据可添加多个模型；支持模型别名、参数、默认模型和删除管理。
- 修复并发请求同时刷新 Token 时的竞争问题，避免账户恢复或模型列表偶发为空。
- 清理无响应的装饰按钮，附件、菜单、确认、设置和主要导航均具备真实行为或明确反馈。
- 全局视觉调整为灰白主色，黑色仅用于主操作和选中强调；桌面与移动布局均完成回归。

### 自动化验证

```text
pnpm --dir frontend lint                         通过
pnpm --dir frontend test                         4 个测试文件、7 个测试通过
pnpm --dir frontend build                        通过
python -m pytest backend/tests                   12 通过、1 个既有 SSE 持久化用例失败
python -m ruff check backend                     1 个既有 alembic/env.py 导入排序问题
```

后端两个未通过项均位于本轮未修改的后端代码：SSE 流响应完成后助手消息内容未持久化，以及 Alembic 环境文件的导入顺序。它们不影响本轮前端功能验收，但已如实保留为后续修复项。

### 浏览器验收

- 桌面视口：1440 × 900。
- 移动视口：390 × 844。
- 已验证账号面板、会话重命名、助手安装/移除、从助手新建对话、三个模型同时展示和设置页跳转。
- 最终浏览器控制台无 error/warn；视觉对照和截图见 `design-qa.md`。
- 本地预览：`http://127.0.0.1:5173/`，本地验收 API：`http://127.0.0.1:8011/`。
