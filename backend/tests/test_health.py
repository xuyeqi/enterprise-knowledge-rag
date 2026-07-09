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
