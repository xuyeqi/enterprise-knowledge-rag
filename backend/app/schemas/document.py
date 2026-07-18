"""定义文档上传预览和正式入库接口返回的 JSON 数据结构。

这些类继承 Pydantic BaseModel。FastAPI 会根据它们验证返回数据，并自动在
Swagger 文档中生成字段说明和示例结构。
"""

# datetime 用于描述数据库记录的带时区创建时间。
from datetime import datetime
# Literal 把任务状态限制为前后端约定的五个字符串。
from typing import Literal
# UUID 用于描述数据库为文档生成的全局唯一标识符。
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkPreview(BaseModel):
    """表示一个文本切片的预览信息。"""

    # index 是切片在原文中的顺序，第一片从 0 开始。
    index: int = Field(description="切片在原文中的顺序，从 0 开始")

    page_number: int | None = Field(
        default=None,
        description="PDF 来源页码，从 1 开始；普通文本为 null",
    )

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


class DocumentIndexResponse(BaseModel):
    """表示文档和全部向量切片已经成功写入数据库。"""

    # document_id 供后续文档列表、删除和引用来源接口稳定定位这份文档。
    document_id: UUID = Field(description="数据库为文档生成的唯一标识符")
    filename: str = Field(description="清理路径信息后的原始文件名")
    status: str = Field(description="文档当前处理状态，成功入库时为 indexed")
    chunk_count: int = Field(description="已经写入数据库的切片数量")


class DocumentJobCreateResponse(BaseModel):
    """表示文档已被后台队列接收，但尚未必完成索引。"""

    job_id: str = Field(description="根据文件内容生成的稳定任务 ID")
    status: Literal["queued", "started", "retrying", "finished", "failed"] = Field(
        description="任务的当前处理状态"
    )
    deduplicated: bool = Field(
        description="true 表示相同内容已存在，本次未重复入队"
    )


class DocumentJobStatusResponse(BaseModel):
    """表示前端轮询得到的文档索引任务快照。"""

    job_id: str = Field(description="后台任务 ID")
    filename: str = Field(description="经过路径清理的上传文件名")
    status: Literal["queued", "started", "retrying", "finished", "failed"] = Field(
        description="排队、执行、重试、成功或失败状态"
    )
    document_id: str | None = Field(
        default=None,
        description="索引成功后生成的数据库文档 ID",
    )
    chunk_count: int | None = Field(
        default=None,
        description="索引成功后写入的切片数量",
    )
    error: str | None = Field(
        default=None,
        description="终态失败时返回的安全错误说明",
    )


class DocumentListItem(BaseModel):
    """表示文档列表中的一条摘要，不包含切片正文或 embedding。"""

    document_id: UUID = Field(description="数据库中的文档唯一标识符")
    filename: str = Field(description="用户上传时的文件名")
    status: str = Field(description="文档当前处理状态")
    chunk_count: int = Field(description="该文档已经写入的切片数量")
    created_at: datetime = Field(description="文档入库时间")
