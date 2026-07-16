"""为文档切片增加 PDF 来源页码。

Revision ID: 20260715_002
Revises: 20260711_001
Create Date: 2026-07-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision 和 down_revision 把本文件接到已有迁移之后，Alembic 会按顺序执行。
revision: str = "20260715_002"
down_revision: str | None = "20260711_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加可空页码字段，不改写或删除任何现有切片数据。"""

    # 可空字段让已有 TXT／Markdown 切片自动保持 NULL，无需数据回填。
    op.add_column(
        "document_chunks",
        sa.Column("page_number", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """删除页码字段。

    警告：执行 downgrade 会丢失已经保存的 PDF 页码，必须再次获得用户确认。
    """

    op.drop_column("document_chunks", "page_number")
