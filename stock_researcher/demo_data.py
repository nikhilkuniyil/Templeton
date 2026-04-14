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
                        },
                    )
                ],
            }
        ),
        market_data=StaticMarketDataClient(
            {
                "ASML": [_doc("ASML price history", "market_data", "ASML")],
                "NVDA": [_doc("NVDA price history", "market_data", "NVDA")],
            }
        ),
        news=StaticNewsClient(
            {
                "ASML": [_doc("ASML sector news", "news", "ASML")],
                "NVDA": [_doc("NVDA AI infrastructure news", "news", "NVDA")],
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
