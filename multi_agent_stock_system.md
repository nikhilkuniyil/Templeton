# Multi-Agent Stock Research System v1

## Overview

This project is a multi-agent stock research system designed to help users:
- Discover investable stock ideas
- Investigate individual companies in depth
- Decide whether a stock is a buy now, a watchlist candidate, or a pass

The system is a research and decision-support tool, not an autonomous trader. Its job is to produce structured, source-backed analysis with clear uncertainty and explicit decision logic.

---

## Primary Goal

The system should answer a practical question:

`Is this stock worth buying for this user, at this price, over this time horizon?`

That means the system must go beyond description and cover:
- Business quality
- Financial quality
- Valuation
- Technical context
- Recent news and catalysts
- Downside risks
- Decision criteria tied to a stated time horizon

---

## Core Modes

### 1. Discovery Mode
Generate and rank stock ideas based on themes, filters, user goals, or market conditions.

Examples:
- AI infrastructure stocks with strong earnings revisions
- High-quality compounders trading below historical valuation ranges
- Small-cap biotech names with near-term catalysts

Primary output:
- Ranked candidate list with brief reasons, risks, and follow-up priorities

### 2. Investigation Mode
Deep-dive into a specific stock and produce a full investment memo.

Examples:
- Is NVDA still worth buying after its recent run?
- What are the key risks in SOFI?
- Is ASML attractive for a 3 to 5 year holding period?

Primary output:
- Buy / Watch / Pass recommendation with evidence, confidence, and invalidation criteria

### 3. Comparison Mode
Compare multiple stocks in the same theme, sector, or portfolio slot.

Examples:
- NVDA vs AMD
- CRWD vs PANW
- COST vs WMT for a defensive compounder position

Primary output:
- Relative ranking, tradeoffs, and best fit by objective

### 4. Conversational Mode
Allow the user to chat freely with the system while preserving source grounding and structured follow-up when needed.

Examples:
- Explain AMD's business in simple terms
- What changed in the Tesla thesis since last earnings?
- Why did you rate this as Watch instead of Buy?
- Find me three similar companies but with better free cash flow quality

Primary output:
- Direct conversational answer, with optional follow-up actions such as launching a full investigation, comparison, or watchlist flow

---

## System Architecture

The system is composed of specialized agents with clear responsibilities, defined inputs, and structured outputs. The architecture is designed to reduce hallucinations, separate evidence gathering from judgment, and make disagreements between agents explicit.

The user should be able to interact with the system in two ways:
- Structured workflows such as discovery, investigation, and comparison
- Free-form chat with a conversational interface agent that can answer directly or trigger deeper workflows

---

## Agent Definitions

### 1. Router / Planner Agent
Responsibilities:
- Interpret the user request
- Detect mode: discovery, investigation, or comparison
- Determine user objective, time horizon, and constraints
- Decide which downstream agents must run

Inputs:
- User query
- Optional user profile or portfolio context

Outputs:
- Execution plan
- Required symbols
- Time horizon: short-term, medium-term, long-term
- Evaluation lens: trade, investment, income, growth, value, catalyst-driven

### 2. Data / Source Verification Agent
Responsibilities:
- Gather market data, financial data, and source documents
- Attach timestamps and source references to every material claim
- Flag missing, stale, conflicting, or low-confidence data

Inputs:
- Requested symbol set
- Required analysis dimensions

Outputs:
- Source-backed evidence packet
- Data freshness report
- Missing-data warnings

Rules:
- No unsupported factual claims
- Every numeric claim should be tied to a source and date when possible
- Conflicts between sources should be surfaced, not silently resolved

### 3. Screener / Universe Agent
Responsibilities:
- Generate candidate stocks for discovery workflows
- Apply user filters and ranking logic
- Avoid returning a broad, low-signal list

Inputs:
- Theme, sector, style, market-cap, geography, catalyst type, valuation constraints

Outputs:
- Ranked candidate set
- Why each candidate qualified
- Why top candidates outrank the rest

Example ranking factors:
- Revenue growth
- Earnings revisions
- Margin trend
- Relative strength
- Valuation percentile
- Upcoming catalysts

### 4. Business Quality Agent
Responsibilities:
- Explain what the company does
- Identify business model, competitive position, and growth drivers
- Evaluate moat, market structure, and management execution quality

