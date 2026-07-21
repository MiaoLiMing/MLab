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
