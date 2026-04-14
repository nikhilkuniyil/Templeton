from stock_researcher.cli import main


def test_cli_investigate_demo_outputs_agent_sections(capsys) -> None:
    exit_code = main(["investigate", "ASML", "--demo"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Investigation: ASML" in captured.out
    assert "[source_verification]" in captured.out
    assert "[business_quality]" in captured.out
    assert "[decision_portfolio_fit]" in captured.out
    assert "WATCH" in captured.out


def test_cli_chat_demo_refreshes_and_answers(capsys) -> None:
    exit_code = main(["chat", "ASML", "Why was this rated watch?", "--demo", "--refresh"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Prior research leans WATCH" in captured.out
