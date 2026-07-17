# Backend

FastAPI backend for the enterprise knowledge base RAG project.

## File Purpose

这个目录是后端服务目录。当前阶段实现可验证的最小 RAG 闭环，包括文档入库、
向量检索、模型回答和引用来源。

当前文件作用：

- `app/main.py`：FastAPI 应用入口，定义普通健康检查和数据库健康检查接口。
- `app/api/documents.py`：提供文档列表、TXT／Markdown／PDF 切片预览和正式向量入库接口。
- `app/api/search.py`：接收自然语言问题，返回 pgvector 检索到的相关切片。
- `app/api/answer.py`：组合向量检索和对话模型，返回知识库答案与引用来源。
- `app/schemas/document.py`：定义上传预览和正式入库接口的 JSON 响应结构。
- `app/schemas/search.py`：定义知识库向量检索接口的请求和响应结构。
- `app/schemas/answer.py`：定义知识库问答接口的请求和响应结构。
- `app/core/config.py`：从 `RAG_POSTGRES_*` 环境变量读取数据库连接配置。
- `app/core/error_handlers.py`：统一模型、数据库和未知服务异常的 HTTP 状态码与安全提示。
- `app/db/session.py`：创建 SQLAlchemy 异步引擎和请求级会话，并执行最小数据库查询。
- `app/db/base.py`：定义所有 SQLAlchemy 数据模型共同继承的基础类。
- `app/models/document.py`：定义原始文档和 1024 维文档切片模型。
- `app/services/embedding.py`：调用百炼，把 1～10 条文本转换为 1024 维向量。
- `app/services/document_indexing.py`：编排切片、分批向量生成和数据库事务写入。
- `app/services/document_parser.py`：解析 UTF-8 文本和文本型 PDF，并保留 PDF 页码。
- `app/services/retrieval.py`：生成问题向量并执行 pgvector 余弦距离检索。
- `app/services/answering.py`：使用 LangChain 组织提示词并调用百炼生成答案。
- `app/services/text_splitter.py`：使用 LangChain 按段落和中英文标点递归切片。
- `scripts/check_embedding.py`：由开发者手动执行一次真实 embedding 调用。
- `scripts/evaluate_rag.py`：读取固定问题集，统计检索、回答和拒答是否符合预期。
- `evaluation/rag_cases.json`：保存可重复执行的 RAG 评估问题与期望关键词。
- `migrations/`：保存 Alembic 数据库结构版本和第一次建表迁移。
- `alembic.ini`：指定 Alembic 的迁移脚本位置和基础行为。
- `app/__init__.py`：把 `app` 目录标记为 Python 包，方便用 `from app.main import app` 导入。
- `tests/test_health.py`：使用 FastAPI 测试客户端请求 `/health`，确认接口返回正确。
- `tests/test_error_handling.py`：模拟模型、数据库和未知异常，确认响应不泄露内部细节。
- `tests/test_critical_failures.py`：验证入库、检索和问答跨层失败时的状态码与事务边界。
- `pyproject.toml`：声明 Python 版本、依赖包和测试配置。
- `uv.lock`：uv 根据 `pyproject.toml` 解析出来的锁文件，用来固定依赖版本，保证不同机器安装结果尽量一致。

## Current Scope

Current backend scope:

- FastAPI health and database connectivity endpoints.
- TXT／Markdown／PDF document preview and vector indexing.
- pgvector semantic search.
- LangChain knowledge answer generation with sources.

当前已经提供文档上传、切片、向量入库、向量检索和 LangChain 知识库问答链路。
embedding 服务直接使用百炼的 OpenAI 兼容接口；问答服务通过
`langchain-openai` 调用同一个兼容接口。

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

文本切片测试只在内存中处理字符串，同样不访问数据库或外部 API。

向量检索测试会模拟问题 embedding 和数据库查询，不会调用百炼或读取 PostgreSQL。

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

