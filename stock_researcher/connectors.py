"""Connector interfaces and simple in-memory implementations."""

from __future__ import annotations

import html
import json
import gzip
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

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


class ConnectorError(RuntimeError):
    """Raised when an external data connector fails cleanly."""


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


@dataclass(slots=True)
class EmptyMarketDataClient:
    """No-op client for live runs before market-data integration exists."""

    def get_market_documents(self, ticker: str) -> list[SourceDocument]:
        return []


@dataclass(slots=True)
class EmptyNewsClient:
    """No-op client for live runs before news integration exists."""

    def get_recent_news(self, ticker: str) -> list[SourceDocument]:
        return []


def default_bytes_fetcher(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        body = response.read()
        if response.headers.get("Content-Encoding", "").lower() == "gzip":
            body = gzip.decompress(body)
        return body


def default_url_fetcher(url: str, headers: dict[str, str]) -> dict:
    return json.loads(default_bytes_fetcher(url, headers).decode("utf-8"))


@dataclass(slots=True)
class SecTickerResolver:
    """Shared SEC ticker-to-CIK lookup helper."""

    user_agent: str = "TempletonResearch/0.1 (contact: local@example.com)"
    fetch_json: Callable[[str, dict[str, str]], dict] = default_url_fetcher

    def lookup_cik(self, ticker: str) -> str:
        mapping = self.fetch_json("https://www.sec.gov/files/company_tickers.json", self._headers())
        target = ticker.upper()
        for item in mapping.values():
            if str(item.get("ticker", "")).upper() == target:
                return str(item["cik_str"]).zfill(10)
        raise ValueError(f"Ticker {ticker!r} not found in SEC company_tickers.json")

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        }


