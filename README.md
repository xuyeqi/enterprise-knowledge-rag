# Enterprise Knowledge Base RAG

企业知识库 RAG 问答系统，用于学习 LangChain 并沉淀可写入简历的 AI 应用开发项目。

## 项目目标

本项目从 0 开始实现一个企业知识库问答应用：

- 上传企业文档。
- 将文档切片并写入向量库。
- 用户提问时检索相关文档片段。
- 大模型基于检索上下文回答。
- 返回引用来源，减少幻觉。
- 逐步加入流式输出、文档管理和评估能力。

## 技术栈

- Frontend：Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus
- Backend：Python + uv + FastAPI + LangChain
- Database：PostgreSQL + pgvector
- LLM：OpenAI-compatible API

## 当前状态

项目处于阶段 5：简历亮点增强，并行补齐必要工程能力。

当前已完成：

- FastAPI、PostgreSQL + pgvector 和 Alembic 基础链路。
- txt／md 上传、中文切片、百炼向量生成和文档入库。
- `POST /search` 向量检索与引用来源。
- `POST /answer` LangChain 知识库问答与引用来源，已通过离线测试和真实调用验证。
- Vue3 + TypeScript + Vite 前端骨架、健康状态页和文档上传页，均已通过真实链路验证。
- 文档列表接口和前端页面已通过测试、构建和真实数据验证。
- 聊天问答与引用来源前端页面已通过生产构建和真实问题验证。
- 最近五轮页面级对话历史已经接入，并通过后端测试、前端构建和连续追问验证。
- 相似度阈值和无相关资料拒答已经接入，并通过后端测试与真实问题验证。
- 文本型 PDF 解析、逐页切片、页码存储和引用页码展示已经接入，并通过真实链路验证。
- SSE 流式回答和前端逐块渲染已经接入，并通过后端测试、前端构建和真实链路验证。

下一步：

- 增加简单 RAG 评估样例，为相似度阈值和回答质量提供可重复的验证依据。

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

## 前端启动

前端要求 Node.js `20.19+` 或 `22.12+`。进入前端目录并安装依赖：

```powershell
cd frontend
npm install
```

执行 TypeScript 检查和生产构建：

```powershell
npm run build
```

先启动 FastAPI，再启动前端开发服务器：

```powershell
npm run dev
```

打开 `http://127.0.0.1:5173`。页面显示“FastAPI 服务连接正常”时，说明浏览器、
Vite `/api` 代理和后端健康接口已经连通。

## 数据库迁移

项目使用 Alembic 管理数据库 schema 版本。迁移命令在 `backend` 目录执行：

```powershell
cd backend
uv sync --extra dev
uv run alembic upgrade head
```

第一次迁移会启用 pgvector，并创建 `documents`、`document_chunks` 两张表；
最新迁移会为文档切片增加可空的 PDF 页码字段。
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
CHAT_MODEL=qwen3.7-plus
```

真实接口检查命令需要在 `backend` 目录执行：

```powershell
uv run python -m scripts.check_embedding
```

该命令会产生真实 API 请求并可能消耗百炼额度；pytest 使用模拟响应，不会
访问百炼或产生费用。

知识库问答使用 LangChain `ChatOpenAI` 通过同一个百炼兼容地址调用
`qwen3.7-plus`。当前关闭思考模式，优先验证低延迟的最小 RAG 闭环；模型只接收
向量检索返回的文字切片和最近五轮页面级对话，并在响应中保留引用来源。历史对话
只帮助理解指代和追问，事实依据仍以本次检索切片为准。

## 文本切片

后端使用 LangChain `RecursiveCharacterTextSplitter` 处理 TXT／Markdown 和从
PDF 每页提取出的文本，
默认每片最多 800 个字符，相邻切片目标重叠 120 个字符。分隔符优先级包含
段落、换行和常见中英文标点，以减少句子在不必要的位置被截断。

当前切片服务是纯内存函数，不读取文件、不访问数据库，也不调用 embedding。

## 文档上传预览

启动后端并打开 Swagger：

```text
http://127.0.0.1:8000/docs
```

使用 `POST /documents/preview` 可以上传不超过 2 MB 的 UTF-8 `.txt`、`.md`
或文本型 `.pdf` 文件，查看切片数量、PDF 页码和完整切片内容。当前不支持
加密 PDF、扫描件或 OCR。这个预览接口不会保存文件、写数据库或调用百炼。

## 学习重点

这个项目重点不是训练大模型，而是掌握企业级 AI 应用落地常见能力：

- RAG 基础链路。
- 文档处理。
- 向量检索。
- 模型 API 调用。
- 前后端分离。
- 数据库设计。
- 可验证的工程闭环。