Inputs:
- Company filings
- Investor materials
- Source packet

Outputs:
- Plain-English business summary
- Key revenue drivers
- Competitive advantages and vulnerabilities
- Durability assessment

### 5. Financial Quality Agent
Responsibilities:
- Evaluate core financial health and operating quality
- Separate accounting growth from real economic strength

Inputs:
- Income statement, balance sheet, cash flow statement, guidance, historical trends

Outputs:
- Growth profile
- Margin profile
- Free cash flow quality
- Debt and liquidity assessment
- Share dilution or buyback profile
- Overall quality rating

Key checks:
- Revenue growth consistency
- Gross and operating margin trend
- Free cash flow generation
- Net debt and refinancing risk
- Return on invested capital if available
- Stock-based compensation burden

### 6. Valuation Agent
Responsibilities:
- Determine whether the stock is cheap, fair, or expensive relative to fundamentals and peers
- Translate valuation into expected return logic instead of raw multiples alone

Inputs:
- Current price
- Historical multiples
- Peer group
- Growth and margin assumptions

Outputs:
- Valuation framework used
- Base, bull, and bear valuation ranges
- Market-implied expectations
- Upside / downside asymmetry

Acceptable methods:
- P/E, EV/EBITDA, EV/Sales, FCF yield, sum-of-the-parts, DCF, or scenario-based comparables

### 7. Technical Analysis Agent
Responsibilities:
- Evaluate price action, trend, support/resistance, and market structure
- Assess entry quality, not intrinsic business quality

Inputs:
- Price and volume history

Outputs:
- Trend assessment
- Momentum status
- Key levels
- Entry timing context

Rules:
- Technicals should influence timing and risk management
- Technicals should not override weak business, financial, or valuation conclusions in long-term investment mode

### 8. News / Catalyst Agent
Responsibilities:
- Extract the current narrative around the stock
- Identify catalysts that may change fundamentals, sentiment, or valuation

Inputs:
- Recent news
- Earnings reports
- Regulatory updates
- Product launches
- Macro or sector developments

Outputs:
- Recent narrative summary
- Positive catalysts
- Negative catalysts
- Catalyst timing and likely importance

Rules:
- Distinguish signal from noise
- Separate one-off headlines from thesis-changing events

### 9. Risk Agent
Responsibilities:
- Build the bear case
- Identify what could go wrong operationally, financially, competitively, or macroeconomically

Inputs:
- Outputs from all prior agents

Outputs:
- Core risk list
- Severity and likelihood assessment
- What would break the thesis
- Key monitoring indicators

The Risk Agent must explicitly argue against a buy conclusion when the evidence supports caution.

### 10. Decision / Portfolio Fit Agent
Responsibilities:
- Convert the research into an actionable decision
- Judge the stock in the context of user objective and existing exposure if available

Inputs:
- Full research packet
- User time horizon
- Risk tolerance
- Optional portfolio context

Outputs:
- Decision: Buy, Watch, or Pass
- Confidence: Low, Medium, or High
- Best fit: trade, starter position, long-term hold, or not suitable
- Portfolio overlap or concentration flags

Decision rules:
- `Buy` means the stock has an attractive setup on quality, valuation, and/or catalyst-adjusted expected return
- `Watch` means the business may be attractive, but price, timing, or uncertainty is not favorable yet
- `Pass` means the downside, valuation, or thesis weakness is too high relative to reward

### 11. Synthesizer / Investment Memo Agent
Responsibilities:
- Merge outputs into a clear final memo
- Preserve disagreement instead of flattening it
- Produce a concise conclusion with supporting evidence

Outputs:
- Final memo
- Decision summary
- Open questions
- Follow-up monitoring checklist

### 12. Conversational Interface Agent
Responsibilities:
- Handle free-form user chat
- Answer quick questions directly when existing evidence is sufficient
- Ask the planner for a deeper workflow when the request needs fresh data or multi-agent analysis
- Explain prior recommendations in plain language

Inputs:
- User message
- Conversation history
- Existing research memos and evidence if available

Outputs:
- Direct answer
- Clarifying question if needed
- Suggested next action: investigate, compare, screen, refresh, or monitor

Rules:
- Do not answer time-sensitive market questions from stale memory
- If the user asks for current price, recent news, or an updated decision, route through fresh-data retrieval
- Prefer concise answers first, then offer deeper analysis

