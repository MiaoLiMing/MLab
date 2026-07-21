# MLab 项目规则

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、Vanilla CSS。
- 后端：Python 3.12、FastAPI、SQLAlchemy 2 Async、Alembic、Pydantic v2。
- 数据：生产使用 PostgreSQL；本地测试允许 SQLite；缓存与任务使用 Redis/ARQ。
- 包管理：前端使用 pnpm，后端使用 `pyproject.toml` 与 pip。

## 目录与职责

- `frontend/`：浏览器应用，页面只负责编排，API、状态和复用逻辑分别放入对应目录。
- `backend/app/api/`：HTTP 层；`services/`：业务层；`repositories/`：数据访问层。
- `backend/app/ai/`：模型供应商与 SSE 事件归一化，不允许业务代码直接绑定厂商 SDK。
- `docs/`：架构、部署和接口补充文档。

## 常用命令

```powershell
pnpm --dir frontend install
pnpm --dir frontend dev
pnpm --dir frontend build
pnpm --dir frontend test

python -m pip install -e ".\backend[dev]"
python -m uvicorn app.main:app --app-dir backend --reload
python -m pytest backend/tests
python -m ruff check backend

docker compose up --build
```

## 实施要求

- API 路径统一使用 `/api/v1`，错误响应包含稳定的错误码和 `request_id`。
- 所有用户数据必须在服务或查询层按 `user_id` 隔离。
- API Key 只允许掩码返回，日志不得输出密钥或 Authorization。
- 聊天使用服务端真实 SSE，不使用前端定时器模拟流式效果。
- 前端样式使用 Vanilla CSS 与 Design Tokens，不引入 Tailwind。
- 新增接口、数据模型和组件 Props 必须有明确类型。
- 每次阶段性交付同步更新 `task.md`；最终更新 `walkthrough.md`。

