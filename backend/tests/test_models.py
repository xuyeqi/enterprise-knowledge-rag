"""验证 SQLAlchemy 模型声明是否符合当前最小数据库设计。

这些测试只检查 Python 中的表结构清单，不连接真实 PostgreSQL，也不会创建、
删除或修改任何数据库对象。真实 schema 仍需执行 Alembic 迁移后单独验证。
"""

from app.models import Document, DocumentChunk
from app.models.document import EMBEDDING_DIMENSION


def test_document_table_has_expected_columns() -> None:
    """确认 documents 表包含最小闭环所需的字段。"""

    # __table__ 是 SQLAlchemy 根据模型类生成的表结构对象。
    column_names = set(Document.__table__.columns.keys())

    assert column_names == {
        "id",
        "filename",
        "content_type",
        "status",
        "created_at",
    }


def test_document_chunk_embedding_uses_1024_dimensions() -> None:
    """确认切片向量维度与百炼 text-embedding-v4 配置一致。"""

    embedding_column = DocumentChunk.__table__.columns["embedding"]

    # pgvector 的 Vector 类型会把维度保存在 dim 属性中。
    assert EMBEDDING_DIMENSION == 1024
    assert embedding_column.type.dim == EMBEDDING_DIMENSION
    assert embedding_column.nullable is False


def test_document_chunk_has_document_foreign_key() -> None:
    """确认每个切片都通过外键关联到 documents 表。"""

    document_id_column = DocumentChunk.__table__.columns["document_id"]
    foreign_key_targets = {key.target_fullname for key in document_id_column.foreign_keys}

    assert foreign_key_targets == {"documents.id"}
