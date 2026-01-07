def calc_tp_sl_price(
    entry_price: float,
    leverage: float,
    tp_pnl_pct: float,
    sl_pnl_pct: float,
    is_long: bool,
):
    """
    tp_pnl_pct = 0.80 means +80% PnL on collateral for take profit
    sl_pnl_pct = 0.80 means -80% PnL on collateral for stop loss
    """

    tp_move_pct = tp_pnl_pct / leverage
    sl_move_pct = sl_pnl_pct / leverage

    if is_long:
        tp_price = entry_price * (1 + tp_move_pct)
        sl_price = entry_price * (1 - sl_move_pct)
    else:
        tp_price = entry_price * (1 - tp_move_pct)
        sl_price = entry_price * (1 + sl_move_pct)

    return tp_price, sl_price


def calc_pnl_pct(
    entry_price: float,
    current_price: float,
    leverage: float,
    is_long: bool,
):
    price_diff_pct = (
        (current_price - entry_price) / entry_price
        if is_long
        else (entry_price - current_price) / entry_price
    )

    return price_diff_pct * leverage
