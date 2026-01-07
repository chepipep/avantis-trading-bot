import config

async def place_limit_order(
    client,
    trader,
    pair_index,
    price,
    is_long,
    tp,
    sl
):
    side = "LONG" if is_long else "SHORT"

    if config.DRY_RUN:
        print(f"[DRY-RUN] {side} @ {price} | TP={tp} SL={sl}")
        return

    # Real TradeInput implementation
    # (handled by trader.py)
