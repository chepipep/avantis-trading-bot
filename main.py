import asyncio
import random
import time
from datetime import datetime, timedelta, timezone
import config
from price import get_btc_price, get_pair_price
from trader import AvantisTrader
from strategy import calc_tp_sl_price


# MSK = UTC+3
MSK = timezone(timedelta(hours=3))


def get_msk_time() -> datetime:
    """Get current time in MSK timezone."""
    return datetime.now(MSK)


def is_trading_hours() -> bool:
    """
    Check if current time is within trading hours.
    Supports overnight trading (e.g., 13:00 - 04:00).
    """
    now = get_msk_time()
    current_minutes = now.hour * 60 + now.minute

    # Apply variance
    variance = random.randint(-config.TRADING_HOURS_VARIANCE, config.TRADING_HOURS_VARIANCE)

    start_minutes = config.TRADING_START_HOUR * 60 + variance
    end_minutes = config.TRADING_END_HOUR * 60 + variance

    # Clamp to valid range
    start_minutes = max(0, min(start_minutes, 1439))
    end_minutes = max(0, min(end_minutes, 1440))

    # Handle overnight trading (e.g., 13:00 - 04:00)
    if config.TRADING_END_HOUR <= config.TRADING_START_HOUR:
        # Overnight: valid if after start OR before end
        return current_minutes >= start_minutes or current_minutes < end_minutes
    else:
        # Same day: valid if between start and end
        return start_minutes <= current_minutes < end_minutes


def get_random_offset() -> float:
    """
    Get random offset factor for both positions.
    Random value between MIN and MAX.
    """
    return random.uniform(config.ENTRY_OFFSET_MIN, config.ENTRY_OFFSET_MAX)


def get_reposition_threshold() -> float:
    """
    Get reposition threshold with random variance.
    """
    base = config.REPOSITION_THRESHOLD_PCT
    variance = random.uniform(-config.REPOSITION_RANDOM, config.REPOSITION_RANDOM)
    return base + variance


def get_check_interval() -> float:
    """Get random check interval between MIN and MAX."""
    return random.uniform(config.CHECK_INTERVAL_MIN, config.CHECK_INTERVAL_MAX)


def vary_amount(amount: float) -> float:
    """Vary amount and round to step."""
    variance = getattr(config, 'DEPOSIT_VARIANCE', 0.05)
    step = getattr(config, 'DEPOSIT_STEP', 0.5)
    factor = 1 + random.uniform(-variance, variance)
    varied = amount * factor
    return round(varied / step) * step


async def wait_for_trading_hours():
    """Wait until trading hours start."""
    while not is_trading_hours():
        now = get_msk_time()
        print(f"[{now.strftime('%H:%M:%S')} MSK] Outside trading hours. Waiting...")
        await asyncio.sleep(60)  # Check every minute


