"""提供文档列表、txt／md 上传预览和正式向量入库接口。

两个上传接口共用文件名、大小、编码和空内容校验。列表接口只读取文档摘要；
预览接口只返回切片；正式接口会调用百炼并把结果写入 PostgreSQL。
"""

# dataclass 用来定义只承载数据的小对象，避免在两个接口间传递含义不清的元组。
from dataclasses import dataclass

# Path 用于读取文件扩展名；把反斜杠替换为斜杠后还能兼容浏览器上传的路径。
from pathlib import Path

# Annotated 可以同时保存 UploadFile 类型信息和 FastAPI 的 File 参数说明。
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
# func 提供 SQL COUNT 聚合；select 用于构造只读文档列表查询。
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_database_session
# 列表查询直接读取两个数据库模型，但只选择摘要字段，不加载切片正文和向量。
from app.models.document import Document, DocumentChunk
from app.schemas.document import (
    ChunkPreview,
    DocumentIndexResponse,
    DocumentListItem,
    DocumentPreviewResponse,
)
from app.services.document_indexing import index_document
from app.services.text_splitter import split_text


# router 是本文件自定义的路由集合。prefix 会自动加到下面每一个接口路径前。
router = APIRouter(prefix="/documents", tags=["documents"])

# 2 * 1024 * 1024 表示 2 MiB。读取时会多读 1 字节，用于判断文件是否超限。
MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024

# 媒体类型不直接信任浏览器传值，而是根据允许的扩展名统一确定。
ALLOWED_FILE_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
}


@dataclass(frozen=True)
class ParsedTextUpload:
    """保存一份已经通过公共上传校验的文本文档。

    这个对象由 `read_and_validate_text_upload` 创建，再交给预览接口或正式入库
    接口使用。frozen=True 表示创建后不能误改字段，有助于保证两个后续流程
    拿到的是同一份已经校验过的数据。
    """

    filename: str
    content_type: str
    text: str


def normalize_and_validate_filename(filename: str | None) -> tuple[str, str]:
    """清理上传路径，并确认文件扩展名属于 txt 或 md。

    参数：
        filename：UploadFile 提供的文件名，某些客户端可能不提供。

    返回值：
        二元组 `(安全文件名, 媒体类型)`。

    异常：
        缺少文件名时返回 HTTP 400；扩展名不支持时返回 HTTP 415。
    """

    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件必须包含文件名",
        )

    # 浏览器有时可能传入 C:\fakepath\example.md。先统一路径分隔符，再只取
    # 最后一段文件名，防止把客户端路径信息带入响应或后续存储。
    safe_filename = Path(filename.replace("\\", "/")).name
    extension = Path(safe_filename).suffix.lower()

    if extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="只支持上传 .txt 和 .md 文件",
        )

    return safe_filename, ALLOWED_FILE_TYPES[extension]


async def read_and_validate_text_upload(file: UploadFile) -> ParsedTextUpload:
    """读取并校验 FastAPI 收到的 txt 或 md 上传文件。

    参数：
        file：FastAPI 从 multipart/form-data 请求中解析出的上传文件。

    返回值：
        包含安全文件名、可信媒体类型和 UTF-8 文本的 ParsedTextUpload。

    异常：
        文件名缺失、扩展名不支持、超过 2 MiB、编码错误或内容为空时抛出
        HTTPException，由 FastAPI 转换成对应的 4xx JSON 响应。
    """

    safe_filename, content_type = normalize_and_validate_filename(file.filename)

    try:
        # 多读 1 字节是为了区分“刚好 2 MiB”和“已经超过 2 MiB”。
        raw_content = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    finally:
        # 无论读取成功还是失败，都关闭 UploadFile 使用的临时资源。
        await file.close()

    if len(raw_content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="文件大小不能超过 2 MB",
        )

    try:
        # utf-8-sig 兼容普通 UTF-8 和带 BOM 的 UTF-8 文本，并自动移除 BOM。
        text = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件必须使用 UTF-8 编码",
        ) from error

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件不能为空",
        )

    return ParsedTextUpload(
        filename=safe_filename,
        content_type=content_type,
        text=text,
    )


@router.get("", response_model=list[DocumentListItem])
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[DocumentListItem]:
    """返回按入库时间倒序排列的文档摘要列表。

    查询通过 LEFT OUTER JOIN 和 COUNT 一次得到文档及切片数量。只选择列表展示
    所需字段，不加载切片正文和 1024 维 embedding，避免列表页浪费内存。
    """

    statement = (
        select(
            Document.id,
            Document.filename,
            Document.status,
            Document.created_at,
            func.count(DocumentChunk.id).label("chunk_count"),
        )
        .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
        .group_by(
            Document.id,
            Document.filename,
            Document.status,
            Document.created_at,
        )
        .order_by(Document.created_at.desc())
    )

    result = await session.execute(statement)
    return [
        DocumentListItem(
            document_id=row.id,
            filename=row.filename,
            status=row.status,
            chunk_count=row.chunk_count,
            created_at=row.created_at,
        )
        for row in result.all()
    ]


@router.post("/preview", response_model=DocumentPreviewResponse)
async def preview_document(
    file: Annotated[
        UploadFile,
        File(description="需要预览切片结果的 UTF-8 txt 或 md 文件"),
    ],
) -> DocumentPreviewResponse:
    """读取上传文件并返回切片预览，不产生持久化或模型费用。

    执行步骤：
        1. 校验文件名和扩展名。
        2. 最多读取 2 MiB 加 1 字节，判断是否超过大小限制。
        3. 使用 UTF-8 解码，并拒绝空文本。
        4. 调用 `split_text`，组装每个切片的顺序、长度和完整内容。
    """

    upload = await read_and_validate_text_upload(file)
    chunks = split_text(upload.text)
    chunk_previews = [
        ChunkPreview(
            index=index,
            character_count=len(chunk),
            content=chunk,
        )
        for index, chunk in enumerate(chunks)
    ]

    return DocumentPreviewResponse(
        filename=upload.filename,
        content_type=upload.content_type,
        character_count=len(upload.text),
        chunk_count=len(chunk_previews),
        chunks=chunk_previews,
    )


@router.post(
    "",
    response_model=DocumentIndexResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    file: Annotated[
        UploadFile,
        File(description="需要生成向量并写入知识库的 UTF-8 txt 或 md 文件"),
    ],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DocumentIndexResponse:
    """生成整份文档的向量，并原子写入 PostgreSQL。

    执行步骤：
        1. 复用预览接口的文件校验，得到安全文件名和文本。
        2. `index_document` 完成切片、分批调用百炼和数据库事务。
        3. 只有数据库 commit 成功后才返回 HTTP 201 和文档 ID。

    如果百炼调用失败，数据库写入尚未开始；如果数据库写入失败，业务服务会
    rollback。两种情况都不会错误地返回“入库成功”。
    """

    upload = await read_and_validate_text_upload(file)
    document = await index_document(
        session,
        filename=upload.filename,
        content_type=upload.content_type,
        text=upload.text,
    )

    return DocumentIndexResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        chunk_count=len(document.chunks),
    )
