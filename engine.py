"""
Trading Engine - Executes strategy signals and manages the trading loop.
"""

import asyncio
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable

from trader import AvantisTrader
from price import get_pair_price
from trades_history import add_trade_dict
from strategies.base import BaseStrategy, Signal, StrategyState

MSK = timezone(timedelta(hours=3))


class TradingEngine:
    """
    Trading engine that runs strategies and executes their signals.

    The engine:
    1. Manages the main trading loop
    2. Calls strategy lifecycle methods
    3. Executes signals from strategies
    4. Updates strategy state with market data
    5. Handles logging to trade history
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        rpc_url: str,
        private_key: str,
        on_log: Optional[Callable[[str], None]] = None,
    ):
        self.strategy = strategy
        self.config = strategy.config
        self.trader = AvantisTrader(rpc_url, private_key)
        self.on_log = on_log or print

        self._running = False
        self._cycle = 0
        self._last_status_time = 0
        self._positions_opened_at: Optional[str] = None
        self._saved_trades: list = []

    @property
    def running(self) -> bool:
        return self._running

    def stop(self):
        """Stop the engine."""
        self._running = False

    def log(self, message: str):
        """Log a message."""
        now = self.get_msk_time()
        self.on_log(f"[{now.strftime('%H:%M:%S')}] {message}")

    # === Time Helpers ===

    def get_msk_time(self) -> datetime:
        """Get current time in MSK timezone."""
        return datetime.now(MSK)

    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        now = self.get_msk_time()
        current_minutes = now.hour * 60 + now.minute

        variance = random.randint(
            -self.config.trading_variance,
            self.config.trading_variance
        )

        start_minutes = self.config.trading_start_hour * 60 + variance
        end_minutes = self.config.trading_end_hour * 60 + variance

        start_minutes = max(0, min(start_minutes, 1439))
        end_minutes = max(0, min(end_minutes, 1440))

        # Handle overnight trading
        if self.config.trading_end_hour <= self.config.trading_start_hour:
            return current_minutes >= start_minutes or current_minutes < end_minutes
        else:
            return start_minutes <= current_minutes < end_minutes

    def get_check_interval(self) -> float:
        """Get random check interval."""
        return random.uniform(
            self.config.check_interval_min,
            self.config.check_interval_max
        )

    # === Trading Operations ===

    async def execute_signal(self, signal: Signal) -> bool:
        """
        Execute a trading signal.

        Returns:
            True if successful
        """
        if signal == Signal.NONE:
            return True

        self.log(f"Executing signal: {signal.value}")

        try:
            if signal == Signal.OPEN_BOTH:
                return await self._execute_open_both()

            elif signal == Signal.OPEN_LONG:
                return await self._execute_open_single(is_long=True)

            elif signal == Signal.OPEN_SHORT:
                return await self._execute_open_single(is_long=False)

            elif signal == Signal.CANCEL_ORDERS:
                return await self._execute_cancel_orders()

            elif signal == Signal.REPOSITION:
                await self._execute_cancel_orders()
                return True  # Will open new orders on next cycle

            elif signal == Signal.CLOSE_ALL:
                return await self._execute_close_all()

            return True

        except Exception as e:
            self.log(f"Error executing signal: {e}")
            return False

    async def _execute_open_both(self) -> bool:
        """Execute OPEN_BOTH signal (delta-neutral)."""
        order_params = self.strategy.get_order_params()

        if len(order_params) < 2:
            self.log("Error: OPEN_BOTH requires 2 order params")
            return False

        for params in order_params:
            await self.trader.place_limit_order(
                pair_index=params.pair_index,
                is_long=params.is_long,
                collateral=params.collateral,
                leverage=params.leverage,
                limit_price=params.entry_price,
                tp_price=params.tp_price,
                sl_price=params.sl_price,
                direction=params.direction,
                dry_run=self.config.dry_run
            )

            if not self.config.dry_run:
                await asyncio.sleep(random.uniform(2, 4))

        self.log("Orders placed")
        return True

    async def _execute_open_single(self, is_long: bool) -> bool:
        """Execute OPEN_LONG or OPEN_SHORT signal."""
        order_params = self.strategy.get_order_params()

        for params in order_params:
            if params.is_long == is_long:
                order_type = getattr(params, 'order_type', 'LIMIT')

                if order_type == "MARKET":
                    await self.trader.place_market_order(
                        pair_index=params.pair_index,
                        is_long=params.is_long,
                        collateral=params.collateral,
                        leverage=params.leverage,
                        tp_price=params.tp_price,
                        sl_price=params.sl_price,
                        dry_run=self.config.dry_run
                    )
                else:
                    await self.trader.place_limit_order(
                        pair_index=params.pair_index,
                        is_long=params.is_long,
                        collateral=params.collateral,
                        leverage=params.leverage,
                        limit_price=params.entry_price,
                        tp_price=params.tp_price,
                        sl_price=params.sl_price,
                        direction=params.direction,
                        dry_run=self.config.dry_run
                    )

                self.log(f"{'LONG' if is_long else 'SHORT'} {order_type} order placed")
                return True

        return False

    async def _execute_cancel_orders(self) -> bool:
        """Cancel all pending orders."""
        _, pending = await self.trader.get_open_trades()

        for order in pending:
            try:
                await self.trader.cancel_order(
                    pair_index=order.pair_index,
                    trade_index=order.trade_index,
                    dry_run=self.config.dry_run
                )
                await asyncio.sleep(random.uniform(1, 2))
            except Exception as e:
                self.log(f"Cancel error: {e}")

        self.log("Orders cancelled")
        return True

    async def _execute_close_all(self) -> bool:
        """Close all open positions."""
        trades, _ = await self.trader.get_open_trades()

        for trade in trades:
            inner = getattr(trade, 'trade', trade)
            try:
                collateral = getattr(inner, 'collateral_in_trade', 0)
                await self.trader.close_position(
                    pair_index=inner.pair_index,
                    trade_index=inner.trade_index,
                    collateral_to_close=collateral,
                    dry_run=self.config.dry_run
                )
                await asyncio.sleep(random.uniform(1, 2))
            except Exception as e:
                self.log(f"Close error: {e}")

        self.log("Positions closed")
        return True

    # === History Logging ===

    def _log_closed_trades(self, current_price: float):
        """Log closed trades to history."""
        for trade_obj in self._saved_trades:
            try:
                trade = getattr(trade_obj, 'trade', trade_obj)

                is_long = getattr(trade, 'is_long', getattr(trade, 'buy', False))
                entry_price = getattr(trade, 'open_price', 0) or 1.0
                collateral = getattr(trade, 'collateral_in_trade', 0) or 0
                leverage = getattr(trade, 'leverage', self.config.leverage)
                tp = getattr(trade, 'tp', 0) or 0
                sl = getattr(trade, 'sl', 0) or 0

                if entry_price <= 0 or collateral <= 0:
                    continue

                if is_long:
                    if current_price >= tp:
                        result, exit_price = "TP", tp
                    else:
                        result, exit_price = "SL", sl
                else:
                    if current_price <= tp:
                        result, exit_price = "TP", tp
                    else:
                        result, exit_price = "SL", sl

                add_trade_dict(
                    pair=self.config.pair_name,
                    side="LONG" if is_long else "SHORT",
                    entry_price=entry_price,
                    exit_price=exit_price,
                    collateral=collateral,
                    leverage=leverage,
                    result=result,
                    opened_at=self._positions_opened_at,
                )
                self.log(f"Logged {'LONG' if is_long else 'SHORT'}: {result}")

            except Exception as e:
                self.log(f"History error: {e}")

        self._saved_trades = []
        self._positions_opened_at = None

    # === Main Loop ===

    async def run(self):
        """Main trading loop."""
        self._running = True
        self.log(f"Starting {self.strategy.name} strategy")
        self.log(f"Mode: {'DRY RUN' if self.config.dry_run else 'LIVE'}")

        # Initialize
        self.strategy.on_start()

        if not self.config.dry_run:
            await self.trader.check_and_approve_usdc(
                self.config.position_size * 2
            )

        try:
            while self._running:
                await self._run_cycle()

        except asyncio.CancelledError:
            self.log("Engine cancelled")
        finally:
            self.strategy.on_stop()
            self.log("Engine stopped")

    async def _run_cycle(self):
        """Run a single trading cycle."""
        # Wait for trading hours
        while self._running and not self.is_trading_hours():
            now = self.get_msk_time()
            self.log(f"Outside trading hours. Waiting...")
            await asyncio.sleep(60)

        if not self._running:
            return

        # Check existing positions/orders
        if not self.config.dry_run:
            trades, pending = await self.trader.get_open_trades()
            self.strategy.update_state(open_trades=trades, pending_orders=pending)

            # Handle existing pending orders
            if pending:
                await self._wait_for_pending_orders()
                return

        # Start new cycle
        self._cycle += 1
        self.strategy.on_cycle_start(self._cycle)

        self.log(f"=== CYCLE {self._cycle} ===")

        # Get current price
        current_price = await get_pair_price(self.config.pair_name)
        if current_price <= 0:
            self.log("Failed to get price, retrying...")
            await asyncio.sleep(5)
            return

        # Set anchor price and update state
        self.strategy.update_state(
            current_price=current_price,
            anchor_price=current_price,
        )

        self.log(f"{self.config.pair_name}: ${current_price:.2f}")

        # Get initial signal from strategy
        signal = self.strategy.on_tick(current_price)

        if signal in (Signal.OPEN_BOTH, Signal.OPEN_LONG, Signal.OPEN_SHORT):
            success = await self.execute_signal(signal)
            self.strategy.on_signal_executed(signal, success)

            if success:
                await self._monitor_positions()

        self.strategy.on_cycle_end()
        self.log(f"Cycle {self._cycle} complete")
        await asyncio.sleep(random.uniform(3, 8))

    async def _wait_for_pending_orders(self):
        """Wait for pending orders to be filled or cancelled."""
        self.log(f"Found {len(self.strategy.state.pending_orders)} pending orders")

        while self._running:
            if not self.is_trading_hours():
                break

            await asyncio.sleep(self.get_check_interval())
            trades, pending = await self.trader.get_open_trades()
            self.strategy.update_state(open_trades=trades, pending_orders=pending)

            if not pending:
                break

        # If positions opened, wait for TP/SL
        if len(self.strategy.state.open_trades) >= 2:
            self._saved_trades = list(self.strategy.state.open_trades)
            self._positions_opened_at = self.get_msk_time().isoformat()
            await self._wait_for_positions_close()

    async def _monitor_positions(self):
        """Monitor after placing orders."""
        self._last_status_time = time.time()
        anchor_price = self.strategy.state.anchor_price

        while self._running and self.is_trading_hours():
            await asyncio.sleep(self.get_check_interval())

            # Get current price and state
            current_price = await get_pair_price(self.config.pair_name)
            if current_price <= 0:
                continue

            if not self.config.dry_run:
                trades, pending = await self.trader.get_open_trades()
                self.strategy.update_state(
                    current_price=current_price,
                    open_trades=trades,
                    pending_orders=pending
                )

            # Show status periodically
            if time.time() - self._last_status_time >= 60:
                price_diff = abs(current_price - anchor_price) / anchor_price * 100
                self.log(f"${current_price:.2f} | Diff: {price_diff:.2f}%")
                self._last_status_time = time.time()

            # Get signal from strategy
            signal = self.strategy.on_tick(current_price)

            if signal == Signal.REPOSITION:
                await self.execute_signal(signal)
                self.strategy.on_signal_executed(signal, True)
                break

            # Check if positions opened
            if not self.config.dry_run and len(trades) >= 2:
                self.log("Positions opened! Waiting for TP/SL...")
                self._saved_trades = list(trades)
                self._positions_opened_at = self.get_msk_time().isoformat()
                await self._wait_for_positions_close()
                break

        # End of trading hours - cancel pending orders
        if not self.is_trading_hours():
            self.log("Trading hours ended")
            await self.execute_signal(Signal.CANCEL_ORDERS)

    async def _wait_for_positions_close(self):
        """Wait for all positions to close (TP/SL hit)."""
        last_status = time.time()

        while self._running:
            if not self.is_trading_hours():
                break

            await asyncio.sleep(self.get_check_interval())
            trades, _ = await self.trader.get_open_trades()
            self.strategy.update_state(open_trades=trades)

            if not trades:
                self.log("All positions closed!")
                current_price = await get_pair_price(self.config.pair_name)
                self._log_closed_trades(current_price)
                break

            # Status every 2 minutes
            if time.time() - last_status >= 120:
                self.log(f"Positions: {len(trades)} open")
                last_status = time.time()