@dataclass(slots=True)
class SecFilingsClient(SecTickerResolver):
    """Fetches recent SEC filings from official SEC JSON endpoints."""
    fetch_bytes: Callable[[str, dict[str, str]], bytes] = default_bytes_fetcher

    def get_company_filings(self, ticker: str) -> list[SourceDocument]:
        try:
            cik = self.lookup_cik(ticker)
            submissions = self.fetch_json(self._submissions_url(cik), self._headers())
            return self._documents_from_submissions(ticker=ticker, cik=cik, submissions=submissions)
        except (HTTPError, URLError, ValueError) as exc:
            raise ConnectorError(f"SEC filings lookup failed for {ticker.upper()}: {exc}") from exc

    def _submissions_url(self, cik: str) -> str:
        return f"https://data.sec.gov/submissions/CIK{cik}.json"

    def _documents_from_submissions(self, ticker: str, cik: str, submissions: dict) -> list[SourceDocument]:
        recent = submissions.get("filings", {}).get("recent", {})
        accession_numbers = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        primary_documents = recent.get("primaryDocument", [])
        docs: list[SourceDocument] = []
        retrieved_at = datetime.now(timezone.utc).isoformat()
        company_name = str(submissions.get("name", ticker))
        sic_description = str(submissions.get("sicDescription", "")).strip()
        records = list(zip(accession_numbers, forms, filing_dates, primary_documents))
        prioritized_records = sorted(
            records,
            key=lambda item: (
                self._form_priority(str(item[1])),
                -self._date_rank(str(item[2])),
            ),
            reverse=False,
        )[:8]

        for accession, form, filing_date, primary_document in prioritized_records:
            accession_clean = str(accession).replace("-", "")
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{primary_document}"
            )
            metadata = {
                "company_name": company_name,
                "form": form,
                "filing_date": filing_date,
                "sic_description": sic_description,
            }
            metadata.update(self._enrich_form_metadata(company_name=company_name, form=form, sic_description=sic_description))
            if form in {"10-K", "10-Q", "20-F", "40-F"}:
                metadata.update(self._extract_filing_metadata(company_name=company_name, form=form, filing_url=filing_url))
            docs.append(
                SourceDocument(
                    source_name=f"{company_name} {form}",
                    source_type="company_filing_or_release",
                    source_url=filing_url,
                    published_at=f"{filing_date}T00:00:00Z",
                    retrieved_at=retrieved_at,
                    ticker=ticker.upper(),
                    metadata=metadata,
                )
            )
        return docs

    def _form_priority(self, form: str) -> int:
        if form in {"10-K", "20-F", "40-F"}:
            return 0
        if form in {"10-Q"}:
            return 1
        if form in {"8-K", "6-K"}:
            return 2
        return 3

    def _date_rank(self, filing_date: str) -> int:
        digits = filing_date.replace("-", "")
        return int(digits) if digits.isdigit() else 0

    def _enrich_form_metadata(self, company_name: str, form: str, sic_description: str) -> dict:
        metadata: dict[str, object] = {}
        sector_hint = f" in {sic_description}" if sic_description else ""
        if form in {"10-K", "20-F", "40-F"}:
            metadata["business_model"] = (
                f"{company_name} operates{sector_hint} and its annual report should contain the clearest description of its business model, end markets, and risks."
            )
            metadata["competitive_advantages"] = [
                "Primary annual company filing available for review",
                "Management business description available in the filing set",
            ]
            metadata["vulnerabilities"] = [
                "Detailed filing text extraction is still heuristic in live mode",
            ]
            metadata["event_type"] = "annual_report"
            metadata["expected_impact"] = "high"
        elif form in {"10-Q", "6-K"}:
            metadata["positive_catalysts"] = ["Quarterly update available"]
            metadata["negative_catalysts"] = ["Quarterly filing may contain changed risk disclosures"]
            metadata["event_type"] = "quarterly_update"
            metadata["expected_impact"] = "medium"
        elif form == "8-K":
            metadata["positive_catalysts"] = ["Current report may include material corporate updates"]
            metadata["negative_catalysts"] = ["Current report may disclose adverse developments"]
            metadata["event_type"] = "current_report"
            metadata["expected_impact"] = "medium"
        return metadata

    def _extract_filing_metadata(self, company_name: str, form: str, filing_url: str) -> dict:
        try:
            raw = self.fetch_bytes(filing_url, self._headers()).decode("utf-8", errors="ignore")
        except (HTTPError, URLError, ValueError):
            return {}

        text = self._normalize_filing_text(raw)
        if not text:
            return {}

        business_section = self._extract_section(
            text=text,
            start_patterns=self._business_start_patterns(form),
            end_patterns=self._business_end_patterns(form),
        )
        risk_section = self._extract_section(
            text=text,
            start_patterns=self._risk_start_patterns(form),
            end_patterns=self._risk_end_patterns(form),
        )

        business_model = self._extract_business_model(company_name, business_section)
        revenue_drivers = self._extract_revenue_drivers(business_section)
        competitive_advantages = self._extract_competitive_advantages(business_section)
        vulnerabilities = self._extract_risk_items(risk_section)
        core_risks = [
            {"risk": item, "severity": "medium", "likelihood": "medium"} for item in vulnerabilities[:3]
        ]

        metadata: dict[str, object] = {}
        if business_model:
            metadata["business_model"] = business_model
        if revenue_drivers:
            metadata["revenue_drivers"] = revenue_drivers
        if competitive_advantages:
            metadata["competitive_advantages"] = competitive_advantages
        if vulnerabilities:
            metadata["vulnerabilities"] = vulnerabilities
            metadata["core_risks"] = core_risks
            metadata["thesis_breakers"] = vulnerabilities[:2]
            metadata["monitoring_indicators"] = self._monitoring_indicators_from_risks(vulnerabilities)
        return metadata

    def _normalize_filing_text(self, raw_html: str) -> str:
        text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw_html)
        text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
        text = re.sub(r"(?is)<!--.*?-->", " ", text)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</p>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"&nbsp;|&#160;", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _extract_section(self, text: str, start_patterns: list[str], end_patterns: list[str]) -> str:
        lowered = text.lower()
        start_index = 0
        for pattern in start_patterns:
            match = re.search(pattern, lowered)
            if match:
                start_index = match.start()
                break
        snippet = text[start_index:start_index + 30000]
        snippet_lower = snippet.lower()
        end_index = len(snippet)
        for pattern in end_patterns:
            match = re.search(pattern, snippet_lower)
            if match and match.start() > 200:
                end_index = match.start()
                break
        return snippet[:end_index].strip()

    def _business_start_patterns(self, form: str) -> list[str]:
        if form in {"20-F", "40-F"}:
            return [r"item\s+4\W+information on the company", r"business overview", r"information on the company"]
        return [r"item\s+1\W+business", r"business overview", r"our business"]

    def _business_end_patterns(self, form: str) -> list[str]:
        if form in {"20-F", "40-F"}:
            return [r"item\s+4a", r"item\s+5", r"risk factors"]
        return [r"item\s+1a\W+risk factors", r"item\s+1b", r"item\s+2"]

    def _risk_start_patterns(self, form: str) -> list[str]:
        if form in {"20-F", "40-F"}:
            return [r"risk factors", r"item\s+3\W+key information"]
        return [r"item\s+1a\W+risk factors", r"risk factors"]

    def _risk_end_patterns(self, form: str) -> list[str]:
        if form in {"20-F", "40-F"}:
            return [r"item\s+4\W+information on the company", r"item\s+5", r"item\s+6"]
        return [r"item\s+1b", r"item\s+2", r"item\s+3"]

    def _extract_business_model(self, company_name: str, section: str) -> str | None:
        company_token = company_name.lower().split()[0]
        candidates: list[tuple[int, str]] = []
        for sentence in self._sentences(section):
            lowered = sentence.lower()
            if self._is_noisy_sentence(sentence):
                continue
            has_business_verb = re.search(
                r"\b(designs?|develops?|operates?|manufactures?|sells?|provides?|supplies?|includes?|offers?)\b",
                lowered,
            )
            has_subject = company_token in lowered or re.search(r"\b(we|our|company)\b", lowered)
            has_business_object = any(
                term in lowered
                for term in (
                    "systems",
                    "platform",
                    "products",
                    "services",
                    "software",
                    "equipment",
                    "customers",
                    "manufacturers",
                    "applications",
                    "solutions",
                    "technology",
                    "chip",
                )
            )
            if has_business_verb and has_subject:
                if any(term in lowered for term in ("this document", "website", "incorporated by reference")):
                    continue
                if not has_business_object:
                    continue
                score = self._business_sentence_score(sentence=sentence, company_token=company_token)
                candidates.append((score, sentence))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _extract_revenue_drivers(self, section: str) -> list[str]:
        drivers: list[tuple[int, str]] = []
        for sentence in self._sentences(section):
            lowered = sentence.lower()
            if self._is_noisy_sentence(sentence):
                continue
            if any(term in lowered for term in ("revenue", "sales", "customer", "segment", "product", "service", "end market")):
                drivers.append((self._descriptive_sentence_score(sentence), sentence))
        return self._top_unique_sentences(drivers, limit=3)

    def _extract_competitive_advantages(self, section: str) -> list[str]:
        advantages: list[tuple[int, str]] = []
        for sentence in self._sentences(section):
            lowered = sentence.lower()
            if self._is_noisy_sentence(sentence):
                continue
            if any(
                term in lowered
                for term in ("lead", "leader", "technology", "platform", "ecosystem", "scale", "installed base", "proprietary", "switching")
            ):
                advantages.append((self._descriptive_sentence_score(sentence), sentence))
        return self._top_unique_sentences(advantages, limit=3)

    def _extract_risk_items(self, section: str) -> list[str]:
        risks: list[tuple[int, str]] = []
        for sentence in self._sentences(section):
            lowered = sentence.lower()
            if self._is_noisy_sentence(sentence) or self._is_generic_risk_sentence(sentence):
                continue
            if self._has_negative_risk_cue(lowered):
                risks.append((self._risk_sentence_score(sentence), sentence))
        return self._top_unique_sentences(risks, limit=4)

    def _monitoring_indicators_from_risks(self, risks: list[str]) -> list[str]:
        indicators: list[str] = []
        joined = " ".join(risks).lower()
        mapping = {
            "demand": "Revenue growth",
            "margin": "Gross margin trend",
            "customer": "Customer concentration",
            "supply": "Supply-chain commentary",
            "regulation": "Regulatory developments",
            "trade": "Trade restriction developments",
            "competition": "Competitive positioning",
        }
        for key, label in mapping.items():
            if key in joined and label not in indicators:
                indicators.append(label)
        return indicators[:4]

    def _sentences(self, text: str) -> list[str]:
        pieces = re.split(r"(?<=[.!?])\s+", text)
        cleaned = []
        for piece in pieces:
            normalized = piece.strip()
            if 60 <= len(normalized) <= 320:
                cleaned.append(normalized)
        return cleaned

    def _is_noisy_sentence(self, sentence: str) -> bool:
        lowered = sentence.lower()
        if sum(char.isdigit() for char in sentence) > 12:
            return True
        if sentence.count(";") >= 2:
            return True
        if re.match(r"^[A-Z0-9 ,./()-]{20,}$", sentence):
            return True
        noise_terms = (
            "table of contents",
            "board of management",
            "financial performance",
            "commission file number",
            "form 6-k",
            "brainport eindhoven",
            "patents and licenses",
            "significant changes",
            "offer and listing",
            "notes to the consolidated",
            "incorporated by reference",
            "this document also includes",
            "referred to as",
            "part iii item",
            "item 8.",
            "item 10.",
            "quantitative and qualitative disclosures",
            "disclosure regarding foreign jurisdictions",
            "preference shares foundation",
            "throughput of the measured system",
            "dynamic random-access memory",
            "non-employees includes both",
            "employment activities",
        )
        return any(term in lowered for term in noise_terms)

    def _is_generic_risk_sentence(self, sentence: str) -> bool:
        lowered = sentence.lower()
        generic_terms = (
            "forward-looking statements",
            "these risks and uncertainties include",
            "the section entitled",
            "risk factors discussed",
            "see also",
            "item 1a",
            "item 3d",
        )
        return any(term in lowered for term in generic_terms)

    def _business_sentence_score(self, sentence: str, company_token: str) -> int:
        lowered = sentence.lower()
        score = self._descriptive_sentence_score(sentence)
        if company_token in lowered:
            score += 3
        if re.search(r"\b(designs?|develops?|operates?|manufactures?|sells?|provides?|supplies?)\b", lowered):
            score += 4
        if any(term in lowered for term in ("customers", "systems", "platform", "products", "services", "manufacturers")):
            score += 2
        return score

    def _risk_sentence_score(self, sentence: str) -> int:
        lowered = sentence.lower()
        score = self._descriptive_sentence_score(sentence)
        if "could" in lowered or "may" in lowered:
            score += 2
        if any(term in lowered for term in ("demand", "competition", "regulation", "trade", "supply", "customer")):
            score += 2
        return score

    def _has_negative_risk_cue(self, lowered: str) -> bool:
        negative_cues = (
            "adverse",
            "adversely",
            "could",
            "may not",
            "depend",
            "decline",
            "decrease",
            "disrupt",
            "disruption",
            "restrict",
            "restriction",
            "regulation",
            "regulatory",
            "competition",
            "competitive",
            "supply",
            "cyclic",
            "cyclical",
            "trade",
            "tariff",
            "unable",
            "uncertain",
            "materially affect",
            "materially impact",
            "expose",
            "volatility",
            "shortage",
            "delay",
        )
        positive_false_positives = (
            "strengthens our ecosystem",
            "we believe will continue",
            "growth opportunities",
            "fuel capacity build-up",
            "starting to fuel",
        )
        return any(cue in lowered for cue in negative_cues) and not any(
            phrase in lowered for phrase in positive_false_positives
        )

    def _descriptive_sentence_score(self, sentence: str) -> int:
        lowered = sentence.lower()
        score = 0
        if 90 <= len(sentence) <= 240:
            score += 2
        if sentence.count(",") <= 3:
            score += 1
        if not re.search(r"\b(item|part|note|section)\b", lowered):
            score += 2
        if not re.search(r"\b(defined as|referred to as|means)\b", lowered):
            score += 2
        return score

    def _top_unique_sentences(self, scored_sentences: list[tuple[int, str]], limit: int) -> list[str]:
        ordered = sorted(scored_sentences, key=lambda item: item[0], reverse=True)
        results: list[str] = []
        for _, sentence in ordered:
            if sentence not in results:
                results.append(sentence)
            if len(results) == limit:
                break
        return results


