# 项目路线图

## 当前阶段

阶段 1：项目初始化

目标：建立项目规范，搭建 FastAPI 后端骨架，接入 PostgreSQL + pgvector，并提供可验证的健康检查接口。

## 已完成

- 2026-07-09：确定项目方向为企业知识库 RAG 问答系统。
- 2026-07-09：确定技术栈为 Vue3 + TypeScript、FastAPI + LangChain、PostgreSQL + pgvector。
- 2026-07-09：补充项目规范文档、路线图和项目说明。
- 2026-07-09：补充第二步后端骨架的新手向文件说明和代码注释。
- 2026-07-09：统一后端依赖管理方式为 uv，并修正安装、测试和启动命令文档。
- 2026-07-09：完成后端最小骨架，包含 FastAPI 应用、`/health` 接口和健康检查测试；已通过 `uv run pytest` 验证。

## 进行中

- 阶段 1：项目初始化。
- PostgreSQL + pgvector 的 Docker Compose 配置已添加，等待 Docker Desktop 启动后验证容器运行。

## 待办

### 阶段 1：项目初始化

- 添加 docker-compose.yml，启动 PostgreSQL + pgvector。（配置已实现，容器启动待验证）
- 添加数据库配置和连接检查。
- 验证后端启动和数据库连通。

### 阶段 2：最小 RAG 闭环

- 支持上传 txt / md 文档。
- 实现文档切片。
- 调用 embedding 模型生成向量。
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

- 当前 Codex 环境无法连接 Docker daemon，`docker compose up -d postgres` 报错 `dockerDesktopLinuxEngine` 管道不存在；需要先启动 Docker Desktop 后再复跑。

## 最近验证

- 2026-07-09：文档初始化完成并已提交。
- 2026-07-09：后端文件已创建；本机 `python` 和 `py` 命令不可用，暂无法运行 FastAPI 或 pytest。
- 2026-07-09：后端骨架注释补充完成；本次为注释和说明更新，未新增运行验证项。
- 2026-07-09：已核对 uv 官方项目命令，确认 `uv sync --extra dev` 和 `uv run ...` 是当前后端文档采用的命令形式。
- 2026-07-09：当前终端执行 `uv --version` 失败，说明 uv 未安装或未加入 PATH；已在文档中补充 uv 安装和检查命令。
- 2026-07-09：修复后端 pytest 导入路径配置，并使用 `uv run pytest` 完成验证；结果为 `1 passed, 1 warning`，warning 为 FastAPI/Starlette TestClient 依赖层弃用提醒，不影响当前健康检查测试通过。
- 2026-07-09：新增 PostgreSQL + pgvector 的 `docker-compose.yml`，`docker compose config` 已通过；`docker compose up -d postgres` 因 Docker daemon 未运行失败，容器启动待复验。

## 待确认

- 模型供应商和 API 兼容地址。
- 本地是否使用 Docker 启动 PostgreSQL + pgvector。
