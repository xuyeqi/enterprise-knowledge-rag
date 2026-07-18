"""验证异步文档索引的入队、去重和 HTTP 状态查询。

测试使用内存假任务替代 Redis 和 RQ Worker，不连接真实 Redis、
PostgreSQL 或百炼模型。
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from rq.exceptions import DuplicateJobError

from app.api import documents as documents_api
from app.main import app
from app.services import document_jobs


class FakeJob:
    """实现状态转换实际使用的最小 RQ Job 接口。"""

    def __init__(
        self,
        *,
        job_id: str = "document-test",
        status: str = "queued",
        result=None,
    ) -> None:
        self.id = job_id
        self.status = status
        self.result = result
        self.meta = {"filename": "policy.md"}

    def get_status(self, *, refresh: bool = False) -> str:
        assert refresh is True
        return self.status

    def get_meta(self, *, refresh: bool = False) -> dict[str, str]:
        assert refresh is True
        return self.meta


def test_document_job_id_is_stable_for_same_content() -> None:
    """确认相同内容总是生成相同 ID，不同内容不会误判为重复。"""

    first = document_jobs.build_document_job_id(b"same content")
    second = document_jobs.build_document_job_id(b"same content")
    different = document_jobs.build_document_job_id(b"different content")

    assert first == second
    assert first != different
    assert first.startswith("document-")


def test_enqueue_document_job_uses_unique_job_and_retry(monkeypatch) -> None:
    """确认入队时启用 Redis 原子去重和三次分段重试。"""

    captured = {}

    class FakeQueue:
        def enqueue(self, function_name: str, **options):
            captured["function_name"] = function_name
            captured.update(options)
            return FakeJob(job_id=options["job_id"])

    monkeypatch.setattr(document_jobs, "get_document_queue", lambda: FakeQueue())

    snapshot = document_jobs.enqueue_document_job(
        raw_content=b"# policy",
        extension=".md",
        filename="policy.md",
        content_type="text/markdown",
    )

    assert snapshot.status == "queued"
    assert snapshot.deduplicated is False
    assert captured["unique"] is True
    assert captured["retry"].max == 3
    assert captured["retry"].intervals == [10, 30, 60]


def test_enqueue_document_job_returns_existing_duplicate(monkeypatch) -> None:
    """确认相同内容已存在时返回原任务，不重复入队。"""

    class DuplicateQueue:
        def enqueue(self, *args, **kwargs):
            raise DuplicateJobError("duplicate")

    existing_job = FakeJob(status="started")
    monkeypatch.setattr(document_jobs, "get_document_queue", lambda: DuplicateQueue())
    monkeypatch.setattr(document_jobs, "get_redis_connection", lambda: object())
    monkeypatch.setattr(
        document_jobs.Job,
        "fetch",
        lambda job_id, connection: existing_job,
    )

    snapshot = document_jobs.enqueue_document_job(
        raw_content=b"# policy",
        extension=".md",
        filename="policy.md",
        content_type="text/markdown",
    )

    assert snapshot.status == "started"
    assert snapshot.deduplicated is True


def test_create_and_read_document_job_endpoints(monkeypatch) -> None:
    """确认异步上传返回 202，状态接口能返回最终文档结果。"""

    monkeypatch.setattr(
        documents_api,
        "enqueue_document_job",
        lambda **kwargs: SimpleNamespace(
            job_id="document-test",
            status="queued",
            deduplicated=False,
        ),
    )
    monkeypatch.setattr(
        documents_api,
        "get_document_job",
        lambda job_id: SimpleNamespace(
            job_id=job_id,
            filename="policy.md",
            status="finished",
            document_id="12345678-1234-5678-1234-567812345678",
            chunk_count=1,
            error=None,
        ),
    )
    client = TestClient(app)

    create_response = client.post(
        "/documents/jobs",
        files={"file": ("policy.md", "# 报销规则".encode(), "text/markdown")},
    )
    status_response = client.get("/documents/jobs/document-test")

    assert create_response.status_code == 202
    assert create_response.json() == {
        "job_id": "document-test",
        "status": "queued",
        "deduplicated": False,
    }
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "finished"
    assert status_response.json()["chunk_count"] == 1