@dataclass(slots=True)
class SecCompanyFactsMarketDataClient(SecTickerResolver):
    """Fetches SEC companyfacts and derives financial-quality metadata."""

    quote_fetch_json: Callable[[str, dict[str, str]], dict] = default_url_fetcher

    def get_market_documents(self, ticker: str) -> list[SourceDocument]:
        try:
            cik = self.lookup_cik(ticker)
            company_facts = self.fetch_json(self._companyfacts_url(cik), self._headers())
            chart = self._fetch_chart(ticker)
            return [self._document_from_companyfacts(ticker=ticker, company_facts=company_facts, chart=chart)]
        except (HTTPError, URLError, ValueError, KeyError) as exc:
            raise ConnectorError(f"Live market-data lookup failed for {ticker.upper()}: {exc}") from exc

    def _companyfacts_url(self, cik: str) -> str:
        return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    def _fetch_chart(self, ticker: str) -> dict:
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}?range=1y&interval=1d"
        return self.quote_fetch_json(url, headers)

    def _document_from_companyfacts(self, ticker: str, company_facts: dict, chart: dict) -> SourceDocument:
        facts_root = company_facts.get("facts", {})
        fact_sets = [namespace for namespace in (facts_root.get("us-gaap"), facts_root.get("ifrs-full")) if isinstance(namespace, dict)]
        revenue_series = self._series_any(
            fact_sets,
            [
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "Revenue",
            ],
        )
        net_income_series = self._series_any(fact_sets, ["NetIncomeLoss", "ProfitLoss"])
        gross_profit_series = self._series_any(fact_sets, ["GrossProfit"])
        operating_cash_flow_series = self._series_any(
            fact_sets,
            [
                "NetCashProvidedByUsedInOperatingActivities",
                "CashFlowsFromUsedInOperatingActivities",
            ],
        )
        cash_series = self._series_any(
            fact_sets,
            [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashAndCashEquivalents",
            ],
        )
        debt_series = self._series_any(
            fact_sets,
            [
                "LongTermDebtAndCapitalLeaseObligations",
                "LongTermDebt",
                "Borrowings",
            ],
        )
        shares_series = self._series_any(
            fact_sets,
            [
                "CommonStockSharesOutstanding",
                "EntityCommonStockSharesOutstanding",
                "NumberOfSharesOutstanding",
            ],
        )

        latest_revenue, previous_revenue = self._latest_pair(revenue_series)
        latest_income, previous_income = self._latest_pair(net_income_series)
        latest_gross, previous_gross = self._latest_pair(gross_profit_series)
        latest_ocf, _ = self._latest_pair(operating_cash_flow_series)
        latest_cash, _ = self._latest_pair(cash_series)
        latest_debt, _ = self._latest_pair(debt_series)
        latest_shares, _ = self._latest_pair(shares_series)
        price = self._latest_price(chart)
        closes = self._closing_prices(chart)

        latest_margin = self._ratio(latest_gross, latest_revenue)
        previous_margin = self._ratio(previous_gross, previous_revenue)
        pe = self._compute_pe(price, latest_income, latest_shares)
        technical_analysis = self._technical_metadata(closes=closes, price=price)

        metadata = {
            "growth_profile": {
                "revenue_growth_trend": self._growth_label(latest_revenue, previous_revenue),
                "earnings_growth_trend": self._growth_label(latest_income, previous_income),
            },
            "margin_profile": {
                "gross_margin_trend": self._margin_label(latest_margin, previous_margin),
                "operating_margin_trend": "unknown",
            },
            "cash_flow_profile": {
                "free_cash_flow_quality": self._cash_flow_label(latest_ocf, latest_income),
                "cash_conversion": self._cash_conversion_label(latest_ocf, latest_income),
            },
            "balance_sheet_profile": {
                "debt_risk": self._debt_risk_label(latest_cash, latest_debt),
                "liquidity": "strong" if isinstance(latest_cash, (int, float)) and latest_cash > 0 else "unknown",
            },
            "capital_allocation": {
                "dilution_risk": "unknown",
                "buyback_profile": "unknown",
            },
            "valuation_methods": ["sec_companyfacts", "yahoo_chart_quote"],
            "current_valuation": {
                "pe": pe,
                "price": price,
                "shares_outstanding": latest_shares,
            },
            "scenario_ranges": {},
            "market_implied_expectations": [],
            "technical_analysis": technical_analysis,
        }

        company_name = str(company_facts.get("entityName", ticker.upper()))
        retrieved_at = datetime.now(timezone.utc).isoformat()
        return SourceDocument(
            source_name=f"{company_name} company facts",
            source_type="market_data",
            source_url=self._companyfacts_url(str(company_facts.get("cik", "")).zfill(10)),
            published_at=retrieved_at,
            retrieved_at=retrieved_at,
            ticker=ticker.upper(),
            metadata=metadata,
        )

    def _series_any(self, fact_sets: list[dict], concepts: list[str]) -> list[dict]:
        for facts in fact_sets:
            for concept in concepts:
                series = self._series(facts, concept)
                if series:
                    return series
        return []

    def _series(self, facts: dict, concept: str) -> list[dict]:
        concept_block = facts.get(concept, {})
        units = concept_block.get("units", {})
        for unit_name in ("USD", "EUR", "shares", "pure"):
            unit_values = units.get(unit_name)
            if isinstance(unit_values, list):
                return unit_values
        return []

    def _latest_pair(self, series: list[dict]) -> tuple[float | None, float | None]:
        filtered = [item for item in series if "val" in item and ("fy" in item or "frame" in item)]
        sorted_items = sorted(
            filtered,
            key=lambda item: (
                str(item.get("fy", "")),
                str(item.get("fp", "")),
                str(item.get("end", "")),
            ),
            reverse=True,
        )
        latest = self._as_number(sorted_items[0].get("val")) if len(sorted_items) >= 1 else None
        previous = self._as_number(sorted_items[1].get("val")) if len(sorted_items) >= 2 else None
        return latest, previous

    def _latest_price(self, quote: dict) -> float | None:
        result = quote.get("chart", {}).get("result", [])
        if not result:
            return None
        meta = result[0].get("meta", {})
        regular_market = self._as_number(meta.get("regularMarketPrice"))
        if regular_market is not None:
            return regular_market
        closes = self._closing_prices(quote)
        return closes[-1] if closes else None

    def _closing_prices(self, chart: dict) -> list[float]:
        result = chart.get("chart", {}).get("result", [])
        if not result:
            return []
        indicators = result[0].get("indicators", {}).get("quote", [])
        if not indicators:
            return []
        closes = indicators[0].get("close", [])
        return [float(value) for value in closes if isinstance(value, (int, float))]

    def _as_number(self, value) -> float | None:
        return float(value) if isinstance(value, (int, float)) else None

    def _ratio(self, numerator: float | None, denominator: float | None) -> float | None:
        if numerator is None or denominator in (None, 0):
            return None
        return numerator / denominator

    def _compute_pe(
        self,
        price: float | None,
        net_income: float | None,
        shares_outstanding: float | None,
    ) -> float | None:
        if price is None or net_income in (None, 0) or shares_outstanding in (None, 0):
            return None
        eps = net_income / shares_outstanding
        if eps <= 0:
            return None
        return round(price / eps, 2)

    def _growth_label(self, latest: float | None, previous: float | None) -> str:
        if latest is None or previous in (None, 0):
            return "unknown"
        if latest > previous * 1.1:
            return "strong"
        if latest > previous:
            return "positive"
        return "negative"

    def _margin_label(self, latest: float | None, previous: float | None) -> str:
        if latest is None or previous is None:
            return "unknown"
        if latest > previous + 0.01:
            return "up"
        if latest < previous - 0.01:
            return "down"
        return "stable"

    def _cash_flow_label(self, operating_cash_flow: float | None, net_income: float | None) -> str:
        if operating_cash_flow is None or net_income is None:
            return "unknown"
        if operating_cash_flow > 0 and operating_cash_flow >= net_income:
            return "strong"
        if operating_cash_flow > 0:
            return "healthy"
        return "weak"

    def _cash_conversion_label(self, operating_cash_flow: float | None, net_income: float | None) -> str:
        if operating_cash_flow is None or net_income in (None, 0):
            return "unknown"
        ratio = operating_cash_flow / net_income
        if ratio >= 1:
            return "healthy"
        if ratio > 0:
            return "mixed"
        return "weak"

    def _debt_risk_label(self, cash: float | None, debt: float | None) -> str:
        if debt is None:
            return "unknown"
        if cash is not None and cash >= debt:
            return "low"
        if cash is not None and debt > cash * 2:
            return "high"
        return "medium"

    def _technical_metadata(self, closes: list[float], price: float | None) -> dict:
        if not closes:
            return {
                "trend": "unknown",
                "momentum": "unknown",
                "key_levels": {"support": [], "resistance": []},
                "entry_quality": "unknown",
                "risk_management_note": "Insufficient price history for technical analysis.",
            }
        sma20 = self._sma(closes, 20)
        sma50 = self._sma(closes, 50)
        sma200 = self._sma(closes, 200)
        recent_20 = closes[-20:] if len(closes) >= 20 else closes
        recent_60 = closes[-60:] if len(closes) >= 60 else closes
        current_price = price if price is not None else closes[-1]
        trend = self._trend_label(current_price, sma50, sma200)
        momentum = self._momentum_label(current_price, sma20, closes)
        support = [level for level in (sma50, min(recent_60)) if isinstance(level, (int, float))]
        resistance = [level for level in (max(recent_20), max(closes)) if isinstance(level, (int, float))]
        entry_quality = self._entry_quality(current_price, sma20, sma50)
        return {
            "trend": trend,
            "momentum": momentum,
            "key_levels": {
                "support": [round(level, 2) for level in support[:2]],
                "resistance": [round(level, 2) for level in resistance[:2]],
            },
            "entry_quality": entry_quality,
            "risk_management_note": self._risk_note(entry_quality, support[:2]),
        }

    def _sma(self, closes: list[float], window: int) -> float | None:
        if len(closes) < window:
            return None
        sample = closes[-window:]
        return sum(sample) / len(sample)

    def _trend_label(self, price: float, sma50: float | None, sma200: float | None) -> str:
        if sma50 is None or sma200 is None:
            return "mixed"
        if price > sma50 > sma200:
            return "uptrend"
        if price < sma50 < sma200:
            return "downtrend"
        return "mixed"

    def _momentum_label(self, price: float, sma20: float | None, closes: list[float]) -> str:
        if sma20 is None or len(closes) < 21:
            return "neutral"
        prior_price = closes[-21]
        if price > sma20 and price > prior_price:
            return "positive"
        if price < sma20 and price < prior_price:
            return "negative"
        return "neutral"

    def _entry_quality(self, price: float, sma20: float | None, sma50: float | None) -> str:
        if sma20 is None or sma50 is None:
            return "unknown"
        distance_from_sma20 = abs(price - sma20) / sma20 if sma20 else 0
        if price >= sma20 >= sma50 and distance_from_sma20 <= 0.05:
            return "constructive"
        if price > sma20 and distance_from_sma20 > 0.08:
            return "extended"
        return "neutral"

    def _risk_note(self, entry_quality: str, support_levels: list[float]) -> str:
        if entry_quality == "extended":
            return "Price is extended above short-term support; avoid chasing strength."
        if support_levels:
            return f"Monitor support near {round(support_levels[0], 2)} for pullback risk."
        return "Use recent support levels to manage entry risk."


