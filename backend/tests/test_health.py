# TestClient 是 FastAPI 提供的测试客户端。
# 它不需要真的启动 uvicorn 服务，也能像发送 HTTP 请求一样测试接口。
from fastapi.testclient import TestClient

# 从后端入口文件导入 app。
# 这里的 app 就是 backend/app/main.py 里创建的 FastAPI 实例。
from app.main import app


def test_health_check_returns_ok() -> None:
    # 创建一个测试客户端，后面可以用 client.get、client.post 等方法请求接口。
    client = TestClient(app)

    # 发送 GET 请求到 /health。
    response = client.get("/health")

    # 断言状态码是 200，表示请求成功。
    assert response.status_code == 200

    # 断言接口返回的 JSON 内容正好是 {"status": "ok"}。
    assert response.json() == {"status": "ok"}


def test_database_health_check_returns_connected(monkeypatch) -> None:
    """验证数据库健康检查接口成功时的 HTTP 响应。

    参数：
        monkeypatch：pytest 自动提供的测试工具，可以在当前测试期间临时
        替换对象，测试结束后会自动恢复，不会修改生产代码。

    这里不连接真实 PostgreSQL，只验证接口是否正确调用检查函数并返回
    约定格式。真实数据库连接需要另外启动服务后进行集成验证。
    """

    # 这个测试替身必须也是 async 函数，因为生产代码会用 await 调用它。
    # 函数正常返回 None，用来模拟数据库连接检查成功。
    async def fake_check_database_connection() -> None:
        return None

    # 临时把 app.main 中真正访问数据库的函数替换为上面的测试替身。
    # 这样单元测试不依赖 Docker、数据库密码或本机 PostgreSQL 状态。
    monkeypatch.setattr(
        "app.main.check_database_connection",
        fake_check_database_connection,
    )

    # client 是测试客户端，用来模拟浏览器向 FastAPI 发送 HTTP 请求。
    client = TestClient(app)

    # 请求数据库健康检查接口。由于连接函数已被替换，不会访问真实数据库。
    response = client.get("/health/db")

    # 200 表示接口执行成功；JSON 内容必须符合前后端约定。
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
