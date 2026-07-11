"""启用 pgvector，并创建文档与文档切片表。

Revision ID: 20260711_001
Revises: None
Create Date: 2026-07-11
"""

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


# 这些变量构成 Alembic 的迁移版本链。
# 这是项目第一次迁移，所以 down_revision 为 None，没有上一个版本。
revision: str = "20260711_001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """启用 vector 扩展，并创建最小 RAG 存储结构。

    执行顺序：
        1. 启用 pgvector 的 vector 扩展。
        2. 创建 documents 表。
        3. 创建 document_chunks 表和外键。
        4. 为 document_id 创建普通索引，加快按文档查询切片。
    """

    # IF NOT EXISTS 让数据库已经启用 vector 时不会重复报错。
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # Vector(1024) 必须与 text-embedding-v4 的 dimensions=1024 一致。
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_chunks"),
        sa.UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_id_chunk_index",
        ),
    )

    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    """撤销本次迁移创建的表和 vector 扩展。

    警告：执行 downgrade 会删除表及其中的数据。项目规范要求执行回滚前
    必须再次确认，不能把这个函数当作普通测试命令运行。
    """

    # 删除顺序与创建顺序相反，先删除依赖 documents 的切片表。
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("documents")

    # 两张向量表删除后才能安全删除 vector 扩展。
    op.execute("DROP EXTENSION IF EXISTS vector")
