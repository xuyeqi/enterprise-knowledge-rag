"""把较长的中文或英文文本切成适合向量检索的小片段。

这个模块使用 LangChain 官方推荐的 `RecursiveCharacterTextSplitter`。
它会优先按段落、换行和中文句末标点切分；某一段仍然太长时，再继续尝试
更细的标点，最后才按单个字符切分。这里只负责切片，不调用模型或数据库。
"""

# lru_cache 缓存已经创建的切片器。相同参数重复调用时，可以复用同一个对象。
from functools import lru_cache

# RecursiveCharacterTextSplitter 来自 LangChain 的独立文本切片包。
from langchain_text_splitters import RecursiveCharacterTextSplitter


# 默认按字符数衡量切片长度。800 字符是当前阶段便于验证的初始值，后续会根据
# 检索效果再调整，而不是现在提前加入复杂的 token 计算。
DEFAULT_CHUNK_SIZE = 800

# 相邻切片保留约 120 个字符的上下文，降低一句话刚好被边界截断造成的信息损失。
DEFAULT_CHUNK_OVERLAP = 120

# 分隔符按优先级从高到低排列。切片器先尽量保留完整段落和句子，只有内容仍然
# 超过 chunk_size 时，才逐步使用分号、逗号、空格甚至单字符继续拆分。
CHINESE_SEPARATORS = [
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    "；",
    "，",
    ".",
    "!",
    "?",
    ";",
    ",",
    " ",
    "",
]


def validate_splitter_settings(chunk_size: int, chunk_overlap: int) -> None:
    """检查切片长度参数，避免把无效值传给 LangChain。

    参数：
        chunk_size：每个切片允许的最大字符数，必须大于 0。
        chunk_overlap：相邻切片的目标重叠字符数，必须大于等于 0，且必须
            小于 chunk_size，否则切片器无法向后推进。

    异常：
        任一参数不满足约束时抛出 ValueError。
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")


@lru_cache
def get_text_splitter(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    """创建并缓存一套 LangChain 递归字符切片器。

    返回值：
        配置好中文标点、最大长度和重叠长度的切片器对象。
    """

    validate_splitter_settings(chunk_size, chunk_overlap)

    return RecursiveCharacterTextSplitter(
        separators=CHINESE_SEPARATORS,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # len 按 Python 字符数计算长度，中文字符和英文字母都按 1 计数。
        length_function=len,
        # 分隔符列表都是普通字符串，不使用正则表达式语法。
        is_separator_regex=False,
    )


def split_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """把一段非空文本切成有顺序、无空字符串的文本列表。

    参数：
        text：从 txt 或 md 文件读取出的完整文本。
        chunk_size：单个切片最大字符数，默认 800。
        chunk_overlap：相邻切片目标重叠字符数，默认 120。

    返回值：
        按原文顺序排列的字符串列表。短文本通常只返回一个切片。

    异常：
        text 为空或全是空白字符时抛出 ValueError；参数无效时也会抛出
        ValueError。函数不会调用外部 API，也不会产生模型费用。
    """

    # strip 只用于检查内容是否为空。真正切片时仍传入原始 text，避免在这里
    # 擅自删除用户文档首尾可能有意义的换行或空格。
    if not text.strip():
        raise ValueError("text must not be empty")

    splitter = get_text_splitter(chunk_size, chunk_overlap)
    chunks = splitter.split_text(text)

    # LangChain 正常情况下不会返回空切片；这里再过滤一次，让后续 embedding
    # 服务始终只收到有内容的字符串。
    return [chunk for chunk in chunks if chunk.strip()]