@dataclass(slots=True)
class YahooFinanceNewsClient:
    """Fetches recent ticker news headlines from Yahoo Finance RSS."""

    user_agent: str = "TempletonResearch/0.1 (contact: local@example.com)"
    fetch_bytes: Callable[[str, dict[str, str]], bytes] = default_bytes_fetcher

    def get_recent_news(self, ticker: str) -> list[SourceDocument]:
        try:
            body = self._fetch_rss(ticker)
            return self._documents_from_rss(ticker=ticker, body=body)
        except (HTTPError, URLError, ValueError, ElementTree.ParseError) as exc:
            raise ConnectorError(f"Live news lookup failed for {ticker.upper()}: {exc}") from exc

    def _fetch_rss(self, ticker: str) -> bytes:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker.upper()}&region=US&lang=en-US"
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        return self.fetch_bytes(url, headers)

    def _documents_from_rss(self, ticker: str, body: bytes) -> list[SourceDocument]:
        root = ElementTree.fromstring(body)
        channel = root.find("channel")
        if channel is None:
            return []
        documents: list[SourceDocument] = []
        for item in channel.findall("item")[:8]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            description = self._clean_text(item.findtext("description") or "")
            published_at = self._rss_date_to_iso(pub_date)
            metadata = self._news_metadata(title=title, description=description)
            documents.append(
                SourceDocument(
                    source_name=title or f"{ticker.upper()} news item",
                    source_type="news",
                    source_url=link or "https://finance.yahoo.com",
                    published_at=published_at,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    ticker=ticker.upper(),
                    metadata=metadata,
                )
            )
        return documents

    def _rss_date_to_iso(self, value: str) -> str:
        if not value:
            return datetime.now(timezone.utc).isoformat()
        try:
            parsed = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %z")
            return parsed.astimezone(timezone.utc).isoformat()
        except ValueError:
            return datetime.now(timezone.utc).isoformat()

    def _clean_text(self, value: str) -> str:
        return re.sub(r"<[^>]+>", "", value).strip()

    def _news_metadata(self, title: str, description: str) -> dict:
        combined = f"{title} {description}".lower()
        positive_terms = ["beat", "wins", "surge", "growth", "raises", "expands", "strong", "record"]
        negative_terms = ["miss", "cuts", "probe", "lawsuit", "delay", "drop", "risk", "weak", "ban"]
        positive_hits = [term for term in positive_terms if term in combined]
        negative_hits = [term for term in negative_terms if term in combined]
        return {
            "positive_catalysts": [f"Headline suggests positive catalyst: {title}"] if positive_hits else [],
            "negative_catalysts": [f"Headline suggests risk catalyst: {title}"] if negative_hits else [],
            "event_type": "headline",
            "expected_impact": "high" if positive_hits or negative_hits else "medium",
        }
