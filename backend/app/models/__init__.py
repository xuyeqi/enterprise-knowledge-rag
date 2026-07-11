"""集中导出项目的数据模型。

Alembic 导入这个包时，会继续导入下面的模型类。导入动作会让 SQLAlchemy
把 `documents` 和 `document_chunks` 表登记到 `Base.metadata` 中。
"""

from app.models.document import Document, DocumentChunk

# __all__ 明确说明使用 `from app.models import *` 时允许导出的名称。
__all__ = ["Document", "DocumentChunk"]
