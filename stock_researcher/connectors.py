"""Connector interfaces and simple in-memory implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import SourceDocument, SourcePacket


class FilingsClient(Protocol):
    def get_company_filings(self, ticker: str) -> list[SourceDocument]:
        """Return filing-like primary source documents for a ticker."""


class MarketDataClient(Protocol):
    def get_market_documents(self, ticker: str) -> list[SourceDocument]:
        """Return market-data source documents for a ticker."""


class NewsClient(Protocol):
    def get_recent_news(self, ticker: str) -> list[SourceDocument]:
        """Return recent thesis-relevant news documents for a ticker."""


@dataclass(slots=True)
class ConnectorBundle:
    filings: FilingsClient
    market_data: MarketDataClient
    news: NewsClient

    def build_source_packet(self, ticker: str) -> SourcePacket:
        return SourcePacket(
            ticker=ticker,
            filings=self.filings.get_company_filings(ticker),
            market_data=self.market_data.get_market_documents(ticker),
            news=self.news.get_recent_news(ticker),
        )


@dataclass(slots=True)
class StaticFilingsClient:
    documents_by_ticker: dict[str, list[SourceDocument]] = field(default_factory=dict)

    def get_company_filings(self, ticker: str) -> list[SourceDocument]:
        return list(self.documents_by_ticker.get(ticker, []))


@dataclass(slots=True)
class StaticMarketDataClient:
    documents_by_ticker: dict[str, list[SourceDocument]] = field(default_factory=dict)

    def get_market_documents(self, ticker: str) -> list[SourceDocument]:
        return list(self.documents_by_ticker.get(ticker, []))


@dataclass(slots=True)
class StaticNewsClient:
    documents_by_ticker: dict[str, list[SourceDocument]] = field(default_factory=dict)

    def get_recent_news(self, ticker: str) -> list[SourceDocument]:
        return list(self.documents_by_ticker.get(ticker, []))
