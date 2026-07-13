"""验证中文文本切片服务的最小行为。

这些测试只在内存中处理字符串，不读取文件、不访问数据库，也不调用模型 API。
"""

import pytest

from app.services.text_splitter import split_text


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_split_text_rejects_empty_content(text: str) -> None:
    """确认空字符串和纯空白文本不会进入后续 embedding 流程。"""

    with pytest.raises(ValueError, match="must not be empty"):
        split_text(text)


def test_split_text_keeps_short_text_in_one_chunk() -> None:
    """确认长度未超过上限的文本不会被无意义地拆开。"""

    text = "员工报销需要提供真实有效的费用凭证。"

    chunks = split_text(text)

    assert chunks == [text]


def test_split_text_splits_long_text_and_respects_size_limit() -> None:
    """确认长文本会产生多个非空切片，且每片不超过指定长度。"""

    text = "这是用于验证中文切片行为的较长句子。" * 20

    chunks = split_text(text, chunk_size=60, chunk_overlap=10)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 60 for chunk in chunks)


def test_split_text_preserves_overlap_when_falling_back_to_characters() -> None:
    """确认无法按标点拆分时，相邻切片仍保留指定的重叠字符。"""

    # 这段文本不包含配置中的分隔符，切片器最终只能按单字符拆分。
    text = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    chunks = split_text(text, chunk_size=10, chunk_overlap=3)

    assert len(chunks) > 1
    assert chunks[0][-3:] == chunks[1][:3]


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (10, -1), (10, 10), (10, 11)],
)
def test_split_text_rejects_invalid_settings(
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """确认不合理的长度和重叠配置会给出明确错误。"""

    with pytest.raises(ValueError):
        split_text(
            "有效文本",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
