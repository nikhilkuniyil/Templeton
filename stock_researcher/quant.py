"""Small factor-ranking and backtest helpers for research outputs."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .models import AgentEnvelope, SourcePacket


@dataclass(slots=True)
class FactorScore:
    ticker: str
    total_score: float
    quality: float
    value: float
    momentum: float
    risk: float
    catalyst: float
    decision: str
    confidence: str
    evidence_freshness: str
    valuation_label: str
    entry_quality: str
    notes: list[str]
    monthly_returns: list[float]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class RankResult:
    rows: list[FactorScore]

    def to_dict(self) -> dict:
        return {"rows": [row.to_dict() for row in self.rows]}


@dataclass(slots=True)
class BacktestResult:
    strategy: str
    tickers: list[str]
    periods: int
    cumulative_return: float
    annualized_return: float
    volatility: float
    sharpe: float
    max_drawdown: float
    hit_rate: float
    average_monthly_return: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class SignalResult:
    ticker: str
    signal: str
    setup_score: float
    research_decision: str
    confidence: str
    sizing: str
    suggested_action: str
    reasons: list[str]
    invalidation_triggers: list[str]
    diagnostics: dict[str, float | str | int]

    def to_dict(self) -> dict:
        return asdict(self)


def score_research(
    ticker: str,
    outputs: dict[str, AgentEnvelope],
    source_packet: SourcePacket | None = None,
) -> FactorScore:
    financial = _payload(outputs, "financial_quality")
    valuation = _payload(outputs, "valuation")
    technical = _payload(outputs, "technical_analysis")
    risk_payload = _payload(outputs, "risk")
    catalyst_payload = _payload(outputs, "news_catalyst")
    decision_payload = _payload(outputs, "decision_portfolio_fit")
    source_payload = _payload(outputs, "source_verification")

    quality = _quality_score(financial)
    value = _value_score(valuation)
    momentum = _momentum_score(technical)
    risk = _risk_score(risk_payload, source_payload)
    catalyst = _catalyst_score(catalyst_payload)
    total = round(
        quality * 0.30
        + value * 0.20
        + momentum * 0.20
        + risk * 0.20
        + catalyst * 0.10,
        1,
    )
    decision = str(decision_payload.get("decision", "unknown")).upper()
    confidence = str(decision_payload.get("confidence", "unknown")).upper()
    freshness = str(source_payload.get("freshness_status", "unknown"))
    valuation_label = str(valuation.get("valuation_label", "unknown"))
    entry_quality = str(technical.get("entry_quality", "unknown"))

    return FactorScore(
        ticker=ticker,
        total_score=total,
        quality=quality,
        value=value,
        momentum=momentum,
        risk=risk,
        catalyst=catalyst,
        decision=decision,
        confidence=confidence,
        evidence_freshness=freshness,
        valuation_label=valuation_label,
        entry_quality=entry_quality,
        notes=_score_notes(financial, valuation, technical, risk_payload, catalyst_payload),
        monthly_returns=_monthly_returns(source_packet),
    )


def rank_scores(scores: list[FactorScore]) -> RankResult:
    return RankResult(rows=sorted(scores, key=lambda row: row.total_score, reverse=True))


def backtest_top_ranked(rank_result: RankResult, top_n: int = 5) -> BacktestResult:
    selected = rank_result.rows[: max(1, top_n)]
    if not selected:
        return _empty_backtest()

    series = [row.monthly_returns for row in selected if row.monthly_returns]
    if not series:
        return _empty_backtest(tickers=[row.ticker for row in selected])

    periods = min(len(item) for item in series)
    if periods <= 0:
        return _empty_backtest(tickers=[row.ticker for row in selected])

    portfolio_returns = [
        sum(item[index] for item in series) / len(series)
        for index in range(periods)
    ]
    cumulative = _compound(portfolio_returns)
    avg = sum(portfolio_returns) / periods
    vol = _stdev(portfolio_returns) * math.sqrt(12)
    annualized = (1 + cumulative) ** (12 / periods) - 1
    sharpe = annualized / vol if vol else 0.0
    positives = sum(1 for item in portfolio_returns if item > 0)

    return BacktestResult(
        strategy=f"top_{len(selected)}_factor_rank_equal_weight",
        tickers=[row.ticker for row in selected],
        periods=periods,
        cumulative_return=round(cumulative, 4),
        annualized_return=round(annualized, 4),
        volatility=round(vol, 4),
        sharpe=round(sharpe, 3),
        max_drawdown=round(_max_drawdown(portfolio_returns), 4),
        hit_rate=round(positives / periods, 3),
        average_monthly_return=round(avg, 4),
    )


def generate_signal(score: FactorScore) -> SignalResult:
    diagnostics = _return_diagnostics(score.monthly_returns)
    setup_score = _setup_score(score, diagnostics)
    signal = _signal_label(score, setup_score, diagnostics)
    return SignalResult(
        ticker=score.ticker,
        signal=signal,
        setup_score=setup_score,
        research_decision=score.decision,
        confidence=score.confidence,
        sizing=_sizing(signal, score, diagnostics),
        suggested_action=_suggested_action(signal),
        reasons=_signal_reasons(score, diagnostics),
        invalidation_triggers=_invalidation_triggers(score, diagnostics),
        diagnostics=diagnostics,
    )


def _payload(outputs: dict[str, AgentEnvelope], agent_name: str) -> dict:
    envelope = outputs.get(agent_name)
    return envelope.payload if envelope is not None else {}


def _quality_score(payload: dict) -> float:
    rating = str(payload.get("overall_quality_rating", "unknown"))
    return {"high": 90.0, "medium": 60.0, "low": 30.0}.get(rating, 45.0)


def _value_score(payload: dict) -> float:
    label = str(payload.get("valuation_label", "unknown"))
    return {
        "cheap": 90.0,
        "fair": 70.0,
        "fair_to_expensive": 45.0,
        "expensive": 25.0,
    }.get(label, 45.0)


def _momentum_score(payload: dict) -> float:
    score = 45.0
    score += {"uptrend": 25, "mixed": 5, "downtrend": -20}.get(str(payload.get("trend")), 0)
    score += {"positive": 20, "neutral": 5, "negative": -15}.get(str(payload.get("momentum")), 0)
    score += {"constructive": 10, "neutral": 0, "extended": -10}.get(str(payload.get("entry_quality")), 0)
    return _clamp(score)


def _risk_score(risk_payload: dict, source_payload: dict) -> float:
    risks = risk_payload.get("core_risks", [])
    score = 80.0 - min(len(risks), 6) * 6
    for item in risks if isinstance(risks, list) else []:
        if isinstance(item, dict) and item.get("severity") == "high":
            score -= 8
    freshness = source_payload.get("freshness_status")
    if freshness == "mixed":
        score -= 10
    elif freshness == "stale":
        score -= 25
    return _clamp(score)


def _catalyst_score(payload: dict) -> float:
    positives = payload.get("positive_catalysts", [])
    negatives = payload.get("negative_catalysts", [])
    score = 50 + len(positives if isinstance(positives, list) else []) * 12
    score -= len(negatives if isinstance(negatives, list) else []) * 10
    return _clamp(score)


def _score_notes(
    financial: dict,
    valuation: dict,
    technical: dict,
    risk_payload: dict,
    catalyst: dict,
) -> list[str]:
    return [
        f"quality={financial.get('overall_quality_rating', 'unknown')}",
        f"valuation={valuation.get('valuation_label', 'unknown')}",
        f"technical={technical.get('trend', 'unknown')}/{technical.get('momentum', 'unknown')}",
        f"risks={len(risk_payload.get('core_risks', []))}",
        (
            f"catalysts=+{len(catalyst.get('positive_catalysts', []))}"
            f"/-{len(catalyst.get('negative_catalysts', []))}"
        ),
    ]


def _monthly_returns(source_packet: SourcePacket | None) -> list[float]:
    if source_packet is None:
        return []
    for document in source_packet.market_data:
        raw = document.metadata.get("monthly_returns")
        if isinstance(raw, list):
            return [float(item) for item in raw if isinstance(item, (int, float))]
    return []


def _return_diagnostics(returns: list[float]) -> dict[str, float | str | int]:
    if not returns:
        return {
            "periods": 0,
            "trailing_3m_return": 0.0,
            "trailing_6m_return": 0.0,
            "volatility": 0.0,
            "max_drawdown": 0.0,
            "hit_rate": 0.0,
            "return_regime": "insufficient_data",
        }
    trailing_3m = _compound(returns[-3:]) if len(returns) >= 3 else _compound(returns)
    trailing_6m = _compound(returns[-6:]) if len(returns) >= 6 else _compound(returns)
    volatility = _stdev(returns) * math.sqrt(12)
    drawdown = _max_drawdown(returns)
    hit_rate = sum(1 for item in returns if item > 0) / len(returns)
    regime = "positive" if trailing_3m > 0 and trailing_6m > 0 else "mixed"
    if trailing_3m < -0.05 and trailing_6m < 0:
        regime = "negative"
    return {
        "periods": len(returns),
        "trailing_3m_return": round(trailing_3m, 4),
        "trailing_6m_return": round(trailing_6m, 4),
        "volatility": round(volatility, 4),
        "max_drawdown": round(drawdown, 4),
        "hit_rate": round(hit_rate, 3),
        "return_regime": regime,
    }


def _setup_score(score: FactorScore, diagnostics: dict[str, float | str | int]) -> float:
    return_regime_bonus = {"positive": 8, "mixed": 0, "negative": -10, "insufficient_data": -8}
    drawdown = float(diagnostics["max_drawdown"])
    drawdown_penalty = -8 if drawdown < -0.20 else -4 if drawdown < -0.12 else 0
    setup = (
        score.quality * 0.25
        + score.value * 0.20
        + score.momentum * 0.20
        + score.risk * 0.20
        + score.catalyst * 0.05
        + 50 * 0.10
        + return_regime_bonus.get(str(diagnostics["return_regime"]), 0)
        + drawdown_penalty
    )
    if score.evidence_freshness == "stale":
        setup -= 20
    elif score.evidence_freshness == "mixed":
        setup -= 8
    return _clamp(setup)


def _signal_label(
    score: FactorScore,
    setup_score: float,
    diagnostics: dict[str, float | str | int],
) -> str:
    if score.evidence_freshness == "stale" or int(diagnostics["periods"]) < 3:
        return "INSUFFICIENT_DATA"
    if score.risk < 50 or str(diagnostics["return_regime"]) == "negative":
        return "RISK_OFF"
    if score.entry_quality == "extended" and score.value < 55:
        return "AVOID_CHASING"
    if setup_score >= 75 and score.value >= 60 and score.risk >= 65 and score.momentum >= 65:
        return "BUY_ZONE"
    if score.quality >= 75 and score.momentum >= 65 and score.risk >= 60:
        return "WATCH_FOR_PULLBACK"
    return "INSUFFICIENT_DATA" if setup_score < 45 else "WATCH_FOR_PULLBACK"


def _sizing(
    signal: str,
    score: FactorScore,
    diagnostics: dict[str, float | str | int],
) -> str:
    volatility = float(diagnostics["volatility"])
    if signal in {"INSUFFICIENT_DATA", "RISK_OFF", "AVOID_CHASING"}:
        return "avoid new capital"
    if signal == "BUY_ZONE" and score.confidence == "HIGH" and volatility <= 0.30:
        return "research sizing: 4-6%"
    if signal == "BUY_ZONE":
        return "research sizing: 2-4%"
    return "starter/watchlist sizing: 1-2%"


def _suggested_action(signal: str) -> str:
    return {
        "BUY_ZONE": "candidate for staged entry if portfolio constraints allow",
        "WATCH_FOR_PULLBACK": "keep on watchlist; wait for better valuation or entry quality",
        "AVOID_CHASING": "avoid adding after extended strength; reassess on pullback",
        "RISK_OFF": "do not add; risk or return regime is unfavorable",
        "INSUFFICIENT_DATA": "refresh sources or add more price history before acting",
    }[signal]


def _signal_reasons(score: FactorScore, diagnostics: dict[str, float | str | int]) -> list[str]:
    return [
        f"research decision={score.decision}, confidence={score.confidence}",
        f"quality={score.quality:.1f}, value={score.value:.1f}, momentum={score.momentum:.1f}, risk={score.risk:.1f}",
        f"valuation={score.valuation_label}, entry_quality={score.entry_quality}",
        (
            f"trailing_3m={float(diagnostics['trailing_3m_return']):.2%}, "
            f"max_drawdown={float(diagnostics['max_drawdown']):.2%}, "
            f"volatility={float(diagnostics['volatility']):.2%}"
        ),
    ]


def _invalidation_triggers(
    score: FactorScore,
    diagnostics: dict[str, float | str | int],
) -> list[str]:
    triggers = [
        "evidence freshness becomes stale",
        "risk score falls below 50",
        "momentum score falls below 50",
    ]
    if score.value < 60:
        triggers.append("valuation fails to improve from current level")
    if score.entry_quality == "extended":
        triggers.append("price remains extended instead of resetting toward support")
    if float(diagnostics["max_drawdown"]) < -0.12:
        triggers.append("drawdown deepens without a research-backed catalyst")
    return triggers


def _compound(returns: list[float]) -> float:
    value = 1.0
    for item in returns:
        value *= 1 + item
    return value - 1


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((item - mean) ** 2 for item in values) / (len(values) - 1)
    return math.sqrt(variance)


def _max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    worst = 0.0
    for item in returns:
        equity *= 1 + item
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1)
    return worst


def _empty_backtest(tickers: list[str] | None = None) -> BacktestResult:
    return BacktestResult(
        strategy="top_rank_equal_weight",
        tickers=tickers or [],
        periods=0,
        cumulative_return=0.0,
        annualized_return=0.0,
        volatility=0.0,
        sharpe=0.0,
        max_drawdown=0.0,
        hit_rate=0.0,
        average_monthly_return=0.0,
    )


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)