---

## Agent Interaction Flow

### Discovery Mode

User Query
→ Router / Planner
→ Data / Source Verification
→ Screener / Universe
→ Business Quality + Financial Quality + Valuation + Technical + News + Risk
→ Decision / Portfolio Fit
→ Synthesizer

### Investigation Mode

User Query
→ Router / Planner
→ Data / Source Verification
→ Business Quality + Financial Quality + Valuation + Technical + News + Risk
→ Decision / Portfolio Fit
→ Synthesizer

### Comparison Mode

User Query
→ Router / Planner
→ Data / Source Verification
→ Business Quality + Financial Quality + Valuation + Technical + News + Risk for each symbol
→ Decision / Portfolio Fit
→ Synthesizer

### Conversational Mode

User Query
→ Conversational Interface Agent
→ Router / Planner when deeper work is required
→ Existing memo retrieval and/or fresh Data / Source Verification
→ Relevant specialist agents as needed
→ Conversational response or Synthesizer output

---

## Required Structured Outputs

Each agent should return structured fields, not just prose. This makes the system easier to evaluate, compare, and audit.

Minimum fields by agent:
- `summary`
- `key_points`
- `evidence`
- `confidence`
- `open_questions`

Numeric outputs should include:
- `value`
- `unit`
- `as_of_date`
- `source`

Shared metadata fields should include:
- `agent_name`
- `ticker`
- `analysis_mode`
- `generated_at`
- `confidence`
- `sources_used`

---

## Shared Data Model

The system should use a common set of objects so agents can interoperate cleanly.

### 1. Research Request

```json
{
  "request_id": "req_001",
  "user_query": "Is ASML worth buying for a 3 to 5 year hold?",
  "mode": "investigation",
  "tickers": ["ASML"],
  "time_horizon": "long_term",
  "objective": "long_term_compounding",
  "risk_tolerance": "medium",
  "portfolio_context_available": false,
  "requested_at": "2026-04-13T21:45:00-07:00"
}
```

### 2. Evidence Object

```json
{
  "evidence_id": "ev_001",
  "ticker": "ASML",
  "claim": "ASML generates most of its revenue from lithography systems and related services.",
  "value": null,
  "unit": null,
  "as_of_date": "2026-01-28",
  "source_name": "ASML annual report",
  "source_type": "company_filing_or_release",
  "source_url": "...",
  "published_at": "2026-01-28T00:00:00Z",
  "retrieved_at": "2026-04-13T21:45:10-07:00",
  "claim_scope": "business_model",
  "confidence": "high"
}
```

### 3. Agent Output Envelope

Every agent should return a standard envelope around its domain-specific payload.

```json
{
  "agent_name": "financial_quality",
  "ticker": "ASML",
  "analysis_mode": "investigation",
  "summary": "ASML shows high operating quality with strong margins and cash generation.",
  "key_points": [
    "Revenue growth has remained positive over the last three years.",
    "Free cash flow generation is solid relative to net income."
  ],
  "evidence_ids": ["ev_010", "ev_011"],
  "confidence": "medium",
  "open_questions": [
    "How durable are margins if semiconductor capex slows?"
  ],
  "generated_at": "2026-04-13T21:46:00-07:00",
  "payload": {}
}
```

### 4. Final Decision Object

```json
{
  "ticker": "ASML",
  "decision": "watch",
  "confidence": "medium",
  "time_horizon": "long_term",
  "best_fit": "long_term_hold",
  "thesis": "Exceptional business quality, but current valuation leaves less room for error.",
  "key_reasons_for_decision": [
    "Business quality is high.",
    "Financial quality is strong.",
    "Valuation is not yet compelling enough for a Buy."
  ],
  "invalidation_triggers": [
    "Meaningful deterioration in order trends",
    "Sustained margin compression beyond expectations"
  ],
  "follow_up_actions": [
    "Monitor next earnings report",
    "Track valuation relative to historical range"
  ],
  "generated_at": "2026-04-13T21:47:00-07:00"
}
```

---

## Agent JSON Schemas

The schemas below are intentionally minimal. They should be strict enough for validation but flexible enough to evolve.

### Router / Planner Output Schema

