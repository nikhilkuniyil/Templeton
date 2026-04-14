from stock_researcher.benchmarks import BenchmarkHarness
from stock_researcher.run_store import LocalRunStore


def test_benchmark_harness_runs_demo_suite(tmp_path) -> None:
    harness = BenchmarkHarness(run_store=LocalRunStore(tmp_path))

    result = harness.run_suite()

    assert result.suite_name == "templeton_demo_baseline"
    assert result.cases_run == 2
    assert result.passed_cases == 2
    assert result.average_score == 1.0
    assert all(case.passed for case in result.case_results)
