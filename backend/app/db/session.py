"""创建 PostgreSQL 异步数据库引擎，并提供最小连通性检查。

这个文件位于 db（database）模块中，负责把 core/config.py 提供的配置
交给 SQLAlchemy，生成可以重复使用的数据库引擎。目前只做连接检查，
还没有创建数据表、会话工厂或业务数据的增删改查逻辑。
"""

# 使用缓存保证整个应用进程复用同一个数据库引擎和连接池。
from functools import lru_cache

# text 会把普通 SQL 字符串包装为 SQLAlchemy 可以安全执行的 SQL 表达式。
from sqlalchemy import text

# AsyncEngine 是异步数据库引擎的类型；create_async_engine 用来创建该引擎。
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# 导入项目自定义函数，用于取得数据库主机、端口、用户和密码等配置。
from app.core.config import get_database_settings


@lru_cache
def get_database_engine() -> AsyncEngine:
    """创建并缓存应用共用的 SQLAlchemy 异步数据库引擎。

    数据库引擎可以理解为后端访问 PostgreSQL 的入口，它内部还会管理
    连接池。缓存引擎可以让不同请求复用连接池，避免每次请求都重新创建。

    返回值：
        AsyncEngine 实例，供异步函数建立和释放数据库连接。
    """

    # settings 是本项目自定义的局部变量，保存已经解析好的数据库配置。
    settings = get_database_settings()

    # pool_pre_ping=True 表示取出连接池中的旧连接前先检查它是否仍然可用，
    # 可以减少数据库重启后复用到失效连接的情况。
    return create_async_engine(settings.database_url, pool_pre_ping=True)


async def check_database_connection() -> None:
    """检查后端是否能够正常连接 PostgreSQL。

    执行步骤：
        1. 获取应用共用的异步数据库引擎。
        2. 从引擎管理的连接池中取得一个数据库连接。
        3. 执行 `SELECT 1`，确认数据库能够接收连接并处理查询。
        4. 离开 async with 代码块时自动归还连接。

    返回值：
        没有返回值。函数正常结束就表示数据库连接和查询均成功。

    异常：
        数据库未启动、地址错误、密码错误或查询失败时，SQLAlchemy 或
        asyncpg 会抛出异常，由调用这个函数的上层接口处理。
    """

    # engine 是本项目自定义的局部变量，指向缓存中的异步数据库引擎。
    engine = get_database_engine()

    # async with 是异步上下文管理器语法：进入时取得连接，退出时自动归还。
    # connection 是当前代码块临时使用的数据库连接对象。
    async with engine.connect() as connection:
        # await 表示等待数据库完成异步查询，但不会阻塞整个 Web 服务进程。
        # SELECT 1 不读取或修改业务数据，只用于验证最基本的查询能力。
        await connection.execute(text("SELECT 1"))
