# Backend

FastAPI backend for the enterprise knowledge base RAG project.

## File Purpose

这个目录是后端服务目录。当前阶段只做一个最小 FastAPI 应用，目的是先确认「后端能启动、接口能访问、测试能验证」。

当前文件作用：

- `app/main.py`：FastAPI 应用入口，定义 API 服务和 `/health` 健康检查接口。
- `app/__init__.py`：把 `app` 目录标记为 Python 包，方便用 `from app.main import app` 导入。
- `tests/test_health.py`：使用 FastAPI 测试客户端请求 `/health`，确认接口返回正确。
- `pyproject.toml`：声明 Python 版本、依赖包和测试配置。
- `uv.lock`：uv 根据 `pyproject.toml` 解析出来的锁文件，用来固定依赖版本，保证不同机器安装结果尽量一致。

## Current Scope

This stage only provides the minimal backend skeleton:

- FastAPI application entry.
- `GET /health` endpoint.
- Basic test for the health endpoint.

Database, LangChain and RAG logic will be added in later stages.

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

## Test

```bash
uv run pytest
```

`uv run pytest` 会在 uv 管理的项目环境里执行 pytest。pytest 会自动查找 `tests/` 目录里以 `test_` 开头的测试文件，并执行里面以 `test_` 开头的测试函数。
