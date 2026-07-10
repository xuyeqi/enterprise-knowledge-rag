"""集中读取和整理后端连接 PostgreSQL 所需的配置。

这个文件属于应用的 core（核心配置）模块，只负责把操作系统中的
`RAG_POSTGRES_*` 环境变量转换成 Python 对象，不负责建立数据库连接。
数据库连接模块会调用这里的 `get_database_settings` 获取配置。
"""

# lru_cache 是 Python 标准库提供的缓存装饰器。
# 它会记住函数第一次执行的返回值，后续调用直接复用，不再重复创建配置对象。
from functools import lru_cache

# Path 是 Python 标准库提供的跨平台路径工具。
# 使用它定位项目根目录，可以避免手动拼接 Windows 或 Linux 路径分隔符。
from pathlib import Path

# SecretStr 是 Pydantic 提供的敏感字符串类型。
# 打印 SecretStr 对象时不会直接显示密码，可以降低密码误入日志的风险。
from pydantic import SecretStr

# BaseSettings 会自动从环境变量读取字段值；SettingsConfigDict 用来配置读取规则。
from pydantic_settings import BaseSettings, SettingsConfigDict

# URL 是 SQLAlchemy 提供的数据库地址对象。
# 使用 URL.create 组装地址，可以避免手动拼接字符串时遗漏转义特殊字符。
from sqlalchemy import URL


# __file__ 是 Python 自动提供的变量，值是当前 config.py 文件的路径。
# resolve() 会把它转换成绝对路径，parents[3] 再向上查找三层：
# core -> app -> backend -> 项目根目录。
# PROJECT_ROOT 是本项目自定义常量，用于准确定位根目录下的 .env 文件，
# 这样无论从项目根目录还是 backend 目录启动服务，读取的都是同一个文件。
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class DatabaseSettings(BaseSettings):
    """保存一组完整的 PostgreSQL 连接配置。

    这个类继承 BaseSettings，所以创建实例时会自动读取环境变量。
    `env_prefix="RAG_POSTGRES_"` 会给字段名前加统一前缀，例如：

    - `host` 对应 `RAG_POSTGRES_HOST`
    - `port` 对应 `RAG_POSTGRES_PORT`
    - `password` 对应 `RAG_POSTGRES_PASSWORD`

    配置会优先读取操作系统环境变量，缺少的值再从项目根目录的 `.env`
    读取。没有默认值的 password 必须由其中一种方式提供；如果两处都没有，
    Pydantic 会主动报错，防止程序在不知道数据库密码的情况下继续运行。
    """

    # model_config 是 Pydantic 约定的类级配置变量，不是数据库中的配置表。
    # env_file 指定本地配置文件；env_file_encoding 保证中文注释按 UTF-8 读取。
    # extra="ignore" 表示 .env 中以后增加其它模块的变量时，不会因此报错。
    model_config = SettingsConfigDict(
        env_prefix="RAG_POSTGRES_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 以下名称都是本项目自定义的配置字段。
    # 冒号后的 str 或 int 是类型标注，等号右侧是没有环境变量时使用的默认值。
    host: str = "127.0.0.1"
    port: int = 5432
    user: str = "rag_user"

    # password 故意不设置默认值，并用 SecretStr 包装，真实密码不能写进代码。
    password: SecretStr
    db: str = "rag_db"

    # @property 把方法包装成只读属性。
    # 调用方写 settings.database_url 即可，不需要写 settings.database_url()。
    @property
    def database_url(self) -> URL:
        """根据各配置字段生成 SQLAlchemy 使用的数据库地址。

        返回值：
            SQLAlchemy 的 URL 对象，内容包含驱动、用户名、密码、主机、
            端口和数据库名。该对象会交给 `create_async_engine` 使用。
        """

        return URL.create(
            # postgresql 表示数据库类型，asyncpg 表示使用异步 PostgreSQL 驱动。
            drivername="postgresql+asyncpg",
            username=self.user,

            # get_secret_value 用于在真正创建连接时取出 SecretStr 中的原始密码。
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.db,
        )


# @lru_cache 表示这个无参数函数在当前 Python 进程中只真正创建一次配置对象。
@lru_cache
def get_database_settings() -> DatabaseSettings:
    """创建并返回当前应用共用的数据库配置对象。

    返回值：
        DatabaseSettings 实例。第一次调用时从环境变量读取配置，后续调用
        返回缓存中的同一个实例，避免每个 HTTP 请求都重复解析环境变量。
    """

    return DatabaseSettings()