全部迁移会执行：

- 启用 PostgreSQL 的 `vector` 扩展。
- 创建 `documents` 表。
- 创建 `document_chunks` 表，其中 `embedding` 为 `vector(1024)`。
- 创建外键、切片顺序唯一约束和 `document_id` 索引。
- 为 `document_chunks` 增加可空的 `page_number` 字段；现有文本切片保持 `NULL`。

不要把下面的回滚命令当作测试命令执行：

```powershell
uv run alembic downgrade -1
```

回滚最新迁移会丢失 PDF 页码；继续回滚第一次迁移会删除两张表及其中的数据。
按照项目规范，执行任何 downgrade 前必须先确认影响和备份数据。

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

## Text Splitting

项目使用 LangChain 的 `RecursiveCharacterTextSplitter`。当前默认参数：

```text
chunk_size=800
chunk_overlap=120
```

长度使用 Python `len` 按字符计算，不是按模型 token 计算。切片器优先保留
完整段落和句子，再依次尝试中英文句号、问号、分号、逗号、空格，最后才按
单字符拆分。

核心调用方式：

```python
from app.services.text_splitter import split_text

chunks = split_text("需要切分的完整文档内容")
```

返回值是按原文顺序排列的 `list[str]`，后续会批量传给 `embed_texts`。

## Document Preview Upload

当前提供不持久化的上传预览接口：

```http
POST /documents/preview
Content-Type: multipart/form-data
```

限制：

- 只接受 `.txt`、`.md` 和 `.pdf`，扩展名不区分大小写。
- 文件最大 `2 MB`。
- TXT／Markdown 必须使用 UTF-8，同时兼容带 BOM 的 UTF-8。
- PDF 必须包含可提取的文本层；当前不支持加密 PDF、扫描件和 OCR。
- 空文件、纯空白文件和没有文本层的 PDF 会被拒绝。

接口只读取、解码和切片，不保存文件、不访问数据库、不调用百炼。

启动后端：

```powershell
uv run uvicorn app.main:app --reload
```

浏览器打开：

```text
http://127.0.0.1:8000/docs
```

展开 `POST /documents/preview`，点击 `Try it out`，选择本地 TXT、Markdown 或
文本型 PDF，再点击 `Execute`。响应会展示文件名、总字符数、切片数量、
PDF 页码和每个完整切片。

## Document Indexing Upload

正式入库接口：

```http
POST /documents
Content-Type: multipart/form-data
```

它与预览接口使用相同的文件限制，但处理链路不同：

1. 校验文件名、大小和内容是否可解析。
2. TXT／Markdown 使用 UTF-8 解码；PDF 使用 pypdf 逐页提取文本。
3. 使用 LangChain 把原文切成多个文本片段，PDF 切片同时记录来源页码。
4. 每批最多 10 个切片调用百炼 `text-embedding-v4`，生成 1024 维向量。
5. 全部向量成功后，通过一次数据库事务写入一条 `documents` 和多条
   `document_chunks`。
6. 数据库提交失败时整体回滚，不保留只有部分切片的不完整数据。

注意：调用这个接口会产生真实百炼 API 请求，并会向本地 `rag_db` 写入数据。
建议先用较短的 txt 或 md 文件验证，避免重复上传造成不必要的模型费用和数据。

成功时返回 HTTP `201 Created`，示例：

```json
{
  "document_id": "12345678-1234-5678-1234-567812345678",
  "filename": "policy.md",
  "status": "indexed",
  "chunk_count": 2
}
```

在 Swagger 中展开 `POST /documents`，选择文件并执行。接口成功后，可以在
VS Code PostgreSQL 查询窗口执行以下只读 SQL 核对刚写入的数据：

