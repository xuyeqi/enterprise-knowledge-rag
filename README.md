# Enterprise Knowledge Base RAG

企业知识库 RAG 问答系统，用于学习 LangChain 并沉淀可写入简历的 AI 应用开发项目。

## 项目目标

本项目从 0 开始实现一个企业知识库问答应用：

- 上传企业文档。
- 将文档切片并写入向量库。
- 用户提问时检索相关文档片段。
- 大模型基于检索上下文回答。
- 返回引用来源，减少幻觉。
- 后续加入流式输出、对话历史、文档管理和评估能力。

## 技术栈

- Frontend：Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus
- Backend：Python + uv + FastAPI + LangChain
- Database：PostgreSQL + pgvector
- LLM：OpenAI-compatible API

## 当前状态

项目处于阶段 1：项目初始化。

当前已完成：

- 确定项目方向。
- 确定技术栈。
- 建立项目规范、路线图和说明文档。
- 创建 FastAPI 后端最小骨架和 `/health` 接口。

下一步：

- 使用 uv 同步后端依赖，并运行后端验证。
- 添加 PostgreSQL + pgvector 本地开发环境。

## 本地数据库

本地数据库使用 Docker Compose 启动 PostgreSQL + pgvector。

首次启动前，在项目根目录复制环境变量示例文件：

```powershell
Copy-Item .env.example .env
```

然后打开 `.env`，把 `RAG_POSTGRES_PASSWORD` 的占位符替换为本地数据库的真实密码。
`.env` 已被 `.gitignore` 排除，不要把真实密码写进 `.env.example`。

启动数据库：

```powershell
docker compose up -d postgres
```

停止数据库：

```powershell
docker compose stop postgres
```

## 后端启动

如果本机还没有安装 `uv`，先在 PowerShell 执行：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

检查 `uv` 是否可用：

```bash
uv --version
```

进入后端目录：

```bash
cd backend
```

同步依赖，包含测试用的 `dev` 依赖：

```bash
uv sync --extra dev
```

运行测试：

```bash
uv run pytest
```

启动接口服务：

```bash
uv run uvicorn app.main:app --reload
```

注意：本项目后端统一使用 `uv run` 执行项目环境里的命令，不直接运行 `uvicorn ...`，也不使用 `pip install -e ".[dev]"` 作为默认安装方式。

后端会自动读取项目根目录 `.env` 中的数据库配置，不需要在每个 PowerShell 窗口重复设置密码。

数据库连通性检查接口：

```text
http://127.0.0.1:8000/health/db
```

## 数据库迁移

项目使用 Alembic 管理数据库 schema 版本。迁移命令在 `backend` 目录执行：

```powershell
cd backend
uv sync --extra dev
uv run alembic upgrade head
```

第一次迁移会启用 pgvector，并创建 `documents`、`document_chunks` 两张表。
`document_chunks.embedding` 固定为 `vector(1024)`，与百炼
`text-embedding-v4` 的 1024 维调用配置保持一致。

迁移会真实修改数据库结构。不要在未确认影响时执行 `alembic downgrade`。

## 百炼文本向量

后端使用阿里云百炼 OpenAI 兼容接口调用 `text-embedding-v4`，输出维度固定
为 1024，与 PostgreSQL 的 `vector(1024)` 字段一致。

在本地 `.env` 中配置新建且未泄露的 Key：

```env
DASHSCOPE_API_KEY=<your-new-api-key>
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=1024
```

真实接口检查命令需要在 `backend` 目录执行：

```powershell
uv run python -m scripts.check_embedding
```

该命令会产生真实 API 请求并可能消耗百炼额度；pytest 使用模拟响应，不会
访问百炼或产生费用。

## 学习重点

这个项目重点不是训练大模型，而是掌握企业级 AI 应用落地常见能力：

- RAG 基础链路。
- 文档处理。
- 向量检索。
- 模型 API 调用。
- 前后端分离。
- 数据库设计。
- 可验证的工程闭环。
