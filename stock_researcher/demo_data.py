"""Demo connector data for local CLI usage."""

from __future__ import annotations

from .connectors import (
    ConnectorBundle,
    StaticFilingsClient,
    StaticMarketDataClient,
    StaticNewsClient,
)
from .models import SourceDocument


def demo_connector_bundle() -> ConnectorBundle:
    return ConnectorBundle(
        filings=StaticFilingsClient(
            {
                "ASML": [
                    _doc(
                        name="ASML annual report",
                        source_type="company_filing_or_release",
                        ticker="ASML",
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
                "ASML": [_doc("ASML price history", "market_data", "ASML", metadata={
                    "valuation_methods": ["historical_multiples", "peer_comparison"],
                    "current_valuation": {"pe": 34.5, "ev_ebitda": 24.1, "fcf_yield": 0.025},
                    "scenario_ranges": {
                        "bear": {"fair_value": 780, "upside_downside_percent": -18},
                        "base": {"fair_value": 910, "upside_downside_percent": -4},
                        "bull": {"fair_value": 1080, "upside_downside_percent": 14}
                    },
                    "market_implied_expectations": ["Sustained high-margin growth"]
                })],
                "NVDA": [_doc("NVDA price history", "market_data", "NVDA", metadata={
                    "valuation_methods": ["historical_multiples", "scenario_analysis"],
                    "current_valuation": {"pe": 38.0, "ev_ebitda": 28.0, "fcf_yield": 0.021},
                    "scenario_ranges": {
                        "bear": {"fair_value": 920, "upside_downside_percent": -20},
                        "base": {"fair_value": 1120, "upside_downside_percent": -6},
                        "bull": {"fair_value": 1310, "upside_downside_percent": 10}
                    },
                    "market_implied_expectations": ["Very high sustained AI infrastructure demand"]
                })],
            }
        ),
        news=StaticNewsClient(
            {
                "ASML": [_doc("ASML sector news", "news", "ASML", metadata={
                    "positive_catalysts": ["AI-driven foundry investment", "Healthy service demand"],
                    "negative_catalysts": ["Export restriction risk"],
                    "event_type": "sector_news",
                    "expected_impact": "medium"
                })],
                "NVDA": [_doc("NVDA AI infrastructure news", "news", "NVDA", metadata={
                    "positive_catalysts": ["Large hyperscaler capex plans", "Strong AI platform adoption"],
                    "negative_catalysts": ["Export controls", "Competition at the margin"],
                    "event_type": "sector_news",
                    "expected_impact": "high"
                })],
            }
        ),
    )


def _doc(name: str, source_type: str, ticker: str, metadata: dict | None = None) -> SourceDocument:
    return SourceDocument(
        source_name=name,
        source_type=source_type,
        source_url=f"https://example.com/{ticker.lower()}/{name.lower().replace(' ', '-')}",
        published_at="2026-04-10T00:00:00Z",
        retrieved_at="2026-04-14T09:00:00-07:00",
        ticker=ticker,
        metadata=metadata or {},
    )