```json
{
  "agent_name": "router_planner",
  "summary": "Investigate ASML for long-term investment suitability.",
  "mode": "investigation",
  "tickers": ["ASML"],
  "time_horizon": "long_term",
  "objective": "long_term_compounding",
  "tasks": [
    "fetch_sources",
    "analyze_business_quality",
    "analyze_financial_quality",
    "analyze_valuation",
    "analyze_news",
    "analyze_risk",
    "make_decision"
  ],
  "needs_fresh_data": true,
  "clarifying_question": null,
  "confidence": "high"
}
```

### Data / Source Verification Output Schema

```json
{
  "agent_name": "source_verification",
  "summary": "Collected primary filings, price data, and recent news.",
  "tickers": ["ASML"],
  "sources_used": [
    {
      "source_name": "ASML annual report",
      "source_type": "company_filing_or_release",
      "published_at": "2026-01-28T00:00:00Z",
      "retrieved_at": "2026-04-13T21:48:00-07:00"
    }
  ],
  "evidence_ids": ["ev_001", "ev_002"],
  "freshness_status": "fresh",
  "missing_data": [],
  "conflicts_found": [],
  "confidence": "high"
}
```

### Screener / Universe Output Schema

```json
{
  "agent_name": "screener_universe",
  "summary": "Ranked five AI infrastructure candidates.",
  "screen_definition": {
    "theme": "AI infrastructure",
    "filters": {
      "market_cap_min": 10000000000,
      "revenue_growth_min": 0.15
    }
  },
  "candidates": [
    {
      "ticker": "NVDA",
      "score": 92,
      "reasons": [
        "Strong revenue growth",
        "Positive earnings revisions"
      ],
      "risks": [
        "Premium valuation"
      ]
    }
  ],
  "confidence": "medium"
}
```

### Business Quality Output Schema

```json
{
  "agent_name": "business_quality",
  "ticker": "ASML",
  "summary": "ASML has a strong competitive position in advanced lithography.",
  "business_model": "Sells lithography systems, upgrades, and services to semiconductor manufacturers.",
  "revenue_drivers": [
    "EUV system demand",
    "Service and installed base growth"
  ],
  "competitive_advantages": [
    "High switching costs",
    "Technological leadership"
  ],
  "vulnerabilities": [
    "Semiconductor capex cyclicality",
    "Customer concentration"
  ],
  "durability_rating": "high",
  "evidence_ids": ["ev_020", "ev_021"],
  "confidence": "medium",
  "open_questions": []
}
```

### Financial Quality Output Schema

```json
{
  "agent_name": "financial_quality",
  "ticker": "ASML",
  "summary": "Financial quality is strong with healthy margins and cash generation.",
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
  "overall_quality_rating": "high",
  "evidence_ids": ["ev_030", "ev_031"],
  "confidence": "medium",
  "open_questions": []
}
```

### Valuation Output Schema

```json
{
  "agent_name": "valuation",
  "ticker": "ASML",
  "summary": "Valuation is above historical average but still defensible under strong execution assumptions.",
  "methods_used": ["historical_multiples", "peer_comparison"],
  "current_valuation": {
    "pe": 34.5,
    "ev_ebitda": 24.1,
    "fcf_yield": 0.025
  },
  "scenario_ranges": {
    "bear": {
      "fair_value": 780,
      "upside_downside_percent": -18
    },
    "base": {
      "fair_value": 910,
      "upside_downside_percent": -4
    },
    "bull": {
      "fair_value": 1080,
      "upside_downside_percent": 14
    }
  },
  "market_implied_expectations": [
    "Sustained high-margin growth"
  ],
  "valuation_label": "fair_to_expensive",
  "evidence_ids": ["ev_040", "ev_041"],
  "confidence": "medium",
  "open_questions": []
}
```

### Technical Analysis Output Schema

```json
{
  "agent_name": "technical_analysis",
  "ticker": "ASML",
  "summary": "Trend remains constructive, but entry is extended from support.",
  "trend": "uptrend",
  "momentum": "positive",
  "key_levels": {
    "support": [860, 825],
    "resistance": [950]
  },
  "entry_quality": "neutral",
  "risk_management_note": "Prefer adding on pullbacks rather than chasing strength.",
  "evidence_ids": ["ev_050"],
  "confidence": "medium",
  "open_questions": []
}
```

### News / Catalyst Output Schema

