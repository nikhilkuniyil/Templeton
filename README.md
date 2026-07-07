# Templeton Stock Researcher

Templeton is a local command-line research assistant for public equities. It runs a fixed set of evidence-aware agents over filing, market, and news inputs, saves the output to disk, and lets you keep asking follow-up questions against the latest saved research.

The project is intentionally small: no service, no database, and no background workers. It is useful as a local research workflow, a test bed for agent orchestration, or a starting point for plugging in better data providers.

## What it does

- Runs an investigation pipeline for a ticker: planning, source verification, business quality, financial quality, valuation, technicals, catalysts, risk, decision, verification, and final synthesis.
- Stores run artifacts and ticker history under `.templeton/` by default.
- Supports a natural-language shell with session memory, watchlists, notes, and simple portfolio context.
- Converts research outputs into transparent factor scores for cross-sectional ranking.
- Replays top-ranked names as an equal-weight portfolio when market metadata includes monthly returns.
- Works offline with built-in demo data for `ASML` and `NVDA`.
- Can call live-ish data connectors for SEC filings/company facts, Yahoo Finance news/price chart data, Financial Datasets, Tavily search, and optional LLM memo generation.

This is research support software, not investment advice. Treat outputs as a checklist and audit trail, not a trading signal.

## Quick Start

Use Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

Run a demo investigation:

```bash
templeton investigate ASML --demo
```

Start the interactive shell:

```bash
templeton --demo
```

You can also use the checked-in wrapper if you do not want to install the console script:

```bash
./templeton investigate NVDA --demo
```

## Common Commands

```bash
templeton investigate ASML --demo
templeton investigate NVDA --demo --json
templeton chat ASML "Why was this rated watch?" --demo --refresh
templeton rank ASML NVDA --demo
templeton backtest ASML NVDA --demo --top-n 2
templeton benchmark
templeton shell --demo
```

Inside the shell, the intended flow is natural language:

```text
look into ASML for a 5 year hold
why was this rated watch?
add this to my semis watchlist
save a note that I only want to buy on a pullback
what changed since last time?
```

Shell controls:

```text
/help
/memory
/history [TICKER] [limit]
/model [provider] [model]
/mode [default|verbose|debug]
/rules
/clear
/quit
```

## Data Modes

`--demo` uses deterministic sample connector data for `ASML` and `NVDA`. This is the best mode for tests, demos, and working on the agent pipeline.

`--live-filings` uses SEC filings and SEC company facts where available, plus Yahoo Finance news. Set a real SEC user agent when doing repeated runs:

```bash
templeton investigate ASML --live-filings --sec-user-agent "YourName/0.1 your.email@example.com"
```

`--financial-datasets` switches structured market data to Financial Datasets. It expects:

```bash
export FINANCIAL_DATASETS_API_KEY="..."
```

`--tavily` adds Tavily web search to the news layer. It expects:

```bash
export TAVILY_API_KEY="..."
```

Without one of these data flags, the shell can still answer from saved workspace/history, but fresh investigations will have limited source material.

## Ranking and Backtests

`rank` runs the normal investigation pipeline for each ticker, then maps the agent outputs into five visible factor buckets:

```text
quality 30%
value 20%
momentum 20%
risk 20%
catalyst 10%
```

Example:

```bash
templeton rank ASML NVDA --demo
```

`backtest` uses the same ranking and replays the top names as an equal-weight basket over `monthly_returns` from market-data metadata. Demo data ships with a small synthetic series; live SEC/Yahoo and Financial Datasets runs derive approximate monthly returns from daily closes.

```bash
templeton backtest ASML NVDA --demo --top-n 2
templeton backtest ASML NVDA --live-filings --top-n 2
templeton backtest ASML NVDA --financial-datasets --top-n 2
```

Historical price flow:

- `--live-filings` gets company facts from SEC and daily chart closes from Yahoo Finance, then converts roughly 21 trading-day windows into monthly returns.
- `--financial-datasets` gets daily prices from Financial Datasets and uses the same return derivation.
- `--demo` uses bundled synthetic returns so the ranking and replay workflow works offline.

This is intentionally a lightweight research sanity check, not a full point-in-time backtester. It is useful for comparing factor definitions, seeing whether ranking output is measurable, and keeping qualitative research tied to portfolio-level metrics such as return, volatility, Sharpe, drawdown, and hit rate.

## LLM Memos

The deterministic agent pipeline does not require an LLM. Add `--llm` when you want a provider model to rewrite the final memo or answer a chat question from saved research.

Supported providers:

```bash
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export GEMINI_API_KEY="..."
```

Examples:

```bash
templeton investigate ASML --demo --llm --llm-provider openai
templeton chat ASML "What changed?" --llm --llm-provider anthropic
templeton shell --demo --llm --agentic
```

The `--agentic` flag uses an LLM manager loop to choose and run agents before finalizing. It requires `--llm`.

## Files and Storage

- `stock_researcher/` contains the CLI, agents, connectors, orchestration, workspace store, and LLM adapters.
- `schemas/` contains the JSON-schema-like contracts used by runtime validation.
- `benchmarks/templeton_cases.json` defines the local benchmark suite.
- `tests/` covers the CLI, orchestration, connectors, benchmarks, conversation flow, and workspace features.
- `.templeton/` is local run/workspace state and is intentionally ignored by git.

Run artifacts include source packets, agent outputs, final run metadata, and optional LLM chat/memo files. Delete `.templeton/` if you want to reset local state.

## Development Notes

Run tests before changing agent behavior:

```bash
python -m pytest
```

The benchmark suite is a quick behavioral smoke test:

```bash
templeton benchmark
```

When adding a new agent output shape, update the matching schema in `schemas/` and add at least one focused test. The runtime validator is deliberately small and only implements the subset of JSON Schema this project uses.

## Current Limits

- Live data extraction is heuristic. SEC filing parsing aims to produce useful metadata, not a full filing analysis.
- Yahoo and Tavily results are treated as catalyst context, not primary evidence.
- Demo data is synthetic and only covers `ASML` and `NVDA`.
- Backtests are single-snapshot replays unless you provide point-in-time historical metadata.
- The project stores local JSON files rather than using a database, which keeps setup simple but is not designed for multi-user concurrency.
