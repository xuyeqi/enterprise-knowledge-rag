# 项目路线图

## 当前阶段

阶段 2：最小 RAG 闭环

当前目标：先完成最小数据库 schema 和迁移机制，再逐步实现文档上传、切片、向量写入、检索问答和引用来源。

## 已完成

- 2026-07-09：确定项目方向为企业知识库 RAG 问答系统。
- 2026-07-09：确定技术栈为 Vue3 + TypeScript、FastAPI + LangChain、PostgreSQL + pgvector。
- 2026-07-09：补充项目规范文档、路线图和项目说明。
- 2026-07-09：补充第二步后端骨架的新手向文件说明和代码注释。
- 2026-07-09：统一后端依赖管理方式为 uv，并修正安装、测试和启动命令文档。
- 2026-07-09：完成后端最小骨架，包含 FastAPI 应用、`/health` 接口和健康检查测试；已通过 `uv run pytest` 验证。
- 2026-07-10：启动 PostgreSQL + pgvector 容器，并通过 VS Code 插件验证 `rag_db` 可以连接。
- 2026-07-10：完成异步数据库配置、SQLAlchemy 引擎和 `/health/db` 接口；用户执行 `uv run pytest` 两次均为 `2 passed, 1 warning`，并确认真实接口返回 `{"status":"ok","database":"connected"}`。
- 2026-07-10：阶段 1 项目初始化完成，进入阶段 2 最小 RAG 闭环。
- 2026-07-11：完成 Alembic 迁移机制、`vector` 扩展、`documents` 和 `document_chunks` 表；用户执行迁移后确认数据库出现两张业务表和 `alembic_version` 版本表。
- 2026-07-11：完成百炼 `text-embedding-v4` 异步调用服务；离线测试通过，真实 API 返回 1024 维向量。
- 2026-07-11：完成 LangChain 中文递归文本切片服务；用户执行 pytest，切片测试及现有测试全部通过。

## 进行中

- 阶段 2：最小 RAG 闭环。
- 已确定百炼 `text-embedding-v4` 和 1024 维向量。
- 最小 SQLAlchemy 模型和第一次 Alembic 迁移已应用，模型与接口测试已全部通过。
- 百炼 embedding 配置、异步客户端、响应校验、离线测试和真实 API 调用均已验证。
- LangChain 中文递归文本切片服务和离线测试已验证通过。

## 待办

### 阶段 2：最小 RAG 闭环

- 支持上传 txt / md 文档。
- 实现文档切片。
- 将文档片段和 embedding 写入 PostgreSQL + pgvector。
- 实现基于知识库的问答接口。
- 返回答案和引用来源。

### 阶段 3：前端最小界面

- 初始化 Vue3 + TypeScript + Vite 前端。
- 实现文档列表。
- 实现文档上传入口。
- 实现聊天问答页面。
- 展示回答引用来源。

### 阶段 4：工程化增强

- 增加对话历史。
- 增加流式回答。
- 增加索引状态展示。
- 增加基础错误处理。
- 增加后端测试。

### 阶段 5：简历亮点增强

- 增加 PDF 文档解析。
- 增加无相关资料时拒答策略。
- 增加检索参数调试。
- 增加简单评估样例。
- 视情况引入 LangGraph 编排问答流程。

## 阻塞

- 暂无。

## 最近验证

- 2026-07-11：用户执行 pytest，新增文本切片测试及现有测试全部通过。
- 2026-07-11：新增 LangChain `RecursiveCharacterTextSplitter` 中文切片服务，默认 800 字符、120 字符重叠，并增加空文本、短文本、长文本、重叠和参数边界测试；尚未执行验证，因此未标记完成。
- 2026-07-11：用户运行 pytest，新增 embedding 模拟测试及现有测试均通过。
- 2026-07-11：用户执行 `uv run python -m scripts.check_embedding`，模型名称、1024 维向量长度和向量样例输出均符合预期；确认本地配置可以真实调用百炼。
- 2026-07-11：实现百炼 `text-embedding-v4` 异步客户端，固定单批最多 10 条、1024 维输出，并增加不访问网络的模拟测试和手动真实调用脚本；尚未执行验证，因此未标记完成。
- 2026-07-11：用户首次执行 `uv run alembic upgrade head` 时，Windows 使用 GBK 读取含 UTF-8 中文注释的 `alembic.ini`，触发 `UnicodeDecodeError`；已将该配置文件改为纯 ASCII，等待重新执行迁移验证。
- 2026-07-11：用户重新执行迁移成功，并在 `rag_db` 中确认 `documents`、`document_chunks` 和 `alembic_version` 三张表存在。
- 2026-07-11：用户执行 `uv run pytest`，5 个测试全部通过；结果为 `5 passed, 1 warning`，warning 仍来自 FastAPI/Starlette TestClient 依赖层，不影响当前模型和接口测试。
- 2026-07-11：确定阿里云百炼 `text-embedding-v4`，项目统一使用 1024 维 dense embedding。
- 2026-07-11：新增 `documents`、`document_chunks` SQLAlchemy 模型和第一次 Alembic 迁移；尚未执行 `uv sync`、pytest 或真实数据库迁移，因此未标记完成。
- 2026-07-10：用户执行 `uv run pytest` 两次，结果分别为 `2 passed, 1 warning`；warning 来自 FastAPI/Starlette TestClient 依赖层，不影响测试通过。
- 2026-07-10：用户启动后端并访问 `/health/db`，真实返回 `{"status":"ok","database":"connected"}`，确认 FastAPI、SQLAlchemy、asyncpg 和 PostgreSQL 链路连通。
- 2026-07-10：增加 `.env.example`，并让后端自动读取项目根目录的 `.env`；真实密码仍由 `.gitignore` 排除，本次等待用户执行测试验证。
- 2026-07-10：按照新手向注释规范补充数据库配置、异步引擎、健康检查接口及测试代码说明；本次只修改注释，未执行测试。
- 2026-07-10：细化新手向代码注释规范，要求生成代码解释文件职责、导入来源、自定义变量、关键语法、调用流程和数据流向。
- 2026-07-10：补充学习型协作分工：Codex 负责编写和解释，用户负责执行依赖同步、测试与服务启动命令；未收到真实结果前不得标记完成。
- 2026-07-09：文档初始化完成并已提交。
- 2026-07-09：后端文件已创建；本机 `python` 和 `py` 命令不可用，暂无法运行 FastAPI 或 pytest。
- 2026-07-09：后端骨架注释补充完成；本次为注释和说明更新，未新增运行验证项。
- 2026-07-09：已核对 uv 官方项目命令，确认 `uv sync --extra dev` 和 `uv run ...` 是当前后端文档采用的命令形式。
- 2026-07-09：当前终端执行 `uv --version` 失败，说明 uv 未安装或未加入 PATH；已在文档中补充 uv 安装和检查命令。
- 2026-07-09：修复后端 pytest 导入路径配置，并使用 `uv run pytest` 完成验证；结果为 `1 passed, 1 warning`，warning 为 FastAPI/Starlette TestClient 依赖层弃用提醒，不影响当前健康检查测试通过。
- 2026-07-09：新增 PostgreSQL + pgvector 的 `docker-compose.yml`，`docker compose config` 已通过；`docker compose up -d postgres` 因 Docker daemon 未运行失败，容器启动待复验。
- 2026-07-10：用户已启动 PostgreSQL + pgvector，并通过 VS Code 插件连接 `rag_db`；`vector` 扩展可用性查询结果符合预期。

## 待确认

- 千问对话模型的具体型号，等问答接口阶段再确定。
