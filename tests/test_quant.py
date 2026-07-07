import json

from stock_researcher.cli import main


def test_cli_rank_demo_outputs_factor_table(capsys, tmp_path) -> None:
    exit_code = main(["rank", "ASML", "NVDA", "--demo", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Factor ranking" in captured.out
    assert "Ticker  Score" in captured.out
    assert "NVDA" in captured.out
    assert "ASML" in captured.out
    assert "Weights: quality 30%" in captured.out


def test_cli_backtest_demo_outputs_metrics(capsys, tmp_path) -> None:
    exit_code = main(["backtest", "ASML", "NVDA", "--top-n", "2", "--demo", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Backtest replay" in captured.out
    assert "Method: single research snapshot" in captured.out
    assert "Cumulative return:" in captured.out
    assert "Sharpe:" in captured.out


def test_cli_signal_demo_outputs_research_signal(capsys, tmp_path) -> None:
    exit_code = main(["signal", "ASML", "NVDA", "--demo", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Research-backed signals" in captured.out
    assert "ASML:" in captured.out
    assert "Setup score:" in captured.out
    assert "Invalidation triggers:" in captured.out


def test_signal_json_exposes_diagnostics_and_sizing(capsys, tmp_path) -> None:
    exit_code = main(["signal", "ASML", "--demo", "--json", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    signal = payload["signals"][0]
    assert exit_code == 0
    assert signal["ticker"] == "ASML"
    assert signal["signal"] in {
        "BUY_ZONE",
        "WATCH_FOR_PULLBACK",
        "AVOID_CHASING",
        "RISK_OFF",
        "INSUFFICIENT_DATA",
    }
    assert "sizing" in signal
    assert "trailing_3m_return" in signal["diagnostics"]
    assert signal["invalidation_triggers"]


def test_cli_simulate_outputs_point_in_time_metrics(capsys) -> None:
    exit_code = main(["simulate", "--top-n", "2", "--cost-bps", "10"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Point-in-time signal simulation" in captured.out
    assert "Average turnover:" in captured.out
    assert "Factor exposure:" in captured.out
    assert "Trade events:" in captured.out


def test_simulate_json_includes_trades_and_attribution(capsys) -> None:
    exit_code = main(["simulate", "--top-n", "2", "--cost-bps", "10", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["periods"] == 6
    assert payload["trades"]
    assert payload["period_results"]
    assert payload["average_turnover"] > 0
    assert "momentum" in payload["factor_exposure"]
    assert "quality" in payload["score_contribution"]


def test_backtest_json_uses_top_ranked_return_series(capsys, tmp_path) -> None:
    exit_code = main(
        [
            "backtest",
            "ASML",
            "NVDA",
            "--top-n",
            "1",
            "--demo",
            "--json",
            "--store-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["backtest"]["periods"] == 12
    assert len(payload["backtest"]["tickers"]) == 1
    assert payload["backtest"]["cumulative_return"] != 0
