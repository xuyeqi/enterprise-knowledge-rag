"""验证 TXT／Markdown 和 PDF 文档解析服务。

PDF 测试使用内存中的假页对象替换 pypdf 读取器，不依赖真实文件、数据库或
模型。这里重点验证逐页切片、页码保留以及扫描件提示等项目业务规则。
"""

from types import SimpleNamespace

import pytest

from app.services import document_parser
from app.services.document_parser import DocumentParseError


def test_parse_text_document_returns_chunks_without_page_number() -> None:
    """确认普通文本沿用 UTF-8 解码和切片规则，并且不伪造页码。"""

    content = "# 公司制度\n\n员工应遵守公司制度。"

    parsed = document_parser.parse_text_document(content.encode("utf-8"))

    assert parsed.character_count == len(content)
    assert [chunk.content for chunk in parsed.chunks] == [content]
    assert [chunk.page_number for chunk in parsed.chunks] == [None]


def test_parse_pdf_document_keeps_real_page_numbers(monkeypatch) -> None:
    """确认空白页被跳过，文本页切片仍保留原 PDF 页码。"""

    pages = [
        SimpleNamespace(extract_text=lambda: "第一页公司介绍"),
        SimpleNamespace(extract_text=lambda: "   "),
        SimpleNamespace(extract_text=lambda: "第三页产品介绍"),
    ]

    class FakePdfReader:
        """提供解析服务实际读取的最小 pypdf 接口。"""

        is_encrypted = False

        def __init__(self, stream) -> None:
            assert stream.read() == b"fake pdf"
            self.pages = pages

    monkeypatch.setattr(document_parser, "PdfReader", FakePdfReader)

    parsed = document_parser.parse_pdf_document(b"fake pdf")

    assert parsed.character_count == len("第一页公司介绍") + len("第三页产品介绍")
    assert [chunk.content for chunk in parsed.chunks] == [
        "第一页公司介绍",
        "第三页产品介绍",
    ]
    assert [chunk.page_number for chunk in parsed.chunks] == [1, 3]


def test_parse_pdf_document_rejects_scanned_pdf(monkeypatch) -> None:
    """确认没有文本层的 PDF 会提示扫描件暂不支持，而不是建立空索引。"""

    class FakePdfReader:
        """模拟只有图片、无法提取文本层的 PDF。"""

        is_encrypted = False

        def __init__(self, stream) -> None:
            self.pages = [SimpleNamespace(extract_text=lambda: None)]

    monkeypatch.setattr(document_parser, "PdfReader", FakePdfReader)

    with pytest.raises(DocumentParseError, match="暂不支持扫描件"):
        document_parser.parse_pdf_document(b"fake pdf")


def test_parse_pdf_document_rejects_encrypted_pdf(monkeypatch) -> None:
    """确认加密 PDF 在读取页面前就返回明确错误。"""

    class FakePdfReader:
        """模拟 pypdf 已识别到加密标记的文件。"""

        is_encrypted = True
        pages = []

        def __init__(self, stream) -> None:
            pass

    monkeypatch.setattr(document_parser, "PdfReader", FakePdfReader)

    with pytest.raises(DocumentParseError, match="暂不支持加密 PDF"):
        document_parser.parse_pdf_document(b"fake pdf")
