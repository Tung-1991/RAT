# -*- coding: utf-8 -*-
import os
from datetime import datetime


def account_dir():
    try:
        import core.storage_manager as storage_manager

        return storage_manager._active_account_dir
    except Exception:
        return "data"


def account_id():
    try:
        import core.storage_manager as storage_manager

        return storage_manager._active_account_id
    except Exception:
        return None


def advisor_root():
    return os.path.join(account_dir(), "advisor")


def archive_root():
    return os.path.join(advisor_root(), "archive")


def history_path():
    return os.path.join(advisor_root(), "advisor_history.xlsx")


def technical_settings_path():
    return os.path.join(advisor_root(), "technical_settings.json")


def user_context_path():
    return os.path.join(advisor_root(), "user_context.md")


def advisor_response_path():
    return os.path.join(advisor_root(), "advisor_response.md")


def ensure_advisor_dirs():
    os.makedirs(advisor_root(), exist_ok=True)
    return advisor_root()


def timestamp_name():
    return datetime.now().strftime("%Y%m%d_%H%M%S")
