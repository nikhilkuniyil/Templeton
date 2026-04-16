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
    assert "What changed:" in captured.out


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


def test_cli_shell_supports_investigate_chat_and_history(monkeypatch, capsys, tmp_path) -> None:
    commands = iter(
        [
            "/memory",
            "look into ASML for a 5 year hold",
            "Why was this rated watch?",
            "/history",
            "/clear",
            "/memory",
            "/quit",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    exit_code = main(["shell", "--demo", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Templeton shell" in captured.out
    assert "Investor research terminal" in captured.out
    assert "Ask naturally:" in captured.out
    assert "Session memory:" in captured.out
    assert "Investigation: ASML" in captured.out or "Investigation (agentic): ASML" in captured.out
    assert "Prior research leans WATCH" in captured.out
    assert "History: ASML" in captured.out
    assert "Session context cleared." in captured.out


def test_cli_shell_requests_clarification_without_ticker(monkeypatch, capsys, tmp_path) -> None:
    commands = iter(
        [
            "what changed since last time",
            "/quit",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    exit_code = main(["shell", "--demo", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "I need a ticker to show thesis history or what changed." in captured.out


def test_cli_shell_debug_mode_shows_routing(monkeypatch, capsys, tmp_path) -> None:
    commands = iter(
        [
            "look into ASML for a 5 year hold",
            "/quit",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    exit_code = main(["shell", "--demo", "--display-mode", "debug", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[debug] intent=investigate_stock ticker=ASML refresh=False" in captured.out


def test_cli_defaults_to_shell_when_no_command_is_given(monkeypatch, capsys, tmp_path) -> None:
    commands = iter(["/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    exit_code = main(["--demo", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Templeton shell" in captured.out
    assert "- Data: demo dataset" in captured.out


def test_cli_shell_supports_workspace_flows(monkeypatch, capsys, tmp_path) -> None:
    commands = iter(
        [
            "look into ASML for a 5 year hold",
            "add this to my semis watchlist",
            "save a note that I only want to buy on a pullback",
            "show my semis watchlist",
            "I want more money into semis",
            "what am I missing before buying more into semis",
            "/memory",
            "/quit",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    exit_code = main(["shell", "--demo", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Added ASML to the semis watchlist." in captured.out
    assert "Saved note." in captured.out
    assert "Watchlist: semis" in captured.out
    assert "Added semis as a priority theme for new capital." in captured.out
    assert "Main blockers before buying more into semis:" in captured.out
    assert "Priority themes: semis" in captured.out


def test_cli_shell_help_matches_natural_language_session(monkeypatch, capsys, tmp_path) -> None:
    commands = iter(
        [
            "/help",
            "/quit",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    exit_code = main(["shell", "--demo", "--store-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Templeton help" in captured.out
    assert "Research and workspace tasks use natural language." in captured.out
    assert "/mode [default|verbose|debug]" in captured.out
    assert "Current session:" in captured.out
