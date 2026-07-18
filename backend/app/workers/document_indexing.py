"""在 RQ Worker 进程中执行文档解析、向量化和数据库写入。

这个文件属于 workers 模块。RQ 通过函数的字符串路径导入本文件，
完成后把文档 ID 和切片数量写回 Redis，供 FastAPI 状态接口读取。
"""

import asyncio

from app.db.session import get_database_engine, get_database_session_factory
from app.services.document_indexing import index_document
from app.services.document_parser import parse_document


async def _index_document(
    *,
    raw_content: bytes,
    extension: str,
    filename: str,
    content_type: str,
) -> dict[str, str | int]:
    """在独立异步事件循环中完成一份文档的原子入库。"""

    parsed_document = parse_document(raw_content, extension)
    session_factory = get_database_session_factory()

    try:
        async with session_factory() as session:
            document = await index_document(
                session,
                filename=filename,
                content_type=content_type,
                chunks=parsed_document.chunks,
            )

        return {
            "document_id": str(document.id),
            "chunk_count": len(document.chunks),
        }
    finally:
        # SpawnWorker 为每个任务启动独立子进程。在事件循环关闭前
        # 释放 asyncpg 连接，避免子进程退出时留下未清理资源。
        await get_database_engine().dispose()


def process_document_indexing_job(
    *,
    raw_content: bytes,
    extension: str,
    filename: str,
    content_type: str,
) -> dict[str, str | int]:
    """作为 RQ 同步任务入口，运行项目现有的异步索引链路。"""

    return asyncio.run(
        _index_document(
            raw_content=raw_content,
            extension=extension,
            filename=filename,
            content_type=content_type,
        )
    )
