# 从 fastapi 包中导入 FastAPI 类。
# 类可以理解为「创建对象的模板」；这里用它创建整个 API 应用。
from fastapi import FastAPI

# 导入文档路由集合，后面通过 include_router 注册到 FastAPI 应用。
from app.api.documents import router as documents_router

# 从项目的数据库模块导入连接检查函数，供 /health/db 接口调用。
from app.db.session import check_database_connection

# app 是 FastAPI 的应用实例，也是 uvicorn 启动时要寻找的对象。
# title 和 version 会出现在自动生成的接口文档里，例如 /docs。
app = FastAPI(
    title="Enterprise Knowledge Base RAG API",
    version="0.1.0",
)

# include_router 会把 documents.py 中定义的接口加入当前应用。
# 注册后可以访问切片预览和正式入库接口，并在 /docs 中看到 documents 分组。
app.include_router(documents_router)


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


# 这个装饰器把下面的函数注册为 GET /health/db 接口。
# 用户或监控程序访问该地址时，FastAPI 会执行 database_health_check。
@app.get("/health/db")
async def database_health_check() -> dict[str, str]:
    """通过真实数据库查询检查 FastAPI 到 PostgreSQL 的连接。

    返回值：
        数据库查询成功时返回包含两个字符串字段的字典，FastAPI 会把它
        自动转换成 JSON。如果连接失败，底层数据库异常会使请求失败，
        因而不会错误地返回 `database: connected`。
    """

    # await 等待异步数据库检查完成；没有抛出异常才会继续执行下一行。
    await check_database_connection()

    # 这是接口成功时的固定响应，不包含数据库密码等敏感信息。
    return {"status": "ok", "database": "connected"}
