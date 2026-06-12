# -*- coding: utf-8 -*-
from types import SimpleNamespace

from telegram_notify import proposals
from telegram_notify.control import (
    TelegramControlService,
    format_positions,
    format_status,
    parse_edit_command,
    parse_order_command,
)


class FakeClient:
    def __init__(self):
        self.messages = []
        self.keyboards = []
        self.answers = []

    def send_message(self, chat_id, text, parse_mode=None):
        self.messages.append((chat_id, text))
        return {"ok": True}

    def send_message_with_keyboard(self, chat_id, text, keyboard=None):
        self.messages.append((chat_id, text))
        self.keyboards.append(keyboard)
        return {"ok": True}

    def answer_callback_query(self, callback_query_id, text=""):
        self.answers.append((callback_query_id, text))
        return {"ok": True}


class FakeUpdatesClient(FakeClient):
    def __init__(self, updates):
        super().__init__()
        self.updates = updates
        self.calls = []

    def get_updates(self, offset=None, timeout=15):
        self.calls.append((offset, timeout))
        return {"ok": True, "updates": list(self.updates)}


class FakeConnector:
    def __init__(self):
        self.positions = []
        self.closed = []
        self.close_ok = True

    def get_account_info(self):
        return {
            "login": 123,
            "balance": 1000,
            "equity": 1010,
            "margin": 100,
            "margin_free": 910,
        }

    def get_all_open_positions(self):
        return list(self.positions)

    def close_position(self, pos, comment=""):
        self.closed.append((pos.ticket, comment))
        return SimpleNamespace(retcode=10009) if self.close_ok else None


def _pos(ticket=1, symbol="ETHUSD", type=0, volume=0.1, profit=5.0, comment="[BOT]_AUTO_ENTRY", magic=11):
    return SimpleNamespace(
        ticket=ticket,
        symbol=symbol,
        type=type,
        volume=volume,
        price_open=2000,
        profit=profit,
        swap=0.0,
        commission=0.0,
        sl=1980,
        tp=2040,
        comment=comment,
        magic=magic,
    )


def _service(connector=None):
    connector = connector or FakeConnector()
    toggles = []
    executions = []
    service = TelegramControlService(
        connector=connector,
        get_state_cb=lambda: {"bot_pnl_today": 3.0, "bot_trades_today": 2, "manual_pnl_today": -1.0, "manual_trades_today": 1},
        get_bot_enabled_cb=lambda: bool(toggles[-1]) if toggles else False,
        set_bot_enabled_cb=lambda enabled, reason="": toggles.append(enabled),
        get_brain_status_cb=lambda: "ONLINE",
        get_active_symbols_cb=lambda: ["ETHUSD"],
        execute_order_cb=lambda symbol, side, lot, sl, tp: executions.append((symbol, side, lot, sl, tp)) or "SUCCESS|777",
    )
    return service, toggles, executions


def test_format_status_includes_account_and_positions():
    pos = _pos()
    text = format_status(
        {"login": 123, "balance": 1000, "equity": 1010, "margin": 100, "margin_free": 910},
        {"bot_pnl_today": 3, "bot_trades_today": 2, "manual_pnl_today": -1, "manual_trades_today": 1},
        [pos],
        False,
        brain_status="ONLINE",
        active_symbols=["ETHUSD"],
        magics={"bot_magic": 11},
    )
    assert "Login: 123" in text
    assert "Bot: OFF" in text
    assert "#1 BOT ETHUSD BUY" in text


def test_format_positions_empty():
    assert format_positions([]) == "Open positions: 0"


def test_control_ignores_unauthorized_user():
    service, _toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": ""}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 2}, "text": "/status"}},
    )
    assert client.messages[-1][1] == "Unauthorized."


def test_control_status_command_sends_dashboard():
    connector = FakeConnector()
    connector.positions = [_pos()]
    service, _toggles, _executions = _service(connector)
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 2}, "text": "/status"}},
    )
    assert "RAT-control status" in client.messages[-1][1]
    assert client.keyboards[-1]


def test_control_primes_offset_and_skips_old_backlog():
    service, _toggles, _executions = _service()
    client = FakeUpdatesClient(
        [
            {"update_id": 40, "channel_post": {"chat": {"id": "-1003941549878"}, "text": "/status"}},
            {"update_id": 41, "channel_post": {"chat": {"id": "-1003941549878"}, "text": "/positions"}},
        ]
    )
    result = service._prime_offset(client)
    assert result == {"ok": True, "skipped": 2}
    assert service.offset == 42
    assert service.offset_primed is True
    assert client.messages == []
    assert client.calls == [(-1, 0)]


def test_control_channel_post_status_sends_dashboard():
    connector = FakeConnector()
    connector.positions = [_pos()]
    service, _toggles, _executions = _service(connector)
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"channel_post": {"chat": {"id": "-1003941549878"}, "text": "/status"}},
    )
    assert "RAT-control status" in client.messages[-1][1]
    assert client.keyboards == []


