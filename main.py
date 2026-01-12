"""
Delta-Neutral Trading Bot - Main Entry Point

Usage:
    python main.py                  # Run with config.py settings
    python main.py --dry-run        # Force dry run mode
    python main.py --live           # Force live mode
"""

import asyncio
import argparse
import config
from engine import TradingEngine
from strategies import create_delta_neutral_strategy


def create_strategy_from_config():
    """Create strategy from config.py settings."""
    return create_delta_neutral_strategy(
        pair_name=config.PAIR_NAME,
        pair_index=config.PAIR_INDEX,
        position_size=config.POSITION_SIZE_USDC,
        leverage=config.LEVERAGE,
        take_profit_pct=config.TAKE_PROFIT_PNL,
        stop_loss_pct=config.STOP_LOSS_PNL,
        entry_offset_min=config.ENTRY_OFFSET_MIN,
        entry_offset_max=config.ENTRY_OFFSET_MAX,
        reposition_threshold=config.REPOSITION_THRESHOLD_PCT,
        check_interval_min=config.CHECK_INTERVAL_MIN,
        check_interval_max=config.CHECK_INTERVAL_MAX,
        trading_start_hour=config.TRADING_START_HOUR,
        trading_end_hour=config.TRADING_END_HOUR,
        trading_variance=config.TRADING_HOURS_VARIANCE,
        dry_run=config.DRY_RUN,
    )


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Delta-Neutral Trading Bot")
    parser.add_argument("--dry-run", action="store_true", help="Force dry run mode")
    parser.add_argument("--live", action="store_true", help="Force live mode")
    args = parser.parse_args()

    # Override dry_run if specified
    if args.dry_run:
        config.DRY_RUN = True
    elif args.live:
        config.DRY_RUN = False

    print("=" * 50)
    print("DELTA-NEUTRAL BOT (v4 - New Architecture)")
    print("=" * 50)
    print(f"Mode: {'DRY RUN' if config.DRY_RUN else 'LIVE'}")
    print(f"Pair: {config.PAIR_NAME}")
    print(f"Position: {config.POSITION_SIZE_USDC} USDC x {config.LEVERAGE}x")
    print(f"TP/SL: {config.TAKE_PROFIT_PNL*100:.0f}% / {config.STOP_LOSS_PNL*100:.0f}%")
    print(f"Entry Offset: {config.ENTRY_OFFSET_MIN*100:.2f}% - {config.ENTRY_OFFSET_MAX*100:.2f}%")
    print(f"Trading Hours: {config.TRADING_START_HOUR}:00 - {config.TRADING_END_HOUR % 24}:00 MSK")
    print("-" * 50)

    # Create strategy
    strategy = create_strategy_from_config()

    # Create and run engine
    engine = TradingEngine(
        strategy=strategy,
        rpc_url=config.RPC_URL,
        private_key=config.PRIVATE_KEY,
    )

    await engine.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped")