```json
{
  "agent_name": "news_catalyst",
  "ticker": "ASML",
  "summary": "Recent narrative remains constructive, centered on AI-driven semiconductor demand.",
  "positive_catalysts": [
    "Strong foundry capex outlook",
    "Positive order commentary"
  ],
  "negative_catalysts": [
    "Export restriction risk",
    "Semiconductor demand slowdown"
  ],
  "recent_events": [
    {
      "event_date": "2026-04-05",
      "event_type": "news",
      "headline": "Example event headline",
      "expected_impact": "medium"
    }
  ],
  "evidence_ids": ["ev_060", "ev_061"],
  "confidence": "medium",
  "open_questions": []
}
```

### Risk Output Schema

```json
{
  "agent_name": "risk",
  "ticker": "ASML",
  "summary": "Main risks are cyclical demand swings and policy-related export constraints.",
  "core_risks": [
    {
      "risk": "Semiconductor capex slowdown",
      "severity": "high",
      "likelihood": "medium"
    },
    {
      "risk": "Export restrictions",
      "severity": "high",
      "likelihood": "medium"
    }
  ],
  "thesis_breakers": [
    "Meaningful reduction in customer demand",
    "Structural erosion of margin profile"
  ],
  "monitoring_indicators": [
    "Order growth",
    "Gross margin trend"
  ],
  "evidence_ids": ["ev_070", "ev_071"],
  "confidence": "medium",
  "open_questions": []
}
```

### Decision / Portfolio Fit Output Schema

```json
{
  "agent_name": "decision_portfolio_fit",
  "ticker": "ASML",
  "summary": "Strong business, but current valuation supports Watch rather than Buy.",
  "decision": "watch",
  "confidence": "medium",
  "best_fit": "long_term_hold",
  "portfolio_flags": [
    "Check existing semiconductor equipment exposure"
  ],
  "key_reasons": [
    "Business quality is high.",
    "Valuation leaves less room for error."
  ],
  "invalidation_triggers": [
    "Deteriorating order trends",
    "Material multiple compression with no earnings support"
  ],
  "evidence_ids": ["ev_030", "ev_040", "ev_070"],
  "open_questions": []
}
```

### Synthesizer Output Schema

```json
{
  "agent_name": "synthesizer",
  "ticker": "ASML",
  "summary": "ASML remains a high-quality company, but valuation tempers the attractiveness of a new position.",
  "decision": "watch",
  "confidence": "medium",
  "memo_sections": {
    "thesis": "...",
    "business_quality": "...",
    "financial_quality": "...",
    "valuation": "...",
    "catalysts": "...",
    "risks": "...",
    "monitoring": "..."
  },
  "evidence_ids": ["ev_020", "ev_030", "ev_040", "ev_060", "ev_070"],
  "open_questions": []
}
```

### Conversational Interface Output Schema

```json
{
  "agent_name": "conversational_interface",
  "summary": "Answered the user's question directly and suggested a deeper refresh.",
  "response_type": "direct_answer",
  "answer": "ASML looks like a high-quality business, but whether it is worth buying depends heavily on the current valuation and your time horizon.",
  "used_existing_research": true,
  "needs_fresh_data": true,
  "recommended_next_action": "run_investigation_refresh",
  "evidence_ids": ["ev_020", "ev_040"],
  "confidence": "medium"
}
```

---

## Final Memo Template

The final memo should answer the user directly and quickly.

### 1. Decision Summary
- Stock
- Current price
- Time horizon
- Decision: Buy / Watch / Pass
- Confidence: Low / Medium / High

### 2. Thesis
- Why this stock may be attractive
- What the market may be missing

### 3. Business and Financial Quality
- Business model
- Growth drivers
- Margin and cash flow quality
- Balance sheet strength

### 4. Valuation View
- Current valuation
- Base, bull, and bear ranges
- What assumptions are required for upside

### 5. Technical and Timing Context
- Trend
- Entry quality
- Key levels

### 6. Catalysts
- Near-term
- Medium-term

### 7. Risks
- Main reasons the thesis could fail
- What would invalidate the idea

### 8. Monitoring Checklist
- Metrics, events, or price levels to track

---

## Decision Framework

The final recommendation should not be a vague sentiment score. It should follow a simple and defensible rubric.