async def main():
    print("=" * 50)
    print("DELTA-NEUTRAL BOT (v3)")
    print("=" * 50)
    print(f"Mode: {'DRY RUN' if config.DRY_RUN else 'LIVE'}")
    print(f"Margin: {config.POSITION_SIZE_USDC} USDC")
    print(f"Leverage: {config.LEVERAGE}x")
    print(f"Entry Offset: {config.ENTRY_OFFSET_MIN*100:.2f}% - {config.ENTRY_OFFSET_MAX*100:.2f}%")
    print(f"Reposition: {config.REPOSITION_THRESHOLD_PCT*100:.1f}% (±{config.REPOSITION_RANDOM*100:.1f}%)")
    print(f"Check Interval: {config.CHECK_INTERVAL_MIN}-{config.CHECK_INTERVAL_MAX}s")
    print(f"Trading Hours: {config.TRADING_START_HOUR}:00 - {config.TRADING_END_HOUR % 24}:00 MSK (±{config.TRADING_HOURS_VARIANCE}min)")
    print("-" * 50)

    trader = AvantisTrader(config.RPC_URL, config.PRIVATE_KEY)

    # Approve once
    if not config.DRY_RUN:
        await trader.check_and_approve_usdc(config.POSITION_SIZE_USDC * 2)

    cycle = 0
    while True:
        # Wait for trading hours
        await wait_for_trading_hours()

        # Check if we already have pending orders
        if not config.DRY_RUN:
            trades, pending = await trader.get_open_trades()
            if len(pending) > 0:
                now = get_msk_time()
                print(f"[{now.strftime('%H:%M:%S')}] Found {len(pending)} pending orders. Waiting...")

                # Wait until orders are filled or cancelled
                while len(pending) > 0:
                    if not is_trading_hours():
                        break
                    await asyncio.sleep(get_check_interval())
                    trades, pending = await trader.get_open_trades()

                # If positions opened, wait for TP/SL
                if len(trades) >= 2:
                    print(f"Positions opened! Waiting for TP/SL...")
                    while len(trades) > 0:
                        if not is_trading_hours():
                            break
                        await asyncio.sleep(get_check_interval())
                        trades, _ = await trader.get_open_trades()
                    print("All positions closed!")

                continue  # Start new cycle

        cycle += 1
        now = get_msk_time()
        print(f"\n{'='*50}")
        print(f"CYCLE {cycle} | {now.strftime('%H:%M:%S')} MSK")
        print("=" * 50)

        # Get anchor price for selected pair
        anchor_price = await get_pair_price(config.PAIR_NAME)
        print(f"{config.PAIR_NAME} price: ${anchor_price:.2f}")

        # Get SAME random offset for both positions
        offset = get_random_offset()

        # Randomly choose direction: ABOVE or BELOW current price
        direction = random.choice(["ABOVE", "BELOW"])

        if direction == "ABOVE":
            entry_price = anchor_price * (1 + offset)
        else:
            entry_price = anchor_price * (1 - offset)

        print(f"Direction: {direction} | Offset: {offset*100:.3f}%")
        print(f"Entry price: ${entry_price:.2f} (both LONG and SHORT)")

        # Calculate TP/SL - both positions at SAME entry price
        long_tp, long_sl = calc_tp_sl_price(entry_price, config.LEVERAGE, config.TAKE_PROFIT_PNL, config.STOP_LOSS_PNL, True)
        short_tp, short_sl = calc_tp_sl_price(entry_price, config.LEVERAGE, config.TAKE_PROFIT_PNL, config.STOP_LOSS_PNL, False)

        collateral = vary_amount(config.POSITION_SIZE_USDC)

        # Place 2 limit orders
        print(f"\nPlacing 2 limit orders (collateral: {collateral} USDC)...")

        await trader.place_limit_order(
            pair_index=config.PAIR_INDEX,
            is_long=True,
            collateral=collateral,
            leverage=config.LEVERAGE,
            limit_price=entry_price,
            tp_price=long_tp,
            sl_price=long_sl,
            direction=direction,
            dry_run=config.DRY_RUN
        )

        if not config.DRY_RUN:
            await asyncio.sleep(random.uniform(2, 4))

        await trader.place_limit_order(
            pair_index=config.PAIR_INDEX,
            is_long=False,
            collateral=collateral,
            leverage=config.LEVERAGE,
            limit_price=entry_price,
            tp_price=short_tp,
            sl_price=short_sl,
            direction=direction,
            dry_run=config.DRY_RUN
        )

        print("Orders placed. Monitoring...")

        # Get reposition threshold for this cycle (same for both directions)
        reposition_threshold = get_reposition_threshold()
        print(f"Reposition threshold: {reposition_threshold*100:.2f}%")

        # Monitor loop
        check_count = 0
        last_status_time = 0

        while True:
            # Check trading hours
            if not is_trading_hours():
                now = get_msk_time()
                print(f"\n[{now.strftime('%H:%M:%S')} MSK] Trading hours ended. Cancelling orders...")

                if not config.DRY_RUN:
                    _, pending = await trader.get_open_trades()
                    for order in pending:
                        try:
                            await trader.cancel_order(
                                pair_index=order.pairIndex,
                                trade_index=order.index,
                                dry_run=False
                            )
                            await asyncio.sleep(random.uniform(1, 2))
                        except Exception as e:
                            print(f"Cancel error: {e}")

                print("Waiting for next trading session...")
                break

            # Wait random interval
            interval = get_check_interval()
            await asyncio.sleep(interval)

            current_price = await get_btc_price()
            price_diff = abs(current_price - anchor_price) / anchor_price
            check_count += 1

            # Show status only every 60 seconds
            current_time = time.time()
            show_status = (current_time - last_status_time) >= 60

            if config.DRY_RUN:
                if show_status:
                    now = get_msk_time()
                    print(f"[{now.strftime('%H:%M:%S')}] ${current_price:.2f} | Diff: {price_diff*100:.2f}%")
                    last_status_time = current_time

                if price_diff > reposition_threshold:
                    print(f"[DRY-RUN] Price moved {price_diff*100:.2f}% - repositioning")
                    break

                # Simulate order fill
                if direction == "BELOW" and current_price <= entry_price:
                    print(f"[DRY-RUN] Orders filled at ${entry_price:.2f}")
                    break
                elif direction == "ABOVE" and current_price >= entry_price:
                    print(f"[DRY-RUN] Orders filled at ${entry_price:.2f}")
                    break

            else:
                # Live trading
                trades, pending = await trader.get_open_trades()

                if show_status:
                    now = get_msk_time()
                    print(f"[{now.strftime('%H:%M:%S')}] ${current_price:.2f} | Diff: {price_diff*100:.2f}% | Pos: {len(trades)} | Pend: {len(pending)}")
                    last_status_time = current_time

                # If positions opened - wait for TP/SL
                if len(trades) >= 2:
                    print(f"Both positions opened! Waiting for TP/SL...")
                    pos_last_status = time.time()

                    while True:
                        if not is_trading_hours():
                            break

                        await asyncio.sleep(get_check_interval())
                        trades, _ = await trader.get_open_trades()

                        if len(trades) == 0:
                            print("All positions closed!")
                            break

                        # Status every 2 minutes
                        if time.time() - pos_last_status >= 120:
                            now = get_msk_time()
                            print(f"[{now.strftime('%H:%M:%S')}] Positions: {len(trades)} open")
                            pos_last_status = time.time()

                    break  # Go to next cycle

                # Check if price moved too far - reposition
                if price_diff > reposition_threshold:
                    print(f"Price moved {price_diff*100:.2f}% - repositioning...")

                    # Cancel pending orders
                    for order in pending:
                        try:
                            await trader.cancel_order(
                                pair_index=order.pairIndex,
                                trade_index=order.index,
                                dry_run=False
                            )
                            await asyncio.sleep(random.uniform(1, 2))
                        except Exception as e:
                            print(f"Cancel error: {e}")

                    break  # Go to next cycle (new orders)

        print(f"\nCycle {cycle} complete.")
        await asyncio.sleep(random.uniform(3, 8))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped")
