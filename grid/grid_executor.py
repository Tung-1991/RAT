# -*- coding: utf-8 -*-
"""GRID market-order executor."""

import MetaTrader5 as mt5

from .grid_config import GRID_CHILD_COMMENT


class GridExecutor:
    def __init__(self, connector=None, log_callback=None):
        self.connector = connector
        self.log_callback = log_callback

    def log(self, message: str, error: bool = False):
        if self.log_callback:
            self.log_callback(f"[GRID] {message}", error=error, target="grid")

    def place_grid_order(self, symbol, direction, lot_size, tp_price, grid_magic, level_id, session_id):
        if not self.connector or not getattr(self.connector, "_is_connected", False):
            return "GRID_FAIL|NO_CONNECTION"

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        comment = f"{GRID_CHILD_COMMENT}|{session_id}|L:{level_id}"
        result = self.connector.place_order(
            symbol=symbol,
            order_type=order_type,
            lot_size=lot_size,
            sl_price=0.0,
            tp_price=tp_price,
            magic_number=grid_magic,
            comment=comment,
        )
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            self.log(f"ORDER {direction} {symbol} #{result.order} lot={lot_size:.2f} tp={tp_price:.5f} level={level_id}")
            return f"SUCCESS|{result.order}"
        return "GRID_FAIL|MT5_ORDER_REJECTED"