```sql
SELECT id, filename, content_type, status, created_at
FROM documents
ORDER BY created_at DESC
LIMIT 5;

SELECT
    d.filename,
    dc.chunk_index,
    dc.page_number,
    LEFT(dc.content, 100) AS content_preview,
    vector_dims(dc.embedding) AS embedding_dimension
FROM document_chunks AS dc
JOIN documents AS d ON d.id = dc.document_id
ORDER BY d.created_at DESC, dc.chunk_index
LIMIT 20;
```

## Document List

文档列表接口：

```http
GET /documents
```

接口按创建时间倒序返回文档 ID、文件名、状态、切片数量和创建时间。查询只聚合
切片数量，不读取切片正文或 embedding。知识库为空时返回空数组 `[]`。

## Knowledge Search

最小向量检索接口：

```http
POST /search
Content-Type: application/json
```

请求示例：

```json
{
  "query": "打车费怎么报销？",
  "limit": 3
}
```

处理流程：

1. 校验问题不是空白文本，并把 `limit` 限制在 1～10。
2. 使用与文档入库相同的百炼 `text-embedding-v4` 生成 1024 维问题向量。
3. 使用 pgvector 余弦距离查询状态为 `indexed` 的文档切片。
4. 按相似度从高到低返回切片内容、文件名和文档 ID。

响应示例：

```json
{
  "query": "打车费怎么报销？",
  "result_count": 1,
  "results": [
    {
      "chunk_id": "11111111-1111-1111-1111-111111111111",
      "document_id": "22222222-2222-2222-2222-222222222222",
      "filename": "expense-policy.md",
      "chunk_index": 2,
      "page_number": null,
      "content": "出差期间产生的出租车费用可以报销。",
      "similarity": 0.91
    }
  ]
}
```

调用 `/search` 会产生一次真实百炼 embedding 请求，但只读取数据库，不会新增、
修改或删除文档。当前使用精确余弦距离检索；数据量增大并经过性能验证后，再考虑
增加 HNSW 或 IVFFlat 索引。

## Knowledge Answer

最小 RAG 问答接口：

```http
POST /answer
Content-Type: application/json
```

请求示例：

```json
{
  "query": "打车费怎么报销？",
  "history": [
    {"role": "user", "content": "公司的交通费用政策是什么？"},
    {"role": "assistant", "content": "公司资料包含交通费用报销规则。"}
  ],
  "limit": 3
}
```

处理流程：

1. 校验 `history` 是最多五轮、按 user／assistant 交替排列的完整对话。
2. 使用最近历史问题补充检索语义，再召回最多 `limit` 个相关切片。
3. 过滤余弦相似度低于 `0.5` 的切片；没有切片达到阈值时直接拒答。
4. 用 LangChain 提示词把历史和通过阈值的切片组织为相互隔离的上下文。
5. 调用百炼 `qwen3.7-plus` 非思考模式生成答案。
6. 返回答案以及真正交给模型的全部引用切片。

响应示例：

```json
{
  "query": "打车费怎么报销？",
  "answer": "出差期间产生的出租车费用可以报销。",
  "source_count": 1,
  "sources": [
    {
      "chunk_id": "11111111-1111-1111-1111-111111111111",
      "document_id": "22222222-2222-2222-2222-222222222222",
      "filename": "expense-policy.md",
      "chunk_index": 2,
      "page_number": null,
      "content": "出差期间产生的出租车费用可以报销。",
      "similarity": 0.91
    }
  ]
}
```

回答正文不会输出 `[资料N]` 标记；资料编号只用于模型区分上下文，引用来源由
前端根据 `sources` 单独展示。

`history` 可以省略或传空数组。它只用于理解代词和追问，历史回答不能代替知识库
资料成为事实依据。当前接口不持久化对话，刷新前端页面或点击清空后历史即消失。

一次正常调用会产生一次 embedding 请求和一次聊天模型请求，并读取 PostgreSQL，
不会修改数据库。数据库没有已索引切片，或者召回切片全部低于初始相似度阈值
`0.5` 时，接口直接返回对应的固定说明，不调用聊天模型，也不返回低相关来源。
阈值是求职版的初始值，后续需要结合 RAG 评估集和真实问题分数分布继续调试。

