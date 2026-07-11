# Backend

FastAPI backend for the enterprise knowledge base RAG project.

## File Purpose

这个目录是后端服务目录。当前阶段只做一个最小 FastAPI 应用，目的是先确认「后端能启动、接口能访问、测试能验证」。

当前文件作用：

- `app/main.py`：FastAPI 应用入口，定义普通健康检查和数据库健康检查接口。
- `app/core/config.py`：从 `RAG_POSTGRES_*` 环境变量读取数据库连接配置。
- `app/db/session.py`：创建 SQLAlchemy 异步引擎，并执行最小数据库查询。
- `app/db/base.py`：定义所有 SQLAlchemy 数据模型共同继承的基础类。
- `app/models/document.py`：定义原始文档和 1024 维文档切片模型。
- `app/services/embedding.py`：调用百炼，把 1～10 条文本转换为 1024 维向量。
- `scripts/check_embedding.py`：由开发者手动执行一次真实 embedding 调用。
- `migrations/`：保存 Alembic 数据库结构版本和第一次建表迁移。
- `alembic.ini`：指定 Alembic 的迁移脚本位置和基础行为。
- `app/__init__.py`：把 `app` 目录标记为 Python 包，方便用 `from app.main import app` 导入。
- `tests/test_health.py`：使用 FastAPI 测试客户端请求 `/health`，确认接口返回正确。
- `pyproject.toml`：声明 Python 版本、依赖包和测试配置。
- `uv.lock`：uv 根据 `pyproject.toml` 解析出来的锁文件，用来固定依赖版本，保证不同机器安装结果尽量一致。

## Current Scope

This stage only provides the minimal backend skeleton:

- FastAPI application entry.
- `GET /health` endpoint.
- Basic test for the health endpoint.

当前已经定义文档和文档切片表，并提供 Alembic 迁移。LangChain、文档上传
和完整 RAG 业务逻辑将继续逐步添加。当前 embedding 服务直接使用百炼的
OpenAI 兼容接口，LangChain 会在后续检索问答链路中接入。

## Run Locally

Install uv first:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Check uv:

```bash
uv --version
```

Then sync dependencies:

```bash
uv sync --extra dev
```

这条命令的意思：

- `uv --version`：检查当前终端是否能找到 uv 命令。
- `uv sync`：根据 `pyproject.toml` 和 `uv.lock` 创建或更新项目虚拟环境。
- `--extra dev`：额外安装 `[project.optional-dependencies]` 里的 `dev` 分组，例如 `pytest` 和 `httpx`。
- uv 会把依赖安装到项目环境中，所以后面运行命令要使用 `uv run`。

Start the API server from the `backend` directory:

```bash
uv run uvicorn app.main:app --reload
```

这条命令的意思：

- `uv run`：在 uv 管理的项目虚拟环境里执行命令。
- `uvicorn`：启动 ASGI Web 服务。
- `app.main:app`：前面的 `app.main` 是 Python 模块路径，后面的 `app` 是 `main.py` 里的 FastAPI 实例变量。
- `--reload`：开发模式下监听文件变化，代码变更后自动重启服务。

Open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

首次启动前，在项目根目录复制环境变量示例文件：

```powershell
Copy-Item .env.example .env
```

然后把 `.env` 中的密码占位符替换为本地数据库的真实密码。后端的
`app/core/config.py` 会自动读取这个文件，不需要每次打开 PowerShell 都重新设置。

数据库连接默认使用以下参数，也可以通过操作系统中的同名环境变量覆盖：

```text
RAG_POSTGRES_HOST=127.0.0.1
RAG_POSTGRES_PORT=5432
RAG_POSTGRES_USER=rag_user
RAG_POSTGRES_DB=rag_db
```

数据库健康检查地址：

```text
http://127.0.0.1:8000/health/db
```

连接成功时返回：

```json
{"status":"ok","database":"connected"}
```

## Test

```bash
uv run pytest
```

`uv run pytest` 会在 uv 管理的项目环境里执行 pytest。pytest 会自动查找 `tests/` 目录里以 `test_` 开头的测试文件，并执行里面以 `test_` 开头的测试函数。

embedding 单元测试使用本地假响应，不会调用百炼，也不会产生 API 费用。

## Database Migration

以下命令会真实修改 `rag_db` 的 schema。执行前保持 Docker Desktop 和
PostgreSQL 容器运行，并确认项目根目录 `.env` 指向本地开发数据库。

先同步新增的 Alembic 和 pgvector 依赖：

```powershell
uv sync --extra dev
```

查看当前数据库迁移版本，不修改 schema：

```powershell
uv run alembic current
```

应用全部尚未执行的迁移：

```powershell
uv run alembic upgrade head
```

第一次迁移会执行：

- 启用 PostgreSQL 的 `vector` 扩展。
- 创建 `documents` 表。
- 创建 `document_chunks` 表，其中 `embedding` 为 `vector(1024)`。
- 创建外键、切片顺序唯一约束和 `document_id` 索引。

不要把下面的回滚命令当作测试命令执行：

```powershell
uv run alembic downgrade -1
```

它会删除两张表及其中的数据，并移除 `vector` 扩展。按照项目规范，执行
任何 downgrade 前必须先确认影响和备份数据。

迁移成功后，在 VS Code 的 `rag_db` 查询窗口执行以下只读 SQL：

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('documents', 'document_chunks')
ORDER BY table_name;

SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'document_chunks'
ORDER BY ordinal_position;
```

## Bailian Embedding

项目使用阿里云百炼 `text-embedding-v4`，固定输出 1024 维 dense embedding，
与数据库的 `vector(1024)` 字段保持一致。

在项目根目录 `.env` 中填写新建且未泄露的 Key：

```env
DASHSCOPE_API_KEY=<your-new-api-key>
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=1024
```

不要把真实 Key 写入 `.env.example`、Python 文件、日志或 Git。

同步新增的 OpenAI SDK 并运行离线测试：

```powershell
uv sync --extra dev
uv run pytest
```

确认测试通过后，再手动执行一次真实 API 检查：

```powershell
uv run python -m scripts.check_embedding
```

这个命令会产生一次百炼请求并可能消耗额度。成功时会输出类似：

```text
model: text-embedding-v4
dimension: 1024
first_5_values: [...]
```

脚本不会输出 API Key，也不会输出完整的 1024 个向量值。
