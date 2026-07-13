"""定义文档上传预览接口返回的 JSON 数据结构。

这些类继承 Pydantic BaseModel。FastAPI 会根据它们验证返回数据，并自动在
Swagger 文档中生成字段说明和示例结构。
"""

from pydantic import BaseModel, Field


class ChunkPreview(BaseModel):
    """表示一个文本切片的预览信息。"""

    # index 是切片在原文中的顺序，第一片从 0 开始。
    index: int = Field(description="切片在原文中的顺序，从 0 开始")

    # character_count 使用 Python len 计算，与当前切片器的长度算法一致。
    character_count: int = Field(description="当前切片包含的字符数")

    # content 返回完整切片文本，便于当前阶段在 Swagger 中人工核对边界。
    content: str = Field(description="当前切片的完整文本")


class DocumentPreviewResponse(BaseModel):
    """表示上传文件完成读取和切片后的预览结果。"""

    filename: str = Field(description="清理路径信息后的原始文件名")
    content_type: str = Field(description="根据扩展名确定的文本媒体类型")
    character_count: int = Field(description="整份文档包含的字符数")
    chunk_count: int = Field(description="文档被拆分出的切片数量")
    chunks: list[ChunkPreview] = Field(description="按原文顺序排列的切片列表")
