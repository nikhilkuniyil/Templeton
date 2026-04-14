"""Benchmark harness for repeatable Templeton quality checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .agents import AgentRuntime
from .demo_data import demo_connector_bundle
from .models import AgentEnvelope, ResearchRequest
from .orchestrator import InvestigationOrchestrator, InvestigationRun
from .run_store import LocalRunStore

BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "benchmarks"


@dataclass(slots=True)
class BenchmarkCase:
    case_id: str
    ticker: str
    query: str
    time_horizon: str
    objective: str
    mode: str
    expected: dict[str, object]


@dataclass(slots=True)
class BenchmarkCaseResult:
    case_id: str
    ticker: str
    passed: bool
    score: float
    passed_checks: int
    total_checks: int
    failures: list[str]
    request_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "ticker": self.ticker,
            "passed": self.passed,
            "score": self.score,
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "failures": self.failures,
            "request_id": self.request_id,
        }


@dataclass(slots=True)
class BenchmarkSuiteResult:
    suite_name: str
    cases_run: int
    passed_cases: int
    average_score: float
    case_results: list[BenchmarkCaseResult]

    def to_dict(self) -> dict[str, object]:
        return {
            "suite_name": self.suite_name,
            "cases_run": self.cases_run,
            "passed_cases": self.passed_cases,
            "average_score": self.average_score,
            "case_results": [item.to_dict() for item in self.case_results],
        }


class BenchmarkHarness:
    """Runs fixed benchmark cases against the current Templeton implementation."""

    def __init__(
        self,
        run_store: LocalRunStore | None = None,
        runtime: AgentRuntime | None = None,
    ) -> None:
        self.run_store = run_store
        self.runtime = runtime or AgentRuntime()

    def run_suite(self, suite_path: str | Path | None = None) -> BenchmarkSuiteResult:
        suite = self._load_suite(suite_path)
        case_results: list[BenchmarkCaseResult] = []
        for case in suite["cases"]:
            benchmark_case = BenchmarkCase(**case)
            case_results.append(self.run_case(benchmark_case))
        cases_run = len(case_results)
        passed_cases = sum(1 for result in case_results if result.passed)
        average_score = (
            round(sum(result.score for result in case_results) / cases_run, 3)
            if cases_run
            else 0.0
        )
        return BenchmarkSuiteResult(
            suite_name=str(suite["suite_name"]),
            cases_run=cases_run,
            passed_cases=passed_cases,
            average_score=average_score,
            case_results=case_results,
        )

    def run_case(self, case: BenchmarkCase) -> BenchmarkCaseResult:
        request = ResearchRequest(
            request_id=f"bench_{case.case_id}_{uuid4().hex[:8]}",
            user_query=case.query,
            mode="investigation",
            tickers=[case.ticker],
            time_horizon=case.time_horizon,
            objective=case.objective,
        )
        orchestrator = InvestigationOrchestrator(
            connectors=demo_connector_bundle(),
            run_store=self.run_store,
        )
        run = orchestrator.run(request, agent_executor=self.runtime.execute)
        return self._score_case(case, run)

    def _score_case(
        self,
        case: BenchmarkCase,
        run: InvestigationRun,
    ) -> BenchmarkCaseResult:
        failures: list[str] = []
        checks = 0
        passed = 0

        def check(condition: bool, failure: str) -> None:
            nonlocal checks, passed
            checks += 1
            if condition:
                passed += 1
            else:
                failures.append(failure)

        decision = run.outputs["decision_portfolio_fit"].payload
        source_verification = run.outputs["source_verification"].payload
        business_quality = run.outputs["business_quality"].payload
        valuation = run.outputs["valuation"].payload
        technical = run.outputs["technical_analysis"].payload
        risk = run.outputs["risk"].payload
        evidence_ids = run.outputs["source_verification"].evidence_ids

        expected = case.expected
        check(
            decision.get("decision") == expected["decision"],
            f"decision mismatch: expected {expected['decision']}, got {decision.get('decision')}",
        )
        check(
            source_verification.get("freshness_status") == expected["freshness_status"],
            "freshness status mismatch",
        )

        business_model = str(business_quality.get("business_model", "")).lower()
        for term in expected.get("business_model_contains", []):
            check(term.lower() in business_model, f"business model missing term: {term}")

        risk_blob = json.dumps(risk.get("core_risks", [])).lower()
        for term in expected.get("risk_contains", []):
            check(term.lower() in risk_blob, f"risk output missing term: {term}")

        check(
            valuation.get("valuation_label") == expected["valuation_label"],
            "valuation label mismatch",
        )
        check(
            technical.get("entry_quality") == expected["technical_entry_quality"],
            "technical entry quality mismatch",
        )
        check(
            len(evidence_ids) >= int(expected["minimum_evidence_ids"]),
            "not enough evidence ids produced",
        )

        score = round(passed / checks, 3) if checks else 0.0
        return BenchmarkCaseResult(
            case_id=case.case_id,
            ticker=case.ticker,
            passed=(passed == checks),
            score=score,
            passed_checks=passed,
            total_checks=checks,
            failures=failures,
            request_id=run.request.request_id,
        )

    def _load_suite(self, suite_path: str | Path | None) -> dict[str, object]:
        path = Path(suite_path) if suite_path is not None else BENCHMARK_DIR / "templeton_cases.json"
        return json.loads(path.read_text(encoding="utf-8"))


def format_suite_result(result: BenchmarkSuiteResult) -> str:
    lines = [
        f"Benchmark suite: {result.suite_name}",
        f"Cases passed: {result.passed_cases}/{result.cases_run}",
        f"Average score: {result.average_score:.3f}",
    ]
    for case in result.case_results:
        status = "PASS" if case.passed else "FAIL"
        lines.append(
            f"- {case.case_id} [{status}] score={case.score:.3f} checks={case.passed_checks}/{case.total_checks}"
        )
        for failure in case.failures:
            lines.append(f"  failure: {failure}")
    return "\n".join(lines)