def test_control_channel_post_blocks_text_toggle():
    service, toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"channel_post": {"chat": {"id": "-1003941549878"}, "text": "/bot_off"}},
    )
    assert toggles == []
    assert "Bot OFF button" in client.messages[-1][1]


def test_control_channel_post_order_creates_pending(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    service, _toggles, executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": ""}
    service.process_update(
        client,
        settings,
        {"channel_post": {"chat": {"id": "-1003941549878"}, "text": "/order ETHUSD BUY lot=0.03 sl=1980 tp=2050"}},
    )
    assert executions == []
    saved = list(proposals.load_proposals().values())[0]
    assert saved["created_by"] == 0
    assert saved["created_by_label"] == "CHANNEL"
    assert saved["status"] == "PENDING"
    assert "Owner approve required" in client.messages[-1][1]


def test_control_channel_post_edit_sets_channel_label(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(0, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050}, user_label="CHANNEL")
    service, _toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": ""}
    service.process_update(
        client,
        settings,
        {"channel_post": {"chat": {"id": "-1003941549878"}, "text": f"/edit {proposal['order_id']} side=SELL lot=0.02"}},
    )
    updated = proposals.get_proposal(proposal["order_id"])
    assert updated["side"] == "SELL"
    assert updated["updated_by"] == 0
    assert updated["updated_by_label"] == "CHANNEL"


def test_control_channel_post_blocks_text_approve_cancel_close(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(0, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050}, user_label="CHANNEL")
    service, _toggles, executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": ""}
    for text, expected in (
        (f"/approve {proposal['order_id']}", "Approve button"),
        (f"/cancel {proposal['order_id']}", "Cancel button"),
        ("/close 88", "Close #ticket button"),
    ):
        service.process_update(
            client,
            settings,
            {"channel_post": {"chat": {"id": "-1003941549878"}, "text": text}},
        )
        assert expected in client.messages[-1][1]
    assert executions == []
    assert proposals.get_proposal(proposal["order_id"])["status"] == "PENDING"


def test_channel_owner_callback_approves_pending(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(0, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050}, user_label="CHANNEL")
    service, _toggles, executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": ""}
    service.process_update(
        client,
        settings,
        {
            "callback_query": {
                "id": "cb1",
                "from": {"id": 1},
                "message": {"chat": {"id": "-1003941549878", "type": "channel"}},
                "data": f"ord:approve:{proposal['order_id']}",
            }
        },
    )
    assert executions == [("ETHUSD", "BUY", 0.03, 1980.0, 2050.0)]
    assert proposals.get_proposal(proposal["order_id"])["status"] == "EXECUTED"


def test_channel_non_owner_callback_approve_is_denied(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(0, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050}, user_label="CHANNEL")
    service, _toggles, executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": ""}
    service.process_update(
        client,
        settings,
        {
            "callback_query": {
                "id": "cb2",
                "from": {"id": 2},
                "message": {"chat": {"id": "-1003941549878", "type": "channel"}},
                "data": f"ord:approve:{proposal['order_id']}",
            }
        },
    )
    assert executions == []
    assert proposals.get_proposal(proposal["order_id"])["status"] == "PENDING"
    assert "approve" in client.messages[-1][1]


def test_channel_non_owner_callback_can_cancel_pending(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(0, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050}, user_label="CHANNEL")
    service, _toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": ""}
    service.process_update(
        client,
        settings,
        {
            "callback_query": {
                "id": "cb3",
                "from": {"id": 2},
                "message": {"chat": {"id": "-1003941549878", "type": "channel"}},
                "data": f"ord:cancel:{proposal['order_id']}",
            }
        },
    )
    assert proposals.get_proposal(proposal["order_id"])["status"] == "CANCELLED"


def test_channel_owner_callbacks_toggle_and_close(monkeypatch, tmp_path):
    connector = FakeConnector()
    connector.positions = [_pos(ticket=88)]
    service, toggles, _executions = _service(connector)
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": ""}
    service.process_update(
        client,
        settings,
        {
            "callback_query": {
                "id": "cb5",
                "from": {"id": 2},
                "message": {"chat": {"id": "-1003941549878", "type": "channel"}},
                "data": "ctl:bot_off",
            }
        },
    )
    assert toggles == []
    service.process_update(
        client,
        settings,
        {
            "callback_query": {
                "id": "cb6",
                "from": {"id": 1},
                "message": {"chat": {"id": "-1003941549878", "type": "channel"}},
                "data": "ctl:bot_off",
            }
        },
    )
    assert toggles == [False]
    service.process_update(
        client,
        settings,
        {
            "callback_query": {
                "id": "cb7",
                "from": {"id": 1},
                "message": {"chat": {"id": "-1003941549878", "type": "channel"}},
                "data": "ctl:close:88",
            }
        },
    )
    assert connector.closed == [(88, "telegram_control_close")]


def test_control_bot_toggle_command():
    service, toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 1}, "text": "/bot_on"}},
    )
    assert toggles == [True]
    assert "Bot is now ON" in client.messages[-1][1]


