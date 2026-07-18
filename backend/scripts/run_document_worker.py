"""启动文档索引 RQ Worker。

请在 backend 目录执行 `uv run python -m scripts.run_document_worker`。
脚本在 Windows 上使用 SpawnWorker，并启用调度器处理延迟重试。
"""

from rq import SpawnWorker

from app.services.document_jobs import get_document_queue, get_redis_connection


def main() -> None:
    """连接 Redis，并持续消费文档索引队列。"""

    queue = get_document_queue()
    worker = SpawnWorker([queue], connection=get_redis_connection())
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