## Streaming Knowledge Answer

流式问答接口保留与普通接口相同的请求结构：

```http
POST /answer/stream
Content-Type: application/json
Accept: text/event-stream
```

接口先执行相同的历史校验、向量检索和相似度过滤，再使用 LangChain
`astream()` 逐块生成答案。响应采用 SSE 协议，事件顺序如下：

```text
event: delta
data: {"content":"出差期间"}

event: delta
data: {"content":"可以报销。"}

event: sources
data: {"sources":[...]}

event: done
data: {}
```

- `delta`：本次新生成的答案文本，前端应按顺序追加，不能覆盖之前内容。
- `sources`：生成结束后的完整引用来源；固定拒答时返回空数组。
- `done`：本次流正常结束。
- `error`：流开始后模型或上游服务异常，前端应停止读取并保留已生成文本。

浏览器使用 `fetch` 发送 POST 请求，并通过 `response.body.getReader()` 读取响应。
`EventSource` 只适合 GET，因此当前页面没有使用它。普通 `POST /answer` 继续保留，
用于非流式调用和兼容现有客户端。

## 简单 RAG 评估

评估前需要满足两个条件：FastAPI 和 PostgreSQL 已启动；
`linxi_company_knowledge.md` 已通过文档上传接口完成向量入库。评估脚本只读取现有
知识库，不上传文件、不写数据库。

先只评估检索和拒答阈值：

```powershell
uv run python -m scripts.evaluate_rag --mode search
```

再执行完整评估，额外检查模型答案关键词和引用来源：

```powershell
uv run python -m scripts.evaluate_rag --mode full
```

扫描多组相似度阈值和 Top-K，并输出推荐组合：

```powershell
uv run python -m scripts.evaluate_rag --mode tune
```

`search` 模式会为每个问题调用一次真实 embedding；`full` 模式还会为每个问题
再次调用 embedding，并为达到相似度阈值的问题调用聊天模型，因此会产生少量百炼
额度消耗。脚本分别输出检索通过率、回答通过率和整体通过率；任一检查失败时返回
非零退出码，便于后续接入自动化验证。

`tune` 模式读取评估集中的 `tuning.thresholds` 和 `tuning.limits`。它为每个问题
只请求一次候选值中最大的 Top-K，再在本地模拟全部参数组合，不会按组合数量重复
调用 embedding，也不会调用聊天模型。输出中的“误拒答”表示相关问题未通过，
“错误放行”表示无关问题仍有切片高于阈值。推荐组合优先考虑通过率和减少错误放行，
但不会自动修改 `app/services/answering.py` 中的当前参数。

评估集中的关键词组支持同义表达：同一组内命中任意一个词即可，不同组必须全部
命中。调整问题或关键词时应以知识库原文和真实回答为依据，不能为了让分数通过而
删除关键事实约束。

## 服务端错误响应

参数校验和文件解析错误继续使用现有的 `4xx` 状态码。请求进入业务链路后，应用
会在 HTTP 边界统一处理以下运行异常：

- 百炼／OpenAI 兼容 SDK 请求失败，或模型响应无法使用：HTTP `502`。
- PostgreSQL 连接、查询或事务失败：HTTP `503`。
- 未分类的内部异常：HTTP `500`。

响应继续使用 FastAPI 标准结构，前端现有请求工具可以直接显示：

```json
{
  "detail": "模型服务暂时不可用，请稍后重试。"
}
```

接口响应不会输出底层异常文本、API Key、数据库地址或密码；项目主动写入的错误
日志只记录异常类型。SSE 流式回答开始后无法再修改 HTTP 状态码，因此仍通过
`error` 事件通知前端中断，并保留已经生成的内容。