### Buy
Use when most of the following are true:
- Business quality is strong or improving
- Financial quality is healthy
- Valuation offers acceptable expected return
- Catalysts exist or long-term compounding is attractive
- Risks are understood and manageable

### Watch
Use when at least one important condition is missing:
- Great business but too expensive
- Attractive setup but low confidence in fundamentals
- Good long-term idea with poor near-term entry
- Catalyst exists but evidence is incomplete

### Pass
Use when the idea is currently unattractive:
- Weak business or deteriorating financials
- Excessive valuation with fragile assumptions
- High downside risk relative to upside
- Thesis depends on speculative or poorly sourced claims

---

## Source and Reliability Standards

The system should prefer primary and high-quality sources:
- Company filings
- Earnings transcripts
- Investor presentations
- Exchange or market data providers
- Reputable financial news sources

The system should always:
- Attach dates to time-sensitive claims
- Separate facts from inference
- Label stale data
- Expose unresolved uncertainty

The system should never:
- Invent numbers
- Make unsupported claims about revenue, margins, or catalysts
- Present old information as current

---

## Design Principles

- Structured outputs over free-form summaries
- Evidence before judgment
- Explicit uncertainty
- Separate data gathering from interpretation
- Separate business quality from valuation
- Technicals influence timing, not core intrinsic quality
- Decision support, not financial advice

---

## Future Extensions

- Thesis Tracker Agent
- Earnings Preview Agent
- Portfolio Construction Agent
- Position Sizing Agent
- Macro Regime Agent
- Alerting and Re-rating Agent

---

## Implementation Plan

The system should be built in phases so that each stage produces something usable and testable.

### Phase 1: Core Research Pipeline
Goal:
- Produce a reliable investigation workflow for a single stock

Build:
- Router / Planner
- Data / Source Verification
- Business Quality
- Financial Quality
- Valuation
- News / Catalyst
- Risk
- Synthesizer

Deliverables:
- Single-stock research memo
- Source-backed evidence packet
- Buy / Watch / Pass output
- Confidence and open-questions fields

Success criteria:
- Every material claim is tied to a source
- The system can analyze a stock end to end without manual intervention
- The final memo is useful enough to review before a real investment decision

### Phase 2: Discovery Engine
Goal:
- Surface investable candidates instead of only analyzing user-provided tickers

Build:
- Screener / Universe Agent
- Ranking logic
- Discovery prompt patterns by theme and style

Deliverables:
- Ranked candidate lists
- Discovery report with top picks and why they passed filters
- Sector or theme-level scan summaries

Success criteria:
- Discovery outputs are narrow, ranked, and explainable
- Results avoid generic, overbroad lists

### Phase 3: Comparison and Portfolio Context
Goal:
- Help users choose between similar ideas and understand fit within an existing portfolio

Build:
- Comparison mode
- Decision / Portfolio Fit Agent
- Optional portfolio ingestion layer

Deliverables:
- Side-by-side comparison memo
- Overlap and concentration warnings
- Best-fit ranking by objective

Success criteria:
- The system can explain why one stock is preferable to another for a specific use case

### Phase 4: Technical Timing and Monitoring
Goal:
- Improve entry timing and post-research tracking

Build:
- Technical Analysis Agent
- Monitoring checklist generator
- Thesis Tracker or alerting workflow

Deliverables:
- Entry context
- Thesis-monitoring dashboard or structured watchlist output
- Trigger-based alerts for re-rating events

Success criteria:
- The system can tell the user not just what to buy, but what to watch after research is complete

### Phase 5: Evaluation and Hardening
Goal:
- Make the system trustworthy enough for repeated use

Build:
- Golden test cases
- Output schema validation
- Source freshness validation
- Failure-mode logging

Deliverables:
- Test suite for representative stocks and query types
- Evaluation rubric for memo quality
- Error handling for stale or missing data

Success criteria:
- The system fails visibly when data quality is weak
- Results are consistent across repeated runs on the same inputs

---

## Suggested Technical Architecture

This is the simplest architecture that can work well early.

### 1. Orchestrator Layer
Responsibilities:
- Receive user request
- Build execution plan
- Run agents in sequence or parallel where possible
- Collect outputs into a final memo

Useful components:
- Agent runner
- Shared context object
- Retry and timeout handling
- Output schema validation

### 2. Data Layer
Responsibilities:
- Normalize price, fundamentals, filings, and news into a common schema
- Cache source responses
- Track freshness and source provenance

