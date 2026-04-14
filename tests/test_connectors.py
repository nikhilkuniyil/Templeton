from urllib.error import HTTPError

import pytest

from stock_researcher.connectors import (
    SecCompanyFactsMarketDataClient,
    SecFilingsClient,
    YahooFinanceNewsClient,
)


def test_sec_filings_client_builds_recent_documents() -> None:
    def fake_fetch(url: str, headers: dict[str, str]) -> dict:
        if url.endswith("company_tickers.json"):
            return {
                "0": {"ticker": "ASML", "cik_str": 937966},
            }
        return {
            "name": "ASML HOLDING NV",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000937966-24-000001"],
                    "form": ["20-F"],
                    "filingDate": ["2026-02-01"],
                    "primaryDocument": ["asml-20260201x20f.htm"],
                }
            },
        }

    def fake_fetch_bytes(url: str, headers: dict[str, str]) -> bytes:
        return b"""
        <html><body>
        <h1>Item 4. Information on the Company</h1>
        <p>ASML designs and sells advanced lithography systems to semiconductor manufacturers worldwide.</p>
        <p>Our revenue is driven by EUV systems, deep ultraviolet systems, and service revenue from the installed base.</p>
        <p>We benefit from technology leadership and a large installed base that creates switching costs.</p>
        <h1>Risk Factors</h1>
        <p>Demand for our systems is cyclical and depends on semiconductor capital spending.</p>
        <p>Export regulation and trade restrictions could adversely affect our business.</p>
        </body></html>
        """

    client = SecFilingsClient(
        user_agent="TempletonTest/0.1",
        fetch_json=fake_fetch,
        fetch_bytes=fake_fetch_bytes,
    )
    docs = client.get_company_filings("ASML")

    assert len(docs) == 1
    assert docs[0].ticker == "ASML"
    assert docs[0].metadata["form"] == "20-F"
    assert "designs and sells advanced lithography systems" in docs[0].metadata["business_model"].lower()
    assert docs[0].metadata["event_type"] == "annual_report"
    assert docs[0].metadata["revenue_drivers"]
    assert docs[0].metadata["competitive_advantages"]
    assert docs[0].metadata["core_risks"]


def test_sec_filings_client_wraps_http_errors() -> None:
    def fake_fetch(url: str, headers: dict[str, str]) -> dict:
        raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

    client = SecFilingsClient(user_agent="TempletonTest/0.1", fetch_json=fake_fetch)

    with pytest.raises(RuntimeError):
        client.get_company_filings("ASML")


def test_sec_companyfacts_market_data_client_derives_financial_metadata() -> None:
    def fake_fetch(url: str, headers: dict[str, str]) -> dict:
        if "company_tickers.json" in url:
            return {"0": {"ticker": "NVDA", "cik_str": 1045810}}
        if "companyfacts" in url:
            return {
                "cik": 1045810,
                "entityName": "NVIDIA CORP",
                "facts": {
                    "us-gaap": {
                        "Revenues": {
                            "units": {
                                "USD": [
                                    {"fy": 2025, "fp": "FY", "end": "2025-01-31", "val": 1000},
                                    {"fy": 2024, "fp": "FY", "end": "2024-01-31", "val": 800},
                                ]
                            }
                        },
                        "NetIncomeLoss": {
                            "units": {
                                "USD": [
                                    {"fy": 2025, "fp": "FY", "end": "2025-01-31", "val": 300},
                                    {"fy": 2024, "fp": "FY", "end": "2024-01-31", "val": 200},
                                ]
                            }
                        },
                        "GrossProfit": {
                            "units": {
                                "USD": [
                                    {"fy": 2025, "fp": "FY", "end": "2025-01-31", "val": 700},
                                    {"fy": 2024, "fp": "FY", "end": "2024-01-31", "val": 520},
                                ]
                            }
                        },
                        "NetCashProvidedByUsedInOperatingActivities": {
                            "units": {
                                "USD": [
                                    {"fy": 2025, "fp": "FY", "end": "2025-01-31", "val": 360},
                                    {"fy": 2024, "fp": "FY", "end": "2024-01-31", "val": 240},
                                ]
                            }
                        },
                        "CashAndCashEquivalentsAtCarryingValue": {
                            "units": {
                                "USD": [
                                    {"fy": 2025, "fp": "FY", "end": "2025-01-31", "val": 500}
                                ]
                            }
                        },
                        "LongTermDebt": {
                            "units": {
                                "USD": [
                                    {"fy": 2025, "fp": "FY", "end": "2025-01-31", "val": 100}
                                ]
                            }
                        },
                        "EntityCommonStockSharesOutstanding": {
                            "units": {
                                "shares": [
                                    {"fy": 2025, "fp": "FY", "end": "2025-01-31", "val": 100}
                                ]
                            }
                        },
                    }
                },
            }
        return {
            "chart": {
                "result": [{"meta": {"regularMarketPrice": 120.0}}],
            }
        }

    client = SecCompanyFactsMarketDataClient(user_agent="TempletonTest/0.1", fetch_json=fake_fetch, quote_fetch_json=fake_fetch)
    docs = client.get_market_documents("NVDA")

    assert len(docs) == 1
    metadata = docs[0].metadata
    assert metadata["growth_profile"]["revenue_growth_trend"] == "strong"
    assert metadata["cash_flow_profile"]["free_cash_flow_quality"] == "strong"
    assert metadata["balance_sheet_profile"]["debt_risk"] == "low"
    assert metadata["current_valuation"]["pe"] == 40.0


def test_yahoo_finance_news_client_parses_rss_items() -> None:
    rss = b"""
    <rss version="2.0">
      <channel>
        <item>
          <title>NVIDIA beats estimates as AI demand surges</title>
          <link>https://example.com/nvda-news</link>
          <pubDate>Mon, 14 Apr 2026 12:00:00 +0000</pubDate>
          <description>Strong quarter and raised outlook.</description>
        </item>
      </channel>
    </rss>
    """

    client = YahooFinanceNewsClient(
        user_agent="TempletonTest/0.1",
        fetch_bytes=lambda url, headers: rss,
    )
    docs = client.get_recent_news("NVDA")

    assert len(docs) == 1
    assert docs[0].source_name == "NVIDIA beats estimates as AI demand surges"
    assert docs[0].metadata["positive_catalysts"]
    assert docs[0].metadata["event_type"] == "headline"
