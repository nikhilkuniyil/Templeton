# Dexter Parity And Differentiation Roadmap

## Why This Exists

Dexter is already a credible baseline for autonomous financial research. Its public repo shows a mature TypeScript/Bun CLI agent with dedicated `agent`, `tools`, `memory`, `evals`, and `gateway` modules, plus scratchpad logging and an evaluation workflow.

Templeton should not try to "also be a financial agent" in generic terms. It should:

1. Reach parity on the core workflow a user expects from Dexter.
2. Beat Dexter on evidence quality, research continuity, and investor usefulness.

This roadmap is ordered for quality first, not feature count first.

## Dexter Baseline

From Dexter's public repository and README, the baseline capability appears to be:

- interactive terminal UX
- autonomous task planning
- tool-based execution
- self-validation / iteration
- live financial data
- scratchpad logging for auditability
- evaluation suite with tracked runs
- memory module

Templeton already has a useful base, but it is not yet at that bar.

## Templeton Current State

Templeton currently has:

- a working Python CLI
- schema-validated agent orchestration
- live SEC filings, SEC company facts, Yahoo chart data, and Yahoo RSS headlines
- research agents for business, financial quality, valuation, technicals, news, risk, and decision synthesis
- conversational mode over prior outputs

Templeton is still weak in:

- section-aware filing parsing
- persistent memory and research history
- evaluation discipline
- self-critique / self-repair loops
- claim-level evidence traceability
- portfolio and monitoring workflows

## Build Order

### Phase 1: Dexter Parity On Core UX

Goal: make the CLI feel dependable and coherent for repeated daily use.

Deliverables:

- stable CLI command surface for `investigate`, `chat`, `compare`, `watchlist`, and `refresh`
- consistent output contracts for all agents
- explicit run IDs and saved run artifacts
- better failure handling for partial data outages

Acceptance criteria:

- a user can run the same command twice and understand what changed
- every run produces a readable final memo and a machine-readable artifact
- connector failures degrade gracefully instead of poisoning the whole run

### Phase 2: Scratchpad, Memory, And Auditability

Goal: match Dexter's debugging and run-history usefulness.

Deliverables:

- local run store, for example `.templeton/runs/<run_id>/`
- JSONL scratchpad of tool calls, intermediate agent outputs, and validation events
- saved evidence index per run
- memo history by ticker

Acceptance criteria:

- every conclusion can be traced back to sources, agent outputs, and tool calls
- the chat layer can answer from prior runs without forcing a full refresh
- users can inspect what changed between two runs on the same ticker

### Phase 3: Evaluation Harness

Goal: stop judging quality by spot checks.

Deliverables:

- curated benchmark set of 20 to 50 stock research tasks
- golden expectations for extraction quality, memo quality, and decision coherence
- per-agent evals for filings parsing, risk extraction, and valuation outputs
- end-to-end scorecard for answer quality, evidence quality, and freshness handling

Acceptance criteria:

- every meaningful change can be scored before and after
- regressions in business extraction or risk extraction are caught automatically
- Templeton can be compared against Dexter on the same prompts

### Phase 4: Self-Validation And Repair

Goal: reach parity with Dexter's self-checking behavior, but with stricter research standards.

Deliverables:

- post-run verifier agent that checks missing evidence, stale data, unsupported claims, and contradiction across agents
- retry or repair loop for incomplete or low-confidence outputs
- confidence downgrade rules when evidence is weak

Acceptance criteria:

- unsupported claims are surfaced before final output
- contradictory agent outputs are resolved or explicitly shown to the user
- low-quality runs fail honestly instead of sounding confident

### Phase 5: Stronger Data Layer

Goal: remove shallow or noisy upstream signals.

Deliverables:

- section-aware SEC parser for `Business`, `MD&A`, and `Risk Factors`
- cleaner mapping from company facts to financial metrics
- stronger news normalization and event clustering
- peer set generation for relative valuation

Acceptance criteria:

- business summaries come from the right filing sections
- risk items are specific and thesis-relevant rather than boilerplate
- valuation is not just a quote proxy

### Phase 6: Decision-Grade Research Memos

Goal: make outputs genuinely useful for an investor, not just technically impressive.

Deliverables:

- fixed memo structure: thesis, bull case, bear case, valuation, risks, catalysts, monitoring items, decision, confidence, invalidation triggers
- claim-level evidence references in the memo
- explicit "what changed since last run" block

Acceptance criteria:

- a user can read one memo and understand the case for and against owning the stock
- the final decision is tied to evidence, not generic language
- reruns show thesis drift instead of overwriting history

### Phase 7: Portfolio And Monitoring Workflows

Goal: move beyond one-off answers.

Deliverables:

- watchlist state
- thesis drift alerts
- earnings preview and post-earnings diff
- portfolio overlap and concentration checks

Acceptance criteria:

- the tool helps users maintain conviction over time
- users can see when a stock moved from `buy` to `watch` and why
- research compounds instead of restarting every time

## Where Templeton Should Beat Dexter

Templeton should try to win on these dimensions:

- better SEC section parsing
- stronger claim-to-evidence linking
- clearer investment memo structure
- thesis history and drift detection
- more explicit risk taxonomy and monitoring signals
- stricter honesty under uncertainty

Templeton does not need to beat Dexter by having more agents. It needs to beat Dexter by producing better research artifacts.

## Immediate Next Milestones

The next concrete milestones should be:

1. Add local run storage and scratchpad logging.
2. Add a benchmark suite with golden cases.
3. Replace heuristic filing scanning with section-aware parsing.
4. Add a verifier pass that rejects unsupported conclusions.
5. Add persistent ticker memo history and thesis-drift diffs.

## Definition Of Success

Templeton is "Dexter capability but better" when:

- it matches Dexter on basic CLI usability and live-research coverage
- it exceeds Dexter on evidence traceability and memo usefulness
- it has a measurable benchmark suite showing better extraction and research quality
- it gives investors better continuity over time, not just one better answer
