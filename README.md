# Templeton Stock Researcher

Templeton is a local command-line research and signal terminal for public equities. It combines evidence-aware company research, factor scoring, signal generation, historical return replay, and point-in-time portfolio simulation in one workflow.

The project is designed to be inspectable end to end: source documents flow into typed agent outputs, agent outputs become factor scores, factor scores become signals, and dated factor snapshots can be simulated with turnover, transaction costs, trade logs, and attribution.

## What it does

- Runs an investigation pipeline for a ticker: planning, source verification, business quality, financial quality, valuation, technicals, catalysts, risk, decision, verification, and final synthesis.
- Stores run artifacts and ticker history under `.templeton/` by default.
- Supports a natural-language shell with session memory, watchlists, notes, and simple portfolio context.
- Converts research outputs into transparent factor scores for cross-sectional ranking.
- Generates research-backed entry signals with sizing bands, diagnostics, and invalidation triggers.
- Replays top-ranked names as an equal-weight portfolio when market metadata includes monthly returns.
- Simulates point-in-time factor snapshots with transaction costs, turnover, trade events, and attribution.
- Works offline with built-in demo data for `ASML` and `NVDA`.
- Can call live-ish data connectors for SEC filings/company facts, Yahoo Finance news/price chart data, Financial Datasets, Tavily search, and optional LLM memo generation.

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
templeton signal ASML NVDA --demo
templeton backtest ASML NVDA --demo --top-n 2
templeton simulate --top-n 2 --cost-bps 10
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

`signal` turns the same research and factor outputs into a conservative entry label:

```bash
templeton signal ASML NVDA --demo
```

Signal labels:

- `BUY_ZONE`: quality, valuation, momentum, risk, and freshness are aligned enough for staged-entry research.
- `WATCH_FOR_PULLBACK`: quality/setup is interesting, but valuation or entry quality argues for patience.
- `AVOID_CHASING`: momentum may be strong, but the setup is extended or valuation is too demanding.
- `RISK_OFF`: risk or return regime is unfavorable.
- `INSUFFICIENT_DATA`: source freshness or price history is not adequate.

Each signal includes setup score, research stance, sizing band, return diagnostics, reasons, and invalidation triggers so the entry logic is explicit and auditable.

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

This replay mode is useful for comparing factor definitions, checking whether ranking output is measurable, and keeping qualitative research tied to portfolio-level metrics such as return, volatility, Sharpe, drawdown, and hit rate.

## Point-In-Time Simulation

`simulate` is the quant-trader-oriented path. It reads dated factor snapshots from CSV, ranks names at each rebalance date, forms an equal-weight top-N basket, applies transaction costs from turnover, and reports the equity-curve metrics.

```bash
templeton simulate --universe data/demo_signal_history.csv --top-n 2 --cost-bps 10
```

CSV columns:

```text
date,ticker,sector,quality,value,momentum,risk,catalyst,forward_return
```

Outputs include:

- gross and net period returns
- cumulative and annualized return
- volatility, Sharpe, max drawdown, and hit rate
- average turnover and total transaction cost
- trade events with buy/sell weight changes
- average factor exposure and score contribution by factor bucket

This path provides the core controls for a quant trading discussion: point-in-time inputs, next-period returns, turnover, costs, position changes, and attribution.

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
- `data/demo_signal_history.csv` is a small point-in-time factor dataset for `simulate`.
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

## Methodology Notes

- Research runs preserve source packets, agent outputs, final metadata, and optional LLM memos under `.templeton/`.
- Ranking and signal commands use transparent factor weights rather than hidden model weights.
- `backtest` uses the latest research-derived return metadata for quick ranking replay.
- `simulate` uses dated factor rows and forward returns for point-in-time evaluation.
- Local JSON storage keeps runs easy to inspect, diff, and reset during research iteration.
