"""手动调用一次百炼 embedding API，验证真实配置和返回维度。

这个脚本会产生一次真实网络请求，并可能消耗百炼额度，因此不会被 pytest
自动执行。请在确认 `.env` 使用的是新建且未泄露的 Key 后手动运行。
"""

import asyncio

from app.core.config import get_embedding_settings
from app.services.embedding import embed_texts


async def main() -> None:
    """生成一条测试向量，只输出非敏感的模型名、维度和少量向量值。"""

    test_text = "企业员工提交报销申请时，需要提供真实有效的费用凭证。"
    settings = get_embedding_settings()
    vectors = await embed_texts([test_text])
    vector = vectors[0]

    # 不打印 API Key，也不打印完整的 1024 个数字，避免终端输出过长。
    print(f"model: {settings.model}")
    print(f"dimension: {len(vector)}")
    print(f"first_5_values: {vector[:5]}")


if __name__ == "__main__":
    # asyncio.run 是普通 Python 脚本启动异步 main 函数的入口。
    asyncio.run(main())
