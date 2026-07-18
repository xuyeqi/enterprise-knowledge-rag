"""集中读取和整理后端连接 PostgreSQL、调用百炼模型所需的配置。

这个文件属于应用的 core（核心配置）模块，只负责把操作系统中的
`RAG_POSTGRES_*` 环境变量转换成 Python 对象，不负责建立数据库连接。
数据库连接模块会调用 `get_database_settings`，embedding 和问答服务会分别调用
对应的模型配置函数。所有配置类共享项目根目录的 `.env` 文件。
"""

# lru_cache 是 Python 标准库提供的缓存装饰器。
# 它会记住函数第一次执行的返回值，后续调用直接复用，不再重复创建配置对象。
from functools import lru_cache

# Path 是 Python 标准库提供的跨平台路径工具。
# 使用它定位项目根目录，可以避免手动拼接 Windows 或 Linux 路径分隔符。
from pathlib import Path

# SecretStr 是 Pydantic 提供的敏感字符串类型。
# 打印 SecretStr 对象时不会直接显示密码，可以降低密码误入日志的风险。
from pydantic import Field, SecretStr, field_validator

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


class EmbeddingSettings(BaseSettings):
    """保存阿里云百炼文本向量接口所需的配置。

    这里没有使用统一前缀，因为百炼 Key 使用 `DASHSCOPE_API_KEY`，模型名称
    和维度使用更通用的 `EMBEDDING_*`。Field 的 validation_alias 明确指定
    每个 Python 字段对应哪个环境变量。

    API Key 没有默认值，必须放在本地 `.env` 或操作系统环境变量中。
    SecretStr 可以避免调试输出意外显示完整 Key。
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr = Field(validation_alias="DASHSCOPE_API_KEY")
    base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias="DASHSCOPE_BASE_URL",
    )
    model: str = Field(
        default="text-embedding-v4",
        validation_alias="EMBEDDING_MODEL",
    )
    dimension: int = Field(
        default=1024,
        validation_alias="EMBEDDING_DIMENSION",
    )

    # field_validator 会在配置对象创建时检查 dimension，而不是等到写数据库时
    # 才发现维度不匹配。当前表字段固定为 vector(1024)，所以只允许 1024。
    @field_validator("dimension")
    @classmethod
    def validate_dimension_matches_database(cls, value: int) -> int:
        """确保 API 返回维度与数据库 vector(1024) 字段一致。

        参数：
            value：从 EMBEDDING_DIMENSION 读取并转换成整数后的值。

        返回值：
            校验成功后原样返回 1024，交给 Pydantic 保存。

        异常：
            值不是 1024 时抛出 ValueError，阻止应用使用错误配置启动调用。
        """

        if value != 1024:
            raise ValueError(
                "EMBEDDING_DIMENSION must be 1024 to match vector(1024)"
            )
        return value


@lru_cache
def get_embedding_settings() -> EmbeddingSettings:
    """创建并缓存应用共用的百炼 embedding 配置对象。"""

    return EmbeddingSettings()


class ChatSettings(BaseSettings):
    """保存阿里云百炼知识库问答模型所需的配置。

    问答模型与 embedding 模型复用同一个百炼 API Key 和 OpenAI 兼容地址，
    但使用独立的 `CHAT_MODEL` 环境变量，避免两类模型名称互相覆盖。
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr = Field(validation_alias="DASHSCOPE_API_KEY")
    base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias="DASHSCOPE_BASE_URL",
    )
    model: str = Field(
        default="qwen3.7-plus",
        validation_alias="CHAT_MODEL",
    )


@lru_cache
def get_chat_settings() -> ChatSettings:
    """创建并缓存应用共用的百炼问答模型配置对象。"""

    return ChatSettings()


class RedisSettings(BaseSettings):
    """保存后台文档索引队列的 Redis 连接地址。

    Redis 只保存任务参数、状态和短期结果，不代替 PostgreSQL
    保存最终的文档和向量。本地默认连接 Docker Compose 对外暴露的
    6379 端口，需要时可通过 `RAG_REDIS_URL` 覆盖。
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = Field(
        default="redis://127.0.0.1:6379/0",
        validation_alias="RAG_REDIS_URL",
    )


@lru_cache
def get_redis_settings() -> RedisSettings:
    """创建并缓存应用共用的 Redis 队列配置对象。"""

    return RedisSettings()
