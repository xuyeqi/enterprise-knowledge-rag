"""配置 Alembic 使用异步 SQLAlchemy 引擎执行数据库迁移。

Alembic 执行命令时会加载这个文件。它会读取项目根目录 `.env` 中的
PostgreSQL 配置，导入所有数据模型，并把 `Base.metadata` 交给 Alembic。
"""

# asyncio 用于从普通命令行入口运行异步迁移函数。
import asyncio

# Alembic 的 context 对象保存当前迁移命令和配置。
from alembic import context

# NullPool 表示迁移命令不长期保留数据库连接，命令结束即可释放资源。
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.core.config import get_database_settings
from app.db.base import Base

# 导入模型包的目的不是直接使用类，而是触发模型注册到 Base.metadata。
# noqa 注释告诉代码检查工具：这个看似未使用的导入是有意保留的。
from app import models  # noqa: F401


# config 是当前 alembic.ini 对应的配置对象。
config = context.config

# target_metadata 是 Alembic 自动比较数据库与 Python 模型时使用的结构清单。
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """在不建立真实连接的离线模式下生成迁移 SQL。

    离线模式不会直接执行 SQL，常用于把迁移内容输出为脚本。URL 中需要包含
    真实密码才能完整表示连接信息，因此这里明确关闭 SQLAlchemy 的密码隐藏。
    """

    settings = get_database_settings()
    database_url = settings.database_url.render_as_string(hide_password=False)

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """把 Alembic 的同步迁移逻辑放到异步数据库连接中执行。

    参数：
        connection：SQLAlchemy 提供给 Alembic 的同步连接代理对象。
    """

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """连接真实 PostgreSQL，并执行尚未应用的迁移。"""

    settings = get_database_settings()

    # connectable 是迁移专用异步引擎，不复用 Web 服务的长期连接池。
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    # async with 会在迁移结束后自动关闭本次数据库连接。
    async with connectable.connect() as connection:
        # run_sync 让 Alembic 的同步迁移函数安全运行在异步连接中。
        await connection.run_sync(do_run_migrations)

    # dispose 释放异步引擎持有的底层资源。
    await connectable.dispose()


# context.is_offline_mode() 根据命令参数判断当前是否为离线模式。
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
