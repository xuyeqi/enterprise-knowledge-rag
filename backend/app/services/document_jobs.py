"""管理 Redis 中的异步文档索引任务。

这个文件属于 services 模块，位于 FastAPI 接口与 RQ Worker 之间。
上传接口通过这里入队和查询状态，Worker 再调用真正的文档索引函数。
"""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import Any, Literal

from redis import Redis
from rq import Queue, Retry
from rq.exceptions import DuplicateJobError, NoSuchJobError
from rq.job import Job

from app.core.config import get_redis_settings


DOCUMENT_QUEUE_NAME = "document-indexing"
DOCUMENT_JOB_FUNCTION = (
    "app.workers.document_indexing.process_document_indexing_job"
)
DOCUMENT_JOB_TIMEOUT_SECONDS = 10 * 60
DOCUMENT_JOB_TTL_SECONDS = 24 * 60 * 60
DOCUMENT_JOB_RETRY_INTERVALS_SECONDS = [10, 30, 60]

DocumentJobStatus = Literal[
    "queued",
    "started",
    "retrying",
    "finished",
    "failed",
]


class DocumentJobNotFoundError(Exception):
    """表示 Redis 中已经不存在指定的文档任务。"""


@dataclass(frozen=True)
class DocumentJobSnapshot:
    """表示可以安全返回给前端的任务状态快照。"""

    job_id: str
    filename: str
    status: DocumentJobStatus
    deduplicated: bool = False
    document_id: str | None = None
    chunk_count: int | None = None
    error: str | None = None


@lru_cache
def get_redis_connection() -> Redis:
    """创建并缓存 RQ 与 FastAPI 共用的 Redis 连接客户端。"""

    return Redis.from_url(get_redis_settings().url)


@lru_cache
def get_document_queue() -> Queue:
    """创建并缓存专门处理文档索引的 RQ 队列。"""

    return Queue(DOCUMENT_QUEUE_NAME, connection=get_redis_connection())


def build_document_job_id(raw_content: bytes) -> str:
    """用文件内容生成稳定任务 ID，使相同文件只会入队一次。"""

    return f"document-{sha256(raw_content).hexdigest()}"


def _status_value(job: Job) -> str:
    """把 RQ 可能返回的枚举或字符串统一为小写字符串。"""

    status = job.get_status(refresh=True)
    value = getattr(status, "value", status)
    return str(value).lower()


def _snapshot_from_job(job: Job, *, deduplicated: bool = False) -> DocumentJobSnapshot:
    """把 RQ Job 内部对象转换为稳定的业务状态。"""

    rq_status = _status_value(job)
    if rq_status == "started":
        public_status: DocumentJobStatus = "started"
    elif rq_status == "scheduled":
        # 本项目不主动创建定时任务，scheduled 只会在失败后
        # 按 10、30、60 秒间隔等待下一次重试时出现。
        public_status = "retrying"
    elif rq_status == "finished":
        public_status = "finished"
    elif rq_status in {"failed", "stopped", "canceled"}:
        public_status = "failed"
    else:
        public_status = "queued"

    meta = job.get_meta(refresh=True)
    filename = str(meta.get("filename", ""))
    result: Any = job.result if public_status == "finished" else None
    if not isinstance(result, dict):
        result = {}

    return DocumentJobSnapshot(
        job_id=job.id,
        filename=filename,
        status=public_status,
        deduplicated=deduplicated,
        document_id=result.get("document_id"),
        chunk_count=result.get("chunk_count"),
        error=(
            "文档索引失败，请稍后重试。"
            if public_status == "failed"
            else None
        ),
    )


def enqueue_document_job(
    *,
    raw_content: bytes,
    extension: str,
    filename: str,
    content_type: str,
) -> DocumentJobSnapshot:
    """将一份已经通过校验的文档放入 Redis 后台队列。

    RQ 的 `unique=True` 会在 Redis 内原子检查自定义 job_id。如果用户
    重复上传相同内容，这里返回原任务而不会重复调用向量模型。
    """

    job_id = build_document_job_id(raw_content)
    queue = get_document_queue()

    try:
        job = queue.enqueue(
            DOCUMENT_JOB_FUNCTION,
            kwargs={
                "raw_content": raw_content,
                "extension": extension,
                "filename": filename,
                "content_type": content_type,
            },
            job_id=job_id,
            unique=True,
            meta={"filename": filename},
            retry=Retry(max=3, interval=DOCUMENT_JOB_RETRY_INTERVALS_SECONDS),
            job_timeout=DOCUMENT_JOB_TIMEOUT_SECONDS,
            ttl=DOCUMENT_JOB_TTL_SECONDS,
            result_ttl=DOCUMENT_JOB_TTL_SECONDS,
            failure_ttl=DOCUMENT_JOB_TTL_SECONDS,
            description=f"索引文档：{filename}",
        )
    except DuplicateJobError:
        # 去重冲突说明 Redis 中已有同内容任务，直接读取它的
        # 最新状态。这个分支不会再把任务推入队列。
        job = Job.fetch(job_id, connection=get_redis_connection())
        return _snapshot_from_job(job, deduplicated=True)

    return _snapshot_from_job(job)


def get_document_job(job_id: str) -> DocumentJobSnapshot:
    """从 Redis 读取任务的当前状态和成功结果。"""

    try:
        job = Job.fetch(job_id, connection=get_redis_connection())
    except NoSuchJobError as error:
        raise DocumentJobNotFoundError(job_id) from error

    return _snapshot_from_job(job)
