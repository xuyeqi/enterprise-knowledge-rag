"""验证 RAG 评估工具的评分规则。

这些测试只使用内存中的模拟响应，不启动 FastAPI、不访问 PostgreSQL，也不会调用
百炼。真实检索分数和回答质量仍需要开发者运行 ``scripts.evaluate_rag`` 验证。
"""

from pathlib import Path

from scripts.evaluate_rag import (
    EvaluationCase,
    evaluate_answer_response,
    evaluate_search_response,
    load_evaluation_cases,
)


def make_positive_case() -> EvaluationCase:
    """创建一个同时要求业务方向和产品类型的正向样例。"""

    return EvaluationCase(
        case_id="company_business",
        question="公司主要做什么？",
        expected_refusal=False,
        expected_retrieval_terms=(("跨境电商",), ("天然石饰品",)),
        expected_answer_terms=(("跨境电商",), ("天然石", "饰品")),
    )


def test_default_evaluation_cases_are_valid() -> None:
    """确认仓库自带评估集可以加载，ID 唯一且基础参数与当前问答阈值一致。"""

    cases_path = Path(__file__).resolve().parents[1] / "evaluation" / "rag_cases.json"

    threshold, limit, cases = load_evaluation_cases(cases_path)

    assert threshold == 0.5
    assert limit == 3
    assert len(cases) == 5
    assert len({case.case_id for case in cases}) == len(cases)


def test_search_evaluation_uses_only_chunks_above_threshold() -> None:
    """确认低相关切片即使包含关键词，也不能让检索评估错误通过。"""

    check = evaluate_search_response(
        make_positive_case(),
        {
            "results": [
                {
                    "content": "公司经营跨境电商，核心产品为天然石饰品。",
                    "similarity": 0.49,
                }
            ]
        },
        threshold=0.5,
    )

    assert check.passed is False
    assert "高于阈值切片 0 个" in check.detail


def test_search_evaluation_accepts_expected_retrieval_terms() -> None:
    """确认达到阈值且覆盖全部关键词组的检索结果可以通过。"""

    check = evaluate_search_response(
        make_positive_case(),
        {
            "results": [
                {
                    "content": "公司主要经营跨境电商，核心产品是天然石饰品。",
                    "similarity": 0.91,
                }
            ]
        },
        threshold=0.5,
    )

    assert check.passed is True


def test_answer_evaluation_accepts_keyword_alternative_and_source() -> None:
    """确认回答可使用关键词组中的同义表达，但正向回答必须保留引用。"""

    check = evaluate_answer_response(
        make_positive_case(),
        {
            "answer": "公司主要经营跨境电商，产品以天然石为核心。",
            "sources": [{"filename": "linxi_company_knowledge.md"}],
        },
    )

    assert check.passed is True


def test_refusal_requires_no_sources_and_refusal_wording() -> None:
    """确认无关问题既不能返回来源，也必须给出明确的无法回答说明。"""

    refusal_case = EvaluationCase(
        case_id="unrelated",
        question="Python 的 GIL 是什么？",
        expected_refusal=True,
        expected_retrieval_terms=(),
        expected_answer_terms=(("无法回答", "没有找到"),),
    )

    passed_check = evaluate_answer_response(
        refusal_case,
        {"answer": "知识库中没有找到相关资料，暂时无法回答。", "sources": []},
    )
    hallucinated_check = evaluate_answer_response(
        refusal_case,
        {"answer": "GIL 是全局解释器锁。", "sources": []},
    )

    assert passed_check.passed is True
    assert hallucinated_check.passed is False
