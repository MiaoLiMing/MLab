# MLab 设计与交互验收

日期：2026-07-23

## 参考真源

- 账号菜单参考：`C:\Users\Liming\AppData\Local\Temp\codex-clipboard-01bdacc7-bde8-45cf-9696-bcb2c22c6926.png`，356 × 426。
- 侧栏参考：`C:\Users\Liming\AppData\Local\Temp\codex-clipboard-a78d5f9a-d49f-4b38-b9ce-0df12f9e3b06.png`，554 × 906。
- 实现遵循现有 MLab Vanilla CSS Design Tokens，并沿用项目已安装的 Lucide 图标库；本轮不需要新增图片资产。

## 验收环境

- 桌面视口：1440 × 900，账户已登录，账号菜单打开。
- 移动视口：390 × 844，模型配置页，侧栏关闭。
- 前端：`http://127.0.0.1:5173/`。
- 后端：`http://127.0.0.1:8011/`。

## 视觉证据

- 账号菜单对照：`docs/qa/account-menu-comparison.png`
- 侧栏与账号入口对照：`docs/qa/sidebar-reference-comparison.png`
- 桌面账号菜单：`docs/qa/account-menu-desktop-final-v2.png`
- 桌面多模型设置：`docs/qa/multi-model-settings-desktop-final-v2.png`
- 移动多模型设置：`docs/qa/multi-model-settings-mobile-final-v2.png`
- 移动侧栏：`docs/qa/sidebar-mobile-open.png`

参考图和实现图已合成到同一张比较图中检查。实现保留参考产品的左侧导航层级、轻边框、灰白底和克制阴影，同时按本次需求将个人资料入口前置、去除底部重复设置，并补齐真实业务状态。

## 交互证据

- 账号面板可打开，包含基本信息、应用设置、订阅与用量和退出登录；点击应用设置可进入模型页。
- 新建会话后可在侧栏重命名为“产品规划讨论”，侧栏与会话页标题同步。
- 对话菜单包含重命名、归档和删除，删除使用确认对话框。
- 安装“全栈工程师”后侧栏即时出现；点击助手创建绑定对话；移除后侧栏即时消失。
- 同一 DeepSeek 凭据下展示 Chat、Coder、Reasoner 三个模型；首页模型选择器可在三者间切换。
- API 请求并发刷新 Token 使用单例刷新 Promise，已增加并发回归测试，避免模型列表偶发为空。

## 迭代记录

### 第一轮发现

- P2：移动设置分类出现横向滚动条，影响完整度。
- P2：助手安装/移除后侧栏不会即时刷新。
- P2：模型 ID 与别名联动存在自动化输入竞争。
- P2：多个并发 API 请求在 Token 过期时可能重复刷新，导致部分请求 401、账户状态或模型列表偶发丢失。
- P3：桌面窄区域的关闭按钮位置和侧栏细节需要统一。

### 修正与复验

- 隐藏移动设置导航滚动条并保持横向可滚动。
- 使用 `mlab:assistants-changed` 事件同步侧栏。
- 通过受控 watch 同步模型别名。
- 为 Token 刷新增加并发锁，并让设置页部分请求失败时保留已成功加载的数据。
- 重新完成桌面和移动视口截图、DOM 快照和控制台检查。

## 最终结论

- P0：0
- P1：0
- P2：0
- P3：0
- 最终浏览器控制台 error/warn：0

final result: passed
