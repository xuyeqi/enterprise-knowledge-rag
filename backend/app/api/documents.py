"""提供 txt／md 文件上传和文本切片预览接口。

当前接口只在内存中读取文件并调用 `split_text`，不会保存原文件、调用百炼或
写入 PostgreSQL。这样可以先独立验证 HTTP 上传、UTF-8 解码和切片边界。
"""

# Path 用于读取文件扩展名；把反斜杠替换为斜杠后还能兼容浏览器上传的路径。
from pathlib import Path

# Annotated 可以同时保存 UploadFile 类型信息和 FastAPI 的 File 参数说明。
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.document import ChunkPreview, DocumentPreviewResponse
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

    chunks = split_text(text)
    chunk_previews = [
        ChunkPreview(
            index=index,
            character_count=len(chunk),
            content=chunk,
        )
        for index, chunk in enumerate(chunks)
    ]

    return DocumentPreviewResponse(
        filename=safe_filename,
        content_type=content_type,
        character_count=len(text),
        chunk_count=len(chunk_previews),
        chunks=chunk_previews,
    )
