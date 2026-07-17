"""运行一组可重复的 RAG 检索与回答评估样例。

这个脚本属于开发期评估工具，不参与 FastAPI 请求链路。它读取
``evaluation/rag_cases.json``，调用已经启动的 ``POST /search`` 和
``POST /answer``，再依据期望关键词、引用来源和相似度阈值生成汇总结果。

评估会发起真实 embedding 请求；full 模式还会调用聊天模型。脚本只读取现有
知识库，不上传文档、不写数据库，也不会修改相似度阈值。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any
from urllib import error, request


# 默认评估集跟随后端代码提交，开发者从 backend 目录执行命令时无需手写路径。
DEFAULT_CASES_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "rag_cases.json"


@dataclass(frozen=True)
class EvaluationCase:
    """表示一个问题及其检索、回答期望。

    每个关键词组中的词是“任选一个”，不同关键词组之间是“全部满足”。例如
    ``[["侯林希", "林希总"], ["老板"]]`` 表示文本必须出现老板，并至少出现
    侯林希或林希总中的一个。这可以容纳模型的正常措辞变化，同时避免只检查一个
    宽泛关键词造成误判。
    """

    case_id: str
    question: str
    expected_refusal: bool
    expected_retrieval_terms: tuple[tuple[str, ...], ...]
    expected_answer_terms: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class EvaluationCheck:
    """保存某个评估环节的通过状态和便于定位失败原因的说明。"""

    passed: bool
    detail: str


@dataclass(frozen=True)
class TuningResult:
    """保存一组相似度阈值和 Top-K 在全部检索样例上的表现。"""

    threshold: float
    limit: int
    passed: int
    total: int
    false_rejections: int
    false_acceptances: int

    @property
    def accuracy(self) -> float:
        """返回通过样例占比，供终端展示和推荐规则比较。"""

        return self.passed / self.total


def parse_term_groups(raw_groups: Any, *, field_name: str) -> tuple[tuple[str, ...], ...]:
    """校验 JSON 中的关键词组，并转换为不可变元组。

    参数：
        raw_groups：从 JSON 读取的关键词组原始值。
        field_name：当前字段名，只用于生成清晰的配置错误。

    返回值：
        清理过空白、且每组至少包含一个关键词的嵌套元组。

    异常：
        配置不是二维字符串数组，或存在空关键词组时抛出 ValueError。
    """

    if not isinstance(raw_groups, list):
        raise ValueError(f"{field_name} must be a list")

    parsed_groups: list[tuple[str, ...]] = []
    for group in raw_groups:
        if not isinstance(group, list):
            raise ValueError(f"each {field_name} item must be a list")

        parsed_group = tuple(
            term.strip()
            for term in group
            if isinstance(term, str) and term.strip()
        )
        if not parsed_group or len(parsed_group) != len(group):
            raise ValueError(f"each {field_name} group must contain non-blank strings")
        parsed_groups.append(parsed_group)

    return tuple(parsed_groups)


def load_evaluation_cases(path: Path) -> tuple[float, int, list[EvaluationCase]]:
    """从 JSON 文件读取阈值、召回数量和评估问题。"""

    with path.open(encoding="utf-8") as cases_file:
        payload = json.load(cases_file)

    threshold = float(payload["relevance_threshold"])
    limit = int(payload["limit"])
    if not 0 <= threshold <= 1:
        raise ValueError("relevance_threshold must be between 0 and 1")
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")

    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("cases must be a non-empty list")

    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise ValueError("each case must be an object")

        case_id = str(raw_case.get("id", "")).strip()
        question = str(raw_case.get("question", "")).strip()
        if not case_id or case_id in seen_ids:
            raise ValueError("each case id must be non-blank and unique")
        if not question:
            raise ValueError(f"case {case_id} question must not be blank")

        seen_ids.add(case_id)
        cases.append(
            EvaluationCase(
                case_id=case_id,
                question=question,
                expected_refusal=bool(raw_case.get("expected_refusal", False)),
                expected_retrieval_terms=parse_term_groups(
                    raw_case.get("expected_retrieval_terms", []),
                    field_name="expected_retrieval_terms",
                ),
                expected_answer_terms=parse_term_groups(
                    raw_case.get("expected_answer_terms", []),
                    field_name="expected_answer_terms",
                ),
            )
        )

    return threshold, limit, cases


def load_tuning_candidates(path: Path) -> tuple[tuple[float, ...], tuple[int, ...]]:
    """读取并校验要比较的相似度阈值和 Top-K 候选值。

    候选参数与问题放在同一个 JSON 中，方便代码评审时同时看到“用什么题评估”
    和“比较哪些参数”。排序和去重在这里统一完成，后续输出表格保持稳定。
    """

    with path.open(encoding="utf-8") as cases_file:
        payload = json.load(cases_file)

    tuning = payload.get("tuning")
    if not isinstance(tuning, dict):
        raise ValueError("tuning must be an object")

    raw_thresholds = tuning.get("thresholds")
    raw_limits = tuning.get("limits")
    if not isinstance(raw_thresholds, list) or not raw_thresholds:
        raise ValueError("tuning.thresholds must be a non-empty list")
    if not isinstance(raw_limits, list) or not raw_limits:
        raise ValueError("tuning.limits must be a non-empty list")

    thresholds = tuple(sorted({float(value) for value in raw_thresholds}))
    limits = tuple(sorted({int(value) for value in raw_limits}))
    if any(not 0 <= value <= 1 for value in thresholds):
        raise ValueError("each tuning threshold must be between 0 and 1")
    if any(not 1 <= value <= 10 for value in limits):
        raise ValueError("each tuning limit must be between 1 and 10")

    return thresholds, limits


def find_missing_term_groups(
    text: str,
    term_groups: tuple[tuple[str, ...], ...],
) -> list[tuple[str, ...]]:
    """返回文本中完全没有命中的关键词组，空列表表示全部满足。"""

    normalized_text = text.casefold()
    return [
        group
        for group in term_groups
        if not any(term.casefold() in normalized_text for term in group)
    ]


def format_missing_groups(groups: list[tuple[str, ...]]) -> str:
    """把未命中组转换成适合终端阅读的 ``词A／词B`` 形式。"""

    return "，".join("／".join(group) for group in groups)


def evaluate_search_response(
    case: EvaluationCase,
    response: dict[str, Any],
    *,
    threshold: float,
) -> EvaluationCheck:
    """检查检索结果是否支持当前问题或正确落在拒答阈值以下。"""

    results = response.get("results")
    if not isinstance(results, list):
        return EvaluationCheck(False, "响应缺少 results 数组")

    relevant_results = [
        result
        for result in results
        if isinstance(result, dict)
        and float(result.get("similarity", -1)) >= threshold
    ]
    top_similarity = max(
        (
            float(result.get("similarity", -1))
            for result in results
            if isinstance(result, dict)
        ),
        default=-1,
    )

    if case.expected_refusal:
        passed = not relevant_results
        detail = (
            f"最高相似度 {top_similarity:.4f}，阈值 {threshold:.4f}，"
            f"高于阈值切片 {len(relevant_results)} 个"
        )
        return EvaluationCheck(passed, detail)

    combined_content = "\n".join(
        str(result.get("content", "")) for result in relevant_results
    )
    missing_groups = find_missing_term_groups(
        combined_content,
        case.expected_retrieval_terms,
    )
    passed = bool(relevant_results) and not missing_groups
    detail = (
        f"最高相似度 {top_similarity:.4f}，高于阈值切片 {len(relevant_results)} 个"
    )
    if missing_groups:
        detail += f"，缺少关键词组：{format_missing_groups(missing_groups)}"
    return EvaluationCheck(passed, detail)


def evaluate_tuning_grid(
    cases: list[EvaluationCase],
    search_responses: dict[str, dict[str, Any]],
    *,
    thresholds: tuple[float, ...],
    limits: tuple[int, ...],
) -> list[TuningResult]:
    """复用同一批检索结果，计算每组阈值和 Top-K 的离线表现。

    参数：
        cases：包含正向问题和预期拒答问题的完整评估集。
        search_responses：按样例 ID 保存的 ``POST /search`` 原始响应。
        thresholds：要模拟的相似度阈值。
        limits：要模拟的 Top-K，也就是只保留前几个召回切片。

    返回值：
        按阈值、Top-K 顺序排列的结果。正向问题失败记为误拒答，预期拒答问题
        失败记为错误放行，便于区分“找不到资料”和“把无关资料交给模型”。
    """

    tuning_results: list[TuningResult] = []
    for threshold in thresholds:
        for limit in limits:
            passed = 0
            false_rejections = 0
            false_acceptances = 0

            for case in cases:
                if case.case_id not in search_responses:
                    raise ValueError(f"missing search response for case {case.case_id}")

                response = search_responses[case.case_id]
                raw_results = response.get("results")
                if not isinstance(raw_results, list):
                    raise ValueError(
                        f"case {case.case_id} response must contain results"
                    )

                check = evaluate_search_response(
                    case,
                    {"results": raw_results[:limit]},
                    threshold=threshold,
                )
                if check.passed:
                    passed += 1
                elif case.expected_refusal:
                    false_acceptances += 1
                else:
                    false_rejections += 1

            tuning_results.append(
                TuningResult(
                    threshold=threshold,
                    limit=limit,
                    passed=passed,
                    total=len(cases),
                    false_rejections=false_rejections,
                    false_acceptances=false_acceptances,
                )
            )

    return tuning_results


def select_recommended_tuning_result(
    results: list[TuningResult],
    *,
    baseline_threshold: float,
    baseline_limit: int,
) -> TuningResult:
    """从扫描结果中选择风险较低且无需无意义改参的推荐组合。

    排序依次考虑：通过样例数量越多越好；错误放行越少越好；与当前阈值、Top-K
    的距离越小越好；最后在完全相同时选择较小 Top-K，减少模型上下文和费用。
    这个推荐只用于生成调试结论，不会自动修改问答服务常量。
    """

    if not results:
        raise ValueError("tuning results must not be empty")

    return max(
        results,
        key=lambda result: (
            result.passed,
            -result.false_acceptances,
            -abs(result.threshold - baseline_threshold),
            -abs(result.limit - baseline_limit),
            -result.limit,
        ),
    )


def evaluate_answer_response(
    case: EvaluationCase,
    response: dict[str, Any],
) -> EvaluationCheck:
    """检查回答关键词与引用数量是否符合有依据回答或拒答预期。"""

    answer = response.get("answer")
    sources = response.get("sources")
    if not isinstance(answer, str) or not isinstance(sources, list):
        return EvaluationCheck(False, "响应缺少 answer 字符串或 sources 数组")

    missing_groups = find_missing_term_groups(answer, case.expected_answer_terms)
    source_rule_passed = not sources if case.expected_refusal else bool(sources)
    passed = source_rule_passed and not missing_groups
    detail = f"引用 {len(sources)} 个"
    if not source_rule_passed:
        expected_text = "0 个" if case.expected_refusal else "至少 1 个"
        detail += f"，期望 {expected_text}"
    if missing_groups:
        detail += f"，答案缺少关键词组：{format_missing_groups(missing_groups)}"
    return EvaluationCheck(passed, detail)


def post_json(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    """使用标准库发送 JSON POST 请求，并返回解析后的 JSON 对象。

    urllib 来自 Python 标准库，因此评估工具不需要为几次本地 HTTP 请求引入
    requests 或 httpx。HTTP 错误会带上响应正文，方便定位后端校验或运行问题。
    """

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"无法连接后端：{exc.reason}") from exc
    except OSError as exc:
        raise RuntimeError(f"请求后端失败：{exc}") from exc

    if not isinstance(response_payload, dict):
        raise RuntimeError("后端响应不是 JSON 对象")
    return response_payload


def print_check(label: str, check: EvaluationCheck) -> None:
    """用固定格式输出单项结果，便于人工查看或复制到验证记录。"""

    status = "PASS" if check.passed else "FAIL"
    print(f"  {label}: {status}｜{check.detail}")


def run_tuning(
    *,
    base_url: str,
    cases_path: Path,
    timeout: float,
    baseline_threshold: float,
    baseline_limit: int,
    cases: list[EvaluationCase],
) -> int:
    """请求每个问题的最大 Top-K，并离线比较所有候选参数组合。"""

    thresholds, limits = load_tuning_candidates(cases_path)
    maximum_limit = max(limits)
    normalized_base_url = base_url.rstrip("/")
    search_responses: dict[str, dict[str, Any]] = {}

    print(
        f"评估集：{cases_path}\n"
        f"模式：tune｜样例：{len(cases)}｜"
        f"阈值候选：{len(thresholds)}｜Top-K 候选：{len(limits)}"
    )
    print(f"每个问题只请求一次 Top-{maximum_limit}，其余组合在本地计算。")

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] 检索 {case.case_id}｜{case.question}")
        try:
            search_responses[case.case_id] = post_json(
                f"{normalized_base_url}/search",
                {"query": case.question, "limit": maximum_limit},
                timeout=timeout,
            )
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            print(f"  FAIL｜{exc}")
            return 1

    results = evaluate_tuning_grid(
        cases,
        search_responses,
        thresholds=thresholds,
        limits=limits,
    )
    recommendation = select_recommended_tuning_result(
        results,
        baseline_threshold=baseline_threshold,
        baseline_limit=baseline_limit,
    )

    print("\n阈值    Top-K  通过率   误拒答  错误放行")
    for result in results:
        print(
            f"{result.threshold:<7.2f} "
            f"{result.limit:<6} "
            f"{result.passed}/{result.total} "
            f"({result.accuracy:>4.0%})   "
            f"{result.false_rejections:<7} "
            f"{result.false_acceptances}"
        )

    print(
        "\n推荐组合："
        f"阈值 {recommendation.threshold:.2f}，Top-K {recommendation.limit}｜"
        f"通过率 {recommendation.passed}/{recommendation.total} "
        f"({recommendation.accuracy:.0%})｜"
        f"误拒答 {recommendation.false_rejections}｜"
        f"错误放行 {recommendation.false_acceptances}"
    )
    print("说明：该结果只提供调试依据，不会自动修改当前问答参数。")
    return 0


def run_evaluation(
    *,
    base_url: str,
    cases_path: Path,
    mode: str,
    timeout: float,
) -> int:
    """依次执行评估样例，并以进程退出码表达整体是否通过。"""

    threshold, limit, cases = load_evaluation_cases(cases_path)
    normalized_base_url = base_url.rstrip("/")
    search_passed = 0
    answer_passed = 0

    if mode == "tune":
        return run_tuning(
            base_url=base_url,
            cases_path=cases_path,
            timeout=timeout,
            baseline_threshold=threshold,
            baseline_limit=limit,
            cases=cases,
        )

    print(
        f"评估集：{cases_path}\n"
        f"模式：{mode}｜样例：{len(cases)}｜阈值：{threshold:.4f}｜limit：{limit}"
    )

    for index, case in enumerate(cases, start=1):
        print(f"\n[{index}/{len(cases)}] {case.case_id}｜{case.question}")
        payload = {"query": case.question, "limit": limit}

        try:
            search_response = post_json(
                f"{normalized_base_url}/search",
                payload,
                timeout=timeout,
            )
            search_check = evaluate_search_response(
                case,
                search_response,
                threshold=threshold,
            )
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            search_check = EvaluationCheck(False, str(exc))

        print_check("检索", search_check)
        search_passed += int(search_check.passed)

        if mode == "full":
            try:
                answer_response = post_json(
                    f"{normalized_base_url}/answer",
                    payload,
                    timeout=timeout,
                )
                answer_check = evaluate_answer_response(case, answer_response)
            except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
                answer_check = EvaluationCheck(False, str(exc))

            print_check("回答", answer_check)
            answer_passed += int(answer_check.passed)

    search_total = len(cases)
    checks_passed = search_passed
    checks_total = search_total
    print(f"\n检索通过率：{search_passed}/{search_total}（{search_passed / search_total:.0%}）")

    if mode == "full":
        answer_total = len(cases)
        checks_passed += answer_passed
        checks_total += answer_total
        print(
            f"回答通过率：{answer_passed}/{answer_total}"
            f"（{answer_passed / answer_total:.0%}）"
        )

    print(f"整体通过率：{checks_passed}/{checks_total}（{checks_passed / checks_total:.0%}）")
    return 0 if checks_passed == checks_total else 1


def build_argument_parser() -> argparse.ArgumentParser:
    """声明命令行参数；mode 必填，避免误触真实聊天模型费用。"""

    parser = argparse.ArgumentParser(description="运行简单 RAG 评估集")
    parser.add_argument(
        "--mode",
        required=True,
        choices=("search", "full", "tune"),
        help=(
            "search 只评估当前检索；full 同时评估回答；"
            "tune 比较多组阈值和 Top-K"
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="已经启动的 FastAPI 服务地址",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help="评估集 JSON 路径",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60,
        help="每个 HTTP 请求的超时秒数",
    )
    return parser


def main() -> int:
    """解析参数并运行评估；配置错误会返回非零退出码。"""

    arguments = build_argument_parser().parse_args()
    try:
        return run_evaluation(
            base_url=arguments.base_url,
            cases_path=arguments.cases,
            mode=arguments.mode,
            timeout=arguments.timeout,
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"评估配置错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
