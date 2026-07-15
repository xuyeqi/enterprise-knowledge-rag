# 企业知识库 RAG 项目规范

## 项目定位

本项目是一个面向求职作品集的企业知识库 RAG 问答系统，目标是展示大模型应用开发中的真实工程能力：

- 文档上传、解析、切片与索引。
- 基于 LangChain 的 RAG 问答链路。
- 使用 PostgreSQL + pgvector 管理业务数据和向量数据。
- 使用 Vue3 + TypeScript 构建企业后台式前端体验。
- 后续逐步加入引用溯源、流式输出、对话历史、权限控制和评估能力。

项目优先服务于 20k 以下 AI 应用开发、前端 + AI 应用开发、大模型应用开发岗位求职，不追求一开始做复杂平台。

## 技术栈

### Frontend

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Element Plus

### Backend

- Python
- uv
- FastAPI
- LangChain
- SQLAlchemy
- Pydantic

### Database

- PostgreSQL
- pgvector

### LLM

- OpenAI-compatible API
- 初期支持一个模型供应商即可，后续再扩展 DeepSeek、Qwen、OpenAI 等兼容模型。

## 目录约定

计划目录结构：

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── pyproject.toml
│   ├── uv.lock
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── styles/
│   │   ├── views/
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   └── README.md
├── docker-compose.yml
├── README.md
├── ROADMAP.md
└── CLAUDE.md
```

### 前端结构与运行约定

- 前端目录固定为 `frontend/`，使用 npm 管理依赖并提交 `package-lock.json`。
- `src/api/` 只放 HTTP 请求和响应类型；页面不直接散落 `fetch` 调用。
- `src/assets/` 存放需要参与 Vite 构建的本地图片等静态品牌资源；业务组件通过模块导入使用。
- `src/views/` 放路由页面，`src/components/` 放可复用界面组件，`src/router/` 放路由配置，`src/stores/` 放 Pinia 状态。
- 开发环境统一请求 `/api/*`，由 Vite 代理到 `http://127.0.0.1:8000`，前端代码不硬编码后端完整地址。
- 当前使用浏览器原生 `fetch`，在出现统一拦截、取消请求等明确需求前不引入 Axios。
- 本地开发使用 `npm run dev`，类型检查与生产构建统一使用 `npm run build`。
- 新增前端依赖前先确认 Vue、浏览器标准能力或现有依赖不能解决，避免同类库重复引入。

## 开发原则

- 每个阶段只做能验证的最小闭环。
- 先跑通主链路，再补复杂能力。
- 不引入当前阶段用不到的抽象、依赖和配置项。
- 后端统一使用 uv 管理 Python 依赖和运行命令，不使用 pip 作为项目默认安装方式。
- 所有代码改动必须对应 ROADMAP.md 中的阶段目标。
- 完成开发、修复、文档补齐或重要调研后，同步更新 ROADMAP.md。
- 涉及数据库 schema、环境变量、密钥、CI/CD、发布部署前必须先确认。

## 新手向代码注释规范

- Codex 生成或修改的代码必须提供清晰、详细的中文注释，默认读者是刚学习 Python 和 AI 应用开发的新手。
- 每个新建代码文件需要在文件开头说明文件用途、所属模块，以及它在项目调用链中的职责。
- 导入第三方库、项目内模块或不容易理解的标准库时，需要说明导入对象来自哪里、在当前文件中解决什么问题。
- 自定义类、函数、重要变量和配置项需要说明：它是什么、由谁创建、在哪里使用，以及命名所表达的含义。
- 函数注释需要说明参数、返回值、主要执行步骤；存在异常、异步调用、上下文管理器或资源释放时，需要解释其作用。
- 对装饰器、类型标注、`async/await`、依赖注入、生成器、上下文管理器等新手不熟悉的语法，需要在首次出现或关键位置解释。
- 数据库、LangChain、RAG、向量检索和模型调用代码，需要说明数据从哪里来、经过哪些处理、最终流向哪里。
- 注释要解释代码的目的和运行机制，不能只把代码逐字翻译成中文，也不能用大量无信息量注释干扰阅读。
- 修改既有代码时，只为本次涉及的代码补充必要注释，不借机重写或格式化无关代码。

## 学习型协作分工

- Codex 负责分析方案、编写代码和文档、解释关键代码，并给出需要执行的命令、执行目录、操作目的和预期结果。
- 用户负责亲自执行 `uv sync`、`uv run pytest`、`npm install`、`npm run build`、启动服务、数据库操作等学习和验证命令，并将完整结果或报错反馈给 Codex。
- Codex 默认不代替用户执行上述学习和验证命令；如果某项操作必须由 Codex 执行，需要先说明原因并获得用户确认。
- 在用户反馈真实执行结果前，Codex 不得声称代码已经验证或完成，也不得将 `ROADMAP.md` 中的对应事项标记为“已完成”。
- 用户反馈结果后，Codex 负责判断是否达到预期；如果失败，需要解释根因、修改代码或给出下一条最小排查命令。

## 第一阶段范围

阶段 1 只做项目初始化：

- 建立项目规范文档。
- 搭建 FastAPI 后端最小骨架。
- 使用 docker-compose 启动 PostgreSQL + pgvector。
- 提供 /health 接口。
- 提供数据库连通性检查。

阶段 1 不做：

- 文档上传。
- LangChain RAG。
- 前端页面。
- 登录权限。
- Agent 或 LangGraph。

## 验证要求

每次实现代码后必须尽量运行验证：

- 后端至少运行启动检查或接口测试。
- 数据库相关改动至少验证连接或迁移结果。
- 前端改动至少运行类型检查或构建。
- 无法验证时，需要在汇报中说明原因。
