# 从 fastapi 包中导入 FastAPI 类。
# 类可以理解为「创建对象的模板」；这里用它创建整个 API 应用。
from fastapi import FastAPI

# app 是 FastAPI 的应用实例，也是 uvicorn 启动时要寻找的对象。
# title 和 version 会出现在自动生成的接口文档里，例如 /docs。
app = FastAPI(
    title="Enterprise Knowledge Base RAG API",
    version="0.1.0",
)


# @app.get("/health") 是装饰器语法。
# 它的意思是：当浏览器或客户端用 GET 方法访问 /health 时，
# FastAPI 就执行下面这个 health_check 函数。
@app.get("/health")
async def health_check() -> dict[str, str]:
    # async def 表示这是一个异步函数，适合 Web 服务处理并发请求。
    # -> dict[str, str] 是类型标注，表示返回值是一个字典：
    # key 是字符串，value 也是字符串。
    # FastAPI 会自动把 Python 字典转换成 JSON 响应。
    return {"status": "ok"}
