"""定义原始文档和文档切片对应的数据库模型。

一条 Document 记录代表用户上传的一份 txt 或 md 文件；一条 DocumentChunk
记录代表文档切分后的一个文本片段。每个片段保存一份 1024 维 embedding，
后续用户提问时会用问题向量和这些片段向量计算相似度。
"""

# uuid 是 Python 标准库，uuid.uuid4 可以生成随机且基本不会重复的标识符。
import uuid

# datetime 只用于类型标注，告诉编辑器 created_at 字段在 Python 中是时间对象。
from datetime import datetime

# Vector 是 pgvector 提供给 SQLAlchemy 的向量字段类型。
from pgvector.sqlalchemy import Vector

# 下面这些 SQLAlchemy 类型分别对应数据库中的时间、外键、整数、字符串和长文本。
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func

# Mapped 描述模型属性对应数据库字段；mapped_column 创建字段；relationship 描述表关系。
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# 这是本项目固定的 embedding 维度，必须与百炼 text-embedding-v4 调用时传入的
# dimensions=1024 保持一致。修改它必须同时新增数据库迁移，不能只改这个数字。
EMBEDDING_DIMENSION = 1024


class Document(Base):
    """表示用户上传的一份原始文档。

    `__tablename__` 指定真实数据库表名。一个 Document 可以关联多个
    DocumentChunk；删除文档对象时，ORM 会同时删除属于它的切片对象。
    """

    __tablename__ = "documents"

    # id 是主键。default=uuid.uuid4 表示创建 Python 对象时自动生成 UUID。
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # filename 保存用户上传时的原始文件名，例如 handbook.md。
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # content_type 保存文件的媒体类型，例如 text/plain 或 text/markdown。
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # status 记录文档处理状态。当前默认 pending，后续可改为 indexed 或 failed。
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    # server_default=func.now() 表示由 PostgreSQL 在插入记录时填写创建时间。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # chunks 不是 documents 表中的独立字段，而是 SQLAlchemy 提供的关系属性。
    # list[DocumentChunk] 表示一份文档可以拥有多个切片。
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    """表示文档切分后的一个文本片段及其 embedding 向量。"""

    __tablename__ = "document_chunks"

    # 同一份文档内的 chunk_index 不能重复，保证切片顺序具有唯一性。
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_id_chunk_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # document_id 是外键，指向 documents.id。
    # ondelete="CASCADE" 表示数据库删除文档时自动删除其所有切片。
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # chunk_index 从 0 开始记录切片在原文中的顺序。
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # content 保存切片的完整文本。Text 适合长度不固定的长字符串。
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # embedding 保存百炼 text-embedding-v4 返回的 1024 个浮点数。
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSION),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # document 是从切片反向访问所属文档的关系属性，与 Document.chunks 配对。
    document: Mapped[Document] = relationship(back_populates="chunks")
