"""解析知识库上传文件，并生成带来源页码的文本切片。

这个服务位于 HTTP 上传接口和向量入库服务之间：TXT／Markdown 按 UTF-8
解码后直接切片；PDF 使用 pypdf 逐页提取文本，并在切片上保留从 1 开始的
页码。这里只处理文本型 PDF，不执行 OCR，也不调用模型或数据库。
"""

# BytesIO 把内存中的 PDF 字节包装成 pypdf 可以读取的二进制文件对象。
from io import BytesIO

# dataclass 用于声明解析结果，避免在接口与入库服务之间传递无含义的元组。
from dataclasses import dataclass

# PdfReader 来自 pypdf，用于读取 PDF 页结构并提取每页的文本层。
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.text_splitter import split_text


class DocumentParseError(ValueError):
    """表示文件格式正确但内容无法转换为可索引文本。"""


@dataclass(frozen=True)
class ParsedDocumentChunk:
    """保存一个待向量化切片及其可选 PDF 页码。"""

    content: str
    # 普通文本没有页概念，因此使用 None；PDF 页码从 1 开始，便于用户阅读。
    page_number: int | None = None


@dataclass(frozen=True)
class ParsedDocument:
    """保存上传文件解析后的统计信息和全部有序切片。"""

    character_count: int
    chunks: list[ParsedDocumentChunk]


def parse_text_document(raw_content: bytes) -> ParsedDocument:
    """将 TXT／Markdown 字节解码并切成不带页码的文本片段。

    参数：
        raw_content：上传接口已经完成大小校验的原始文件字节。

    返回值：
        文档字符数和按原文顺序排列的切片。

    异常：
        文件不是 UTF-8 或没有实际文本时抛出 DocumentParseError。
    """

    try:
        # utf-8-sig 同时兼容普通 UTF-8 和带 BOM 的 UTF-8 文本。
        text = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentParseError("文件必须使用 UTF-8 编码") from error

    if not text.strip():
        raise DocumentParseError("上传文件不能为空")

    return ParsedDocument(
        character_count=len(text),
        chunks=[ParsedDocumentChunk(content=chunk) for chunk in split_text(text)],
    )


def parse_pdf_document(raw_content: bytes) -> ParsedDocument:
    """逐页提取文本型 PDF，并为每个切片记录真实页码。

    每一页单独调用现有中文切片器，因此切片不会跨越页面边界。空白页会被
    跳过；如果所有页面都没有文本层，则明确提示当前版本不支持扫描件 OCR。

    参数：
        raw_content：上传接口已经完成大小校验的 PDF 原始字节。

    返回值：
        所有可提取字符的总数，以及按页码和页内顺序排列的切片。

    异常：
        PDF 损坏、加密或没有可提取文本时抛出 DocumentParseError。
    """

    try:
        reader = PdfReader(BytesIO(raw_content))
        if reader.is_encrypted:
            raise DocumentParseError("暂不支持加密 PDF 文件")

        chunks: list[ParsedDocumentChunk] = []
        character_count = 0

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if not page_text.strip():
                continue

            character_count += len(page_text)
            chunks.extend(
                ParsedDocumentChunk(content=chunk, page_number=page_number)
                for chunk in split_text(page_text)
            )
    except DocumentParseError:
        raise
    except (PdfReadError, OSError, ValueError) as error:
        raise DocumentParseError("PDF 文件无法解析，请确认文件完整且未加密") from error

    if not chunks:
        raise DocumentParseError("PDF 未提取到可用文本，暂不支持扫描件或纯图片 PDF")

    return ParsedDocument(character_count=character_count, chunks=chunks)


def parse_document(raw_content: bytes, extension: str) -> ParsedDocument:
    """根据已经校验过的扩展名选择文本或 PDF 解析流程。"""

    if extension == ".pdf":
        return parse_pdf_document(raw_content)
    return parse_text_document(raw_content)
