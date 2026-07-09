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
│   │   ├── components/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── views/
│   │   └── main.ts
│   ├── package.json
│   └── README.md
├── docker-compose.yml
├── README.md
├── ROADMAP.md
└── CLAUDE.md
```

## 开发原则

- 每个阶段只做能验证的最小闭环。
- 先跑通主链路，再补复杂能力。
- 不引入当前阶段用不到的抽象、依赖和配置项。
- 后端统一使用 uv 管理 Python 依赖和运行命令，不使用 pip 作为项目默认安装方式。
- 所有代码改动必须对应 ROADMAP.md 中的阶段目标。
- 完成开发、修复、文档补齐或重要调研后，同步更新 ROADMAP.md。
- 涉及数据库 schema、环境变量、密钥、CI/CD、发布部署前必须先确认。

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