Useful components:
- Market data client
- Filings client
- News client
- Company metadata store
- Evidence store with timestamps

### 3. Agent Layer
Responsibilities:
- Transform structured inputs into analysis outputs
- Return evidence-backed judgments in a standard format

Useful components:
- Prompt templates
- Strict JSON output schemas
- Shared scoring rubric
- Confidence calibration rules

### 4. Presentation Layer
Responsibilities:
- Render memos, comparisons, and ranked screens
- Show sources, dates, and uncertainty clearly

Useful components:
- Research memo view
- Comparison table
- Watchlist and alert view
- Downloadable JSON or markdown outputs

---

## Recommended Data and Source Stack

The system should use a source hierarchy instead of treating all data equally.

### Tier 1: Primary Sources
Use these whenever possible for facts about the business, financials, guidance, and risks.

- SEC filings: 10-K, 10-Q, 8-K, DEF 14A
- Company investor relations pages
- Earnings releases
- Earnings call transcripts when sourced from a reliable provider
- Investor presentations

Best use cases:
- Business model
- Revenue segments
- Reported financial metrics
- Risk factors
- Management guidance

### Tier 2: Market and Financial Data Providers
Use these for prices, ratios, historical series, and screening inputs.

- Exchange data or reputable market-data APIs
- Financial statement APIs
- Historical price and volume data providers
- Analyst estimate and revision providers if available

Best use cases:
- Price action
- Relative strength
- Historical valuation ranges
- Financial trend normalization
- Screeners

### Tier 3: Reputable News Sources
Use these for catalysts, narrative shifts, and macro or sector context.

- Reuters
- Bloomberg
- Wall Street Journal
- Financial Times
- CNBC only for limited headline awareness, not primary thesis support

Best use cases:
- M&A
- Product launches
- Regulatory developments
- Management changes
- Sector sentiment shifts

### Tier 4: Derived or Secondary Research
Use these cautiously and label them clearly as interpretation, not fact.

- Sell-side summaries
- Independent research platforms
- Industry blogs
- Alternative data writeups

Best use cases:
- Framing debates
- Peer comparisons
- Scenario generation

Rules:
- Do not rely on secondary commentary when a primary source can answer the question
- If secondary sources disagree with filings or reported numbers, primary sources win unless a correction is documented

---

## Source Map by Agent

### Router / Planner Agent
Primary inputs:
- User query
- Stored user preferences
- Portfolio context if available

### Data / Source Verification Agent
Primary inputs:
- SEC filings
- IR pages
- Market data APIs
- News feeds

Must produce:
- `source_name`
- `source_type`
- `published_at`
- `retrieved_at`
- `claim_scope`

### Screener / Universe Agent
Best sources:
- Price and volume data provider
- Fundamentals API
- Estimates and revisions provider
- Sector and industry classification source

Needed fields:
- Market cap
- Revenue growth
- Margins
- Valuation multiples
- Relative strength
- Liquidity filters

### Business Quality Agent
Best sources:
- 10-K
- Investor presentation
- Earnings transcript
- Segment disclosures

Needed fields:
- Revenue segments
- Customer concentration
- Geographic mix
- Competitive positioning
- Management commentary

### Financial Quality Agent
Best sources:
- Reported financial statements
- Cash flow statements
- Footnotes
- Guidance history

Needed fields:
- Revenue
- Gross margin
- Operating margin
- Free cash flow
- Debt
- Cash
- Share count
- Stock-based compensation

### Valuation Agent
Best sources:
- Market data provider
- Financial statements
- Peer set mapping
- Historical multiples database

Needed fields:
- Enterprise value
- Earnings
- EBITDA
- Sales
- Free cash flow
- Historical multiple ranges

### Technical Analysis Agent
Best sources:
- Historical OHLCV data

Needed fields:
- Daily and weekly price history
- Volume
- Moving averages
- Relative performance vs benchmark

### News / Catalyst Agent
Best sources:
- Reputable news feeds
- Earnings releases
- 8-K filings
- Regulatory announcements

Needed fields:
- Event date
- Headline
- Summary
- Event type
- Expected impact

### Risk Agent
Best sources:
- Risk factors from filings
- Debt maturity disclosures
- News flow
- Competitive and macro context