def test_operator_bot_toggle_is_denied():
    service, toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 2}, "text": "/bot_on"}},
    )
    assert toggles == []
    assert "Owner only" in client.messages[-1][1]


def test_control_close_ticket_refetches_position():
    connector = FakeConnector()
    connector.positions = [_pos(ticket=88)]
    service, _toggles, _executions = _service(connector)
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 1}, "text": "/close 88"}},
    )
    assert connector.closed == [(88, "telegram_control_close")]
    assert "Close sent" in client.messages[-1][1]


def test_control_close_missing_ticket():
    connector = FakeConnector()
    service, _toggles, _executions = _service(connector)
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 1}, "text": "/close 88"}},
    )
    assert "not open" in client.messages[-1][1]


def test_parse_order_command_accepts_five_fields():
    parsed = parse_order_command("/order ETHUSD BUY lot=0.03 sl=1980 tp=2050")
    assert parsed == {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980.0, "tp": 2050.0}


def test_parse_order_rejects_unknown_field():
    try:
        parse_order_command("/order ETHUSD BUY lot=0.03 sl=1980 tp=2050 note=x")
    except ValueError as exc:
        assert "Unsupported field" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_edit_command_accepts_partial_five_fields():
    order_id, updates = parse_edit_command("/edit TG1 side=SELL lot=0.02")
    assert order_id == "TG1"
    assert updates == {"side": "SELL", "lot": 0.02}


def test_operator_order_creates_pending(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    service, _toggles, executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 2}, "text": "/order ETHUSD BUY lot=0.03 sl=1980 tp=2050"}},
    )
    pending = proposals.pending_proposals()
    assert len(pending) == 1
    assert pending[0]["status"] == "PENDING"
    assert executions == []
    assert "Owner approve required" in client.messages[-1][1]


def test_owner_order_executes_immediately(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    service, _toggles, executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 1}, "text": "/order ETHUSD BUY lot=0.03 sl=1980 tp=2050"}},
    )
    assert executions == [("ETHUSD", "BUY", 0.03, 1980.0, 2050.0)]
    saved = list(proposals.load_proposals().values())[0]
    assert saved["status"] == "EXECUTED"
    assert saved["ticket"] == "777"


def test_operator_approve_is_denied(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(2, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050})
    service, _toggles, executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 2}, "text": f"/approve {proposal['order_id']}"}},
    )
    assert executions == []
    assert "thiếu quyền" in client.messages[-1][1]


def test_owner_approve_executes_pending(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(2, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050})
    service, _toggles, executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 1}, "text": f"/approve {proposal['order_id']}"}},
    )
    assert executions == [("ETHUSD", "BUY", 0.03, 1980.0, 2050.0)]
    assert proposals.get_proposal(proposal["order_id"])["status"] == "EXECUTED"


def test_operator_edit_pending(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(2, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050})
    service, _toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 2}, "text": f"/edit {proposal['order_id']} side=SELL lot=0.02 sl=2070 tp=2000"}},
    )
    updated = proposals.get_proposal(proposal["order_id"])
    assert updated["side"] == "SELL"
    assert updated["lot"] == 0.02


def test_owner_cancel_pending(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(2, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050})
    service, _toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 1}, "text": f"/cancel {proposal['order_id']}"}},
    )
    assert proposals.get_proposal(proposal["order_id"])["status"] == "CANCELLED"


def test_operator_cancel_is_denied(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(2, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050})
    service, _toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {"message": {"chat": {"id": "-1003941549878"}, "from": {"id": 2}, "text": f"/cancel {proposal['order_id']}"}},
    )
    assert proposals.get_proposal(proposal["order_id"])["status"] == "PENDING"
    assert "Owner only" in client.messages[-1][1]


def test_operator_cancel_callback_is_denied(monkeypatch, tmp_path):
    monkeypatch.setattr(proposals, "account_dir", lambda: str(tmp_path))
    proposal = proposals.create_proposal(2, {"symbol": "ETHUSD", "side": "BUY", "lot": 0.03, "sl": 1980, "tp": 2050})
    service, _toggles, _executions = _service()
    client = FakeClient()
    settings = {"control_chat_id": "1003941549878", "owner_user_id": "1", "operator_user_ids": "2"}
    service.process_update(
        client,
        settings,
        {
            "callback_query": {
                "id": "cb1",
                "from": {"id": 2},
                "message": {"chat": {"id": "-1003941549878"}},
                "data": f"ord:cancel:{proposal['order_id']}",
            }
        },
    )
    assert proposals.get_proposal(proposal["order_id"])["status"] == "PENDING"
    assert "Owner only" in client.messages[-1][1]
