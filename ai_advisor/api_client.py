# -*- coding: utf-8 -*-
import json
import os
import urllib.request

from . import history, paths


DEFAULT_PROMPT = """You are an AI Advisor for RAT6. Analyze only the provided internal package.
Do not suggest automatic trading actions. Do not claim web research. Do not tell the bot to edit config.
Act like a trader/risk manager reviewing performance, risk, close reasons, modules, and config history."""


def _read_text(path, limit=120000):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read(limit)


def _workbook_text(limit_rows=80):
    try:
        from openpyxl import load_workbook

        if not os.path.exists(paths.history_path()):
            return ""
        wb = load_workbook(paths.history_path(), data_only=True)
        chunks = []
        for name in wb.sheetnames:
            ws = wb[name]
            chunks.append(f"\n## {name}")
            max_row = min(ws.max_row, limit_rows)
            for row in ws.iter_rows(min_row=1, max_row=max_row, values_only=True):
                chunks.append(" | ".join("" if v is None else str(v) for v in row))
        return "\n".join(chunks)
    except Exception as exc:
        return f"advisor_history.xlsx read warning: {exc}"


def send_package_to_api(prompt=None):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        msg = "OPENAI_API_KEY is not configured; API mode skipped."
        history.record_event("advisor_api_missing_key", msg, severity="WARN")
        return {"ok": False, "error": msg}

    model = os.environ.get("ADVISOR_API_MODEL", "gpt-5-mini")
    endpoint = os.environ.get("ADVISOR_API_URL", "https://api.openai.com/v1/responses")
    body_text = "\n\n".join(
        [
            "# technical_settings.json",
            _read_text(paths.technical_settings_path()),
            "# advisor_history.xlsx",
            _workbook_text(),
            "# user_context.md",
            _read_text(paths.user_context_path()),
        ]
    )
    payload = {
        "model": model,
        "instructions": prompt or DEFAULT_PROMPT,
        "input": body_text,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data.get("output_text")
        if not text:
            parts = []
            for item in data.get("output", []) or []:
                for content in item.get("content", []) or []:
                    if content.get("type") == "output_text":
                        parts.append(content.get("text", ""))
            text = "\n".join(parts).strip()
        if not text:
            text = json.dumps(data, ensure_ascii=False, indent=2)
        with open(paths.advisor_response_path(), "w", encoding="utf-8") as f:
            f.write(text)
        history.record_event("advisor_api_response_saved", "Advisor API response saved", payload={"model": model})
        return {"ok": True, "response": paths.advisor_response_path(), "model": model}
    except Exception as exc:
        history.record_event("advisor_api_error", str(exc), severity="ERROR", payload={"model": model, "endpoint": endpoint})
        return {"ok": False, "error": str(exc)}
