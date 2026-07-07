"""Demo connector data for local CLI usage."""

from __future__ import annotations

from datetime import datetime, timedelta

from .connectors import (
    ConnectorBundle,
    StaticFilingsClient,
    StaticMarketDataClient,
    StaticNewsClient,
)
from .models import SourceDocument


def _demo_timestamps() -> tuple[str, str]:
    retrieved_at = datetime.now().astimezone()
    published_at = retrieved_at - timedelta(days=3)
    return published_at.isoformat(), retrieved_at.isoformat()


def demo_connector_bundle() -> ConnectorBundle:
    published_at, retrieved_at = _demo_timestamps()
    return ConnectorBundle(
        filings=StaticFilingsClient(
            {
                "ASML": [
                    _doc(
                        name="ASML annual report",
                        source_type="company_filing_or_release",
                        ticker="ASML",
                        published_at=published_at,
                        retrieved_at=retrieved_at,
                        metadata={
                            "business_model": "Sells advanced lithography systems, upgrades, and services to semiconductor manufacturers.",
                            "revenue_drivers": ["EUV demand", "Installed base services"],
                            "competitive_advantages": ["Technological leadership", "High switching costs"],
                            "vulnerabilities": ["Semiconductor capex cyclicality"],
                            "growth_profile": {
                                "revenue_growth_trend": "positive",
                                "earnings_growth_trend": "positive"
                            },
                            "margin_profile": {
                                "gross_margin_trend": "stable_to_up",
                                "operating_margin_trend": "stable"
                            },
                            "cash_flow_profile": {
                                "free_cash_flow_quality": "strong",
                                "cash_conversion": "healthy"
                            },
                            "balance_sheet_profile": {
                                "debt_risk": "low",
                                "liquidity": "strong"
                            },
                            "capital_allocation": {
                                "dilution_risk": "low",
                                "buyback_profile": "moderate"
                            },
                            "core_risks": [
                                {"risk": "Semiconductor capex slowdown", "severity": "high", "likelihood": "medium"}
                            ],
                            "thesis_breakers": ["Meaningful reduction in order growth"],
                            "monitoring_indicators": ["Order growth", "Gross margin trend"],
                        },
                    )
                ],
                "NVDA": [
                    _doc(
                        name="NVIDIA annual report",
                        source_type="company_filing_or_release",
                        ticker="NVDA",
                        published_at=published_at,
                        retrieved_at=retrieved_at,
                        metadata={
                            "business_model": "Designs accelerated computing platforms spanning GPUs, networking, and software.",
                            "revenue_drivers": ["Data center GPU demand", "AI infrastructure spending"],
                            "competitive_advantages": ["Software ecosystem", "Scale advantages"],
                            "vulnerabilities": ["Customer concentration", "Premium valuation sensitivity"],
                            "growth_profile": {
                                "revenue_growth_trend": "strong",
                                "earnings_growth_trend": "strong"
                            },
                            "margin_profile": {
                                "gross_margin_trend": "up",
                                "operating_margin_trend": "up"
                            },
                            "cash_flow_profile": {
                                "free_cash_flow_quality": "strong",
                                "cash_conversion": "healthy"
                            },
                            "balance_sheet_profile": {
                                "debt_risk": "low",
                                "liquidity": "strong"
                            },
                            "capital_allocation": {
                                "dilution_risk": "low",
                                "buyback_profile": "moderate"
                            },
                            "core_risks": [
                                {"risk": "Demand normalization after rapid AI buildout", "severity": "high", "likelihood": "medium"}
                            ],
                            "thesis_breakers": ["Data-center growth deceleration"],
                            "monitoring_indicators": ["Data center revenue growth", "Gross margin trend"],
                        },
                    )
                ],
            }
        ),
        market_data=StaticMarketDataClient(
            {
                "ASML": [
                    _doc(
                        "ASML price history",
                        "market_data",
                        "ASML",
                        published_at=published_at,
                        retrieved_at=retrieved_at,
                        metadata={
                            "valuation_methods": ["historical_multiples", "peer_comparison"],
                            "current_valuation": {
                                "pe": 34.5,
                                "ev_ebitda": 24.1,
                                "fcf_yield": 0.025,
                            },
                            "scenario_ranges": {
                                "bear": {"fair_value": 780, "upside_downside_percent": -18},
                                "base": {"fair_value": 910, "upside_downside_percent": -4},
                                "bull": {"fair_value": 1080, "upside_downside_percent": 14}
                            },
                            "market_implied_expectations": ["Sustained high-margin growth"],
                            "monthly_returns": [
                                0.035,
                                -0.018,
                                0.042,
                                0.012,
                                -0.025,
                                0.031,
                                0.018,
                                0.026,
                                -0.011,
                                0.021,
                                0.014,
                                0.028,
                            ],
                            "technical_analysis": {
                                "trend": "uptrend",
                                "momentum": "positive",
                                "key_levels": {"support": [860, 825], "resistance": [950, 980]},
                                "entry_quality": "neutral",
                                "risk_management_note": "Prefer adding on pullbacks toward support rather than chasing strength.",
                            },
                        },
                    )
                ],
                "NVDA": [
                    _doc(
                        "NVDA price history",
                        "market_data",
                        "NVDA",
                        published_at=published_at,
                        retrieved_at=retrieved_at,
                        metadata={
                            "valuation_methods": ["historical_multiples", "scenario_analysis"],
                            "current_valuation": {
                                "pe": 38.0,
                                "ev_ebitda": 28.0,
                                "fcf_yield": 0.021,
                            },
                            "scenario_ranges": {
                                "bear": {"fair_value": 920, "upside_downside_percent": -20},
                                "base": {"fair_value": 1120, "upside_downside_percent": -6},
                                "bull": {"fair_value": 1310, "upside_downside_percent": 10}
                            },
                            "market_implied_expectations": ["Very high sustained AI infrastructure demand"],
                            "monthly_returns": [
                                0.061,
                                -0.044,
                                0.083,
                                0.028,
                                -0.067,
                                0.052,
                                0.039,
                                0.047,
                                -0.031,
                                0.036,
                                0.022,
                                0.055,
                            ],
                            "technical_analysis": {
                                "trend": "uptrend",
                                "momentum": "positive",
                                "key_levels": {"support": [1100, 1040], "resistance": [1240, 1300]},
                                "entry_quality": "extended",
                                "risk_management_note": "Price is extended above short-term support; avoid chasing strength.",
                            },
                        },
                    )
                ],
            }
        ),
        news=StaticNewsClient(
            {
                "ASML": [
                    _doc(
                        "ASML sector news",
                        "news",
                        "ASML",
                        published_at=published_at,
                        retrieved_at=retrieved_at,
                        metadata={
                            "positive_catalysts": [
                                "AI-driven foundry investment",
                                "Healthy service demand",
                            ],
                            "negative_catalysts": ["Export restriction risk"],
                            "event_type": "sector_news",
                            "expected_impact": "medium"
                        },
                    )
                ],
                "NVDA": [
                    _doc(
                        "NVDA AI infrastructure news",
                        "news",
                        "NVDA",
                        published_at=published_at,
                        retrieved_at=retrieved_at,
                        metadata={
                            "positive_catalysts": [
                                "Large hyperscaler capex plans",
                                "Strong AI platform adoption",
                            ],
                            "negative_catalysts": ["Export controls", "Competition at the margin"],
                            "event_type": "sector_news",
                            "expected_impact": "high"
                        },
                    )
                ],
            }
        ),
    )


def _doc(
    name: str,
    source_type: str,
    ticker: str,
    metadata: dict | None = None,
    published_at: str | None = None,
    retrieved_at: str | None = None,
) -> SourceDocument:
    default_published_at, default_retrieved_at = _demo_timestamps()
    return SourceDocument(
        source_name=name,
        source_type=source_type,
        source_url=f"https://example.com/{ticker.lower()}/{name.lower().replace(' ', '-')}",
        published_at=published_at or default_published_at,
        retrieved_at=retrieved_at or default_retrieved_at,
        ticker=ticker,
        metadata=metadata or {},
    )
