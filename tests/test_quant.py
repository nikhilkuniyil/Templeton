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
