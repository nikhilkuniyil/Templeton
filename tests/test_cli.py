from stock_researcher.cli import main


def test_cli_investigate_demo_outputs_agent_sections(capsys, tmp_path) -> None:
    exit_code = main(["investigate", "ASML", "--demo", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Investigation: ASML" in captured.out
    assert "Run artifacts:" in captured.out
    assert "[source_verification]" in captured.out
    assert "[business_quality]" in captured.out
    assert "[technical_analysis]" in captured.out
    assert "[decision_portfolio_fit]" in captured.out
    assert "[verifier]" in captured.out
    assert "WATCH" in captured.out


def test_cli_chat_demo_refreshes_and_answers(capsys, tmp_path) -> None:
    exit_code = main(
        ["chat", "ASML", "Why was this rated watch?", "--demo", "--refresh", "--store-dir", str(tmp_path)]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Prior research leans WATCH" in captured.out


def test_cli_chat_uses_saved_history_without_refresh(capsys, tmp_path) -> None:
    investigate_exit = main(["investigate", "ASML", "--demo", "--store-dir", str(tmp_path)])
    assert investigate_exit == 0

    exit_code = main(["chat", "ASML", "Why was this rated watch?", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Prior research leans WATCH" in captured.out


def test_cli_benchmark_outputs_summary(capsys, tmp_path) -> None:
    exit_code = main(["benchmark", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Benchmark suite:" in captured.out
    assert "Cases passed:" in captured.out
    assert "asml_long_term_demo [PASS]" in captured.out
