# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import Workbook, load_workbook

from ai_advisor import api_client, history, paths


def _patch_account_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "account_dir", lambda: str(tmp_path))
    monkeypatch.setattr(paths, "account_id", lambda: "TEST")
    paths.ensure_advisor_dirs()


def _new_history_workbook():
    wb = Workbook()
    wb.remove(wb.active)
    for name, headers in history.SHEETS.items():
        ws = wb.create_sheet(name)
        ws.append(headers)
    return wb


def _row(headers, **values):
    return [values.get(header, "") for header in headers]


def test_advisor_paths_split_history_and_export(monkeypatch, tmp_path):
    _patch_account_dir(monkeypatch, tmp_path)

    assert paths.history_path().replace("\\", "/").endswith("advisor_history.xlsx")
    assert paths.history_path().replace("\\", "/").endswith("history/advisor_history.xlsx")
    assert paths.export_path().replace("\\", "/").endswith("advisor/advisor_export.xlsx")
    assert paths.advisor_response_path().replace("\\", "/").endswith("advisor/advisor_response.md")
    assert paths.advisor_response_history_path().replace("\\", "/").endswith(".md")
    assert "/history/advisor_response_" in paths.advisor_response_history_path().replace("\\", "/")
    assert "/history/user_context_" in paths.user_context_history_path().replace("\\", "/")


def test_storage_csv_paths_live_in_account_history(monkeypatch, tmp_path):
    import core.storage_manager as storage_manager

    repo_root = Path.cwd()
    repo_artifact = repo_root / "data" / "TEST_ACCOUNT"
    if repo_artifact.exists():
        import shutil

        shutil.rmtree(repo_artifact)
    monkeypatch.chdir(tmp_path)
    try:
        storage_manager.set_active_account("TEST_ACCOUNT")

        assert storage_manager.MASTER_LOG_FILE.replace("\\", "/").endswith("data/TEST_ACCOUNT/history/trade_history_master.csv")
        assert storage_manager.HISTORY_FILE.replace("\\", "/").endswith("data/TEST_ACCOUNT/history/trade_history_log.csv")
        assert not repo_artifact.exists()
    finally:
        if repo_artifact.exists():
            import shutil

            shutil.rmtree(repo_artifact)


def test_advisor_folder_has_no_nested_dirs_after_export(monkeypatch, tmp_path):
    _patch_account_dir(monkeypatch, tmp_path)
    wb = _new_history_workbook()
    wb.save(paths.history_path())

    result = history.build_export_workbook(export_days=7)

    assert result["ok"] is True
    assert not [p for p in (tmp_path / "advisor").iterdir() if p.is_dir()]


def test_export_workbook_filters_closed_trades_without_touching_full_history(monkeypatch, tmp_path):
    _patch_account_dir(monkeypatch, tmp_path)
    now = datetime.now()
    wb = _new_history_workbook()

    closed_headers = history.SHEETS["closed_trades"]
    wb["closed_trades"].append(
        _row(
            closed_headers,
            **{
                "Recorded At": (now - timedelta(days=3)).isoformat(timespec="seconds"),
                "Ticket": "recent",
                "Symbol": "ETHUSD",
                "Exit Time": (now - timedelta(days=3)).isoformat(timespec="seconds"),
                "Profit": "10",
            },
        )
    )
    wb["closed_trades"].append(
        _row(
            closed_headers,
            **{
                "Recorded At": (now - timedelta(days=20)).isoformat(timespec="seconds"),
                "Ticket": "old",
                "Symbol": "ETHUSD",
                "Exit Time": (now - timedelta(days=20)).isoformat(timespec="seconds"),
                "Profit": "-5",
            },
        )
    )

    open_headers = history.SHEETS["open_trades"]
    wb["open_trades"].append(
        _row(open_headers, **{"Recorded At": now.isoformat(timespec="seconds"), "Ticket": "open-1"})
    )
    wb.save(paths.history_path())

    result_7d = history.build_export_workbook(export_days=7)
    assert result_7d["ok"] is True
    assert result_7d["closed_trades"] == 1
    export_wb = load_workbook(paths.export_path())
    assert [export_wb["closed_trades"].cell(r, 2).value for r in range(2, export_wb["closed_trades"].max_row + 1)] == ["recent"]
    assert export_wb["open_trades"].cell(2, 2).value == "open-1"

    result_30d = history.build_export_workbook(export_days=30)
    assert result_30d["closed_trades"] == 2
    export_wb = load_workbook(paths.export_path())
    assert [export_wb["closed_trades"].cell(r, 2).value for r in range(2, export_wb["closed_trades"].max_row + 1)] == ["recent", "old"]

    full_wb = load_workbook(paths.history_path())
    assert full_wb["closed_trades"].max_row == 3


def test_api_client_reads_advisor_export_not_full_history(monkeypatch, tmp_path):
    _patch_account_dir(monkeypatch, tmp_path)
    full_wb = _new_history_workbook()
    export_wb = _new_history_workbook()
    headers = history.SHEETS["closed_trades"]
    full_wb["closed_trades"].append(_row(headers, **{"Ticket": "full-only"}))
    export_wb["closed_trades"].append(_row(headers, **{"Ticket": "export-only"}))
    full_wb.save(paths.history_path())
    export_wb.save(paths.export_path())

    text = api_client._workbook_text(limit_rows=10)
    assert "export-only" in text
    assert "full-only" not in text


def test_api_client_saves_latest_response_and_history_snapshot(monkeypatch, tmp_path):
    _patch_account_dir(monkeypatch, tmp_path)
    export_wb = _new_history_workbook()
    export_wb.save(paths.export_path())
    paths.user_context_path().replace("\\", "/")
    with open(paths.technical_settings_path(), "w", encoding="utf-8") as f:
        f.write("{}")
    with open(paths.user_context_path(), "w", encoding="utf-8") as f:
        f.write("context")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"output_text":"advisor answer"}'

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(api_client.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    result = api_client.send_package_to_api()

    assert result["ok"] is True
    assert result["response"].replace("\\", "/").endswith("advisor/advisor_response.md")
    assert result["response_history"].replace("\\", "/").endswith(".md")
    assert "/history/advisor_response_" in result["response_history"].replace("\\", "/")
    assert "advisor_responses" not in result["response_history"].replace("\\", "/")
    with open(paths.advisor_response_path(), "r", encoding="utf-8") as f:
        assert f.read() == "advisor answer"
    with open(result["response_history"], "r", encoding="utf-8") as f:
        assert f.read() == "advisor answer"
