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
- Backend：Python + FastAPI + LangChain
- Database：PostgreSQL + pgvector
- LLM：OpenAI-compatible API

## 当前状态

项目处于阶段 1：项目初始化。

当前已完成：

- 确定项目方向。
- 确定技术栈。
- 建立项目规范、路线图和说明文档。

下一步：

- 初始化 FastAPI 后端。
- 添加 /health 接口。
- 添加 PostgreSQL + pgvector 本地开发环境。

## 学习重点

这个项目重点不是训练大模型，而是掌握企业级 AI 应用落地常见能力：

- RAG 基础链路。
- 文档处理。
- 向量检索。
- 模型 API 调用。
- 前后端分离。
- 数据库设计。
- 可验证的工程闭环。