Needed fields:
- Key operational risks
- Financial risks
- Regulatory risks
- Cyclical risks
- Thesis-breaker conditions

### Decision / Portfolio Fit Agent
Best sources:
- Aggregated outputs from all agents
- Portfolio holdings data if available

Needed fields:
- Sector exposure
- Position overlap
- Correlation or concentration proxies
- Time horizon and risk tolerance

---

## Minimum Schema for Evidence Tracking

Every important claim should map to evidence. A minimal evidence object could contain:

```json
{
  "claim": "Revenue grew 24% year over year in the most recent quarter.",
  "value": 24,
  "unit": "percent",
  "ticker": "NVDA",
  "as_of_date": "2026-02-15",
  "source_name": "NVIDIA Q4 FY2026 earnings release",
  "source_type": "company_filing_or_release",
  "source_url": "...",
  "retrieved_at": "2026-04-13T21:30:00-07:00",
  "confidence": "high"
}
```

This makes it easier to:
- Audit outputs
- Refresh stale claims
- Detect contradictions
- Reuse evidence across agents

---

## Evaluation Plan

The system needs evaluation beyond whether the prose sounds smart.

### 1. Research Quality Evaluation
Check:
- Factual accuracy
- Source coverage
- Freshness of claims
- Clarity of thesis
- Clarity of bear case

### 2. Decision Quality Evaluation
Check:
- Whether `Buy / Watch / Pass` follows the stated rubric
- Whether valuation conclusions are supported by assumptions
- Whether risk severity matches the final recommendation

### 3. Consistency Evaluation
Check:
- Same input produces similar conclusions across runs
- Agent disagreements are surfaced consistently
- Changes in source data cause sensible memo updates

### 4. Usefulness Evaluation
Check:
- Whether a user can act on the memo
- Whether the memo reduces follow-up questions
- Whether watchlist and monitoring suggestions are concrete

Example golden cases:
- High-quality compounder that is too expensive
- Cheap cyclical stock with deteriorating fundamentals
- Strong company with near-term regulatory risk
- Popular momentum stock with weak free cash flow quality

---

## Useful Additional Features To Build

These are likely more valuable than adding extra agents too early.

### 1. Research Memory
Store prior memos, thesis changes, and past evidence so the system can answer:
- What changed since last quarter?
- Has conviction improved or worsened?

### 2. Thesis Drift Tracker
Compare current evidence with prior thesis and flag:
- Broken assumptions
- New risks
- Re-acceleration or deterioration

### 3. Earnings Prep Mode
Before earnings, generate:
- What matters this quarter
- What metrics to watch
- Bull and bear interpretation framework

### 4. Post-Earnings Diff
After results, automatically summarize:
- Beats and misses
- Guidance changes
- Whether the thesis improved, weakened, or broke

### 5. Peer Radar
When analyzing one stock, automatically surface:
- Closest peers
- Better-valued alternatives
- Higher-quality alternatives

### 6. Position Sizing Assistant
Not to automate trading, but to frame:
- Starter position vs full position
- What level of confidence justifies more size
- How much uncertainty remains

### 7. Watchlist Builder
Convert `Watch` ideas into tracked setups with:
- Desired entry range
- Required catalysts
- Conditions for upgrade to `Buy`

### 8. Source Freshness Alerts
Warn when:
- A memo relies on outdated filings
- Prices moved enough to invalidate valuation logic
- A major event happened after the memo was generated

### 9. Portfolio Exposure Lens
Flag:
- Hidden concentration in a single theme
- Excess exposure to one macro driver
- Redundant positions across similar names

### 10. Explainability View
Show:
- Which agents drove the final decision
- Which claims were weak or uncertain
- What evidence would most change the recommendation

---

## Recommended Immediate Next Steps

If building this now, the most pragmatic order is:

1. Define JSON schemas for each agent output.
2. Define the shared evidence object and source metadata model.
3. Implement the single-stock investigation pipeline first.
4. Add memo rendering and source display before discovery mode.
5. Add the screener only after the investigation path is reliable.

This order reduces the risk of building a flashy but untrustworthy discovery engine on top of weak research plumbing.

---

## Project Positioning

"A multi-agent stock research and decision-support system that helps users discover, investigate, compare, and judge stocks through source-backed analysis of business quality, financial quality, valuation, catalysts, technical context, and downside risk."
