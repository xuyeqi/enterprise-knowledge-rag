"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}


# revision 是当前迁移的唯一编号；down_revision 指向上一个迁移编号。
revision: str = ${repr(up_revision)}
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """把数据库结构升级到当前版本。"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """撤销当前版本引入的数据库结构。"""
    ${downgrades if downgrades else "pass"}
