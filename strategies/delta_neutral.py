"""
Delta-Neutral Strategy.

Opens both LONG and SHORT positions at the same entry price.
Profits when either position hits TP, loss when both hit SL.
"""

import random
from dataclasses import dataclass
from typing import List

from .base import BaseStrategy, StrategyConfig, Signal, OrderParams


@dataclass
class DeltaNeutralConfig(StrategyConfig):
    """Configuration for Delta-Neutral strategy."""
    name: str = "delta_neutral"

    # Entry offset from current price
    entry_offset_min: float = 0.0025   # 0.25%
    entry_offset_max: float = 0.01     # 1.0%

    # Reposition threshold
    reposition_threshold: float = 0.01  # 1%
    reposition_variance: float = 0.002  # ±0.2%

    # Deposit variance
    deposit_variance: float = 0.05      # 5%
    deposit_step: float = 0.5           # Rounding step


class DeltaNeutralStrategy(BaseStrategy):
    """
    Delta-Neutral Strategy.

    Logic:
    1. Calculate entry price with random offset from current price
    2. Place both LONG and SHORT limit orders at the same entry price
    3. Wait for orders to fill
    4. Wait for TP or SL to be hit
    5. If price moves too far (reposition threshold), cancel and restart

    The strategy profits when one position hits TP before the other hits SL.
    Maximum loss is when both positions hit SL (rare due to same entry).
    """

    def __init__(self, config: DeltaNeutralConfig):
        super().__init__(config)
        self.config: DeltaNeutralConfig = config

        # Strategy-specific state
        self._entry_price = 0
        self._direction = "BELOW"
        self._reposition_threshold = 0
        self._order_params: List[OrderParams] = []

    def on_start(self):
        """Initialize strategy."""
        self.log(f"Entry Offset: {self.config.entry_offset_min*100:.2f}% - {self.config.entry_offset_max*100:.2f}%")
        self.log(f"Reposition: {self.config.reposition_threshold*100:.1f}% (±{self.config.reposition_variance*100:.1f}%)")

    def on_cycle_start(self, cycle: int):
        """Prepare for new cycle."""
        super().on_cycle_start(cycle)

        # Reset state
        self._entry_price = 0
        self._order_params = []

        # Calculate reposition threshold for this cycle
        base = self.config.reposition_threshold
        variance = random.uniform(
            -self.config.reposition_variance,
            self.config.reposition_variance
        )
        self._reposition_threshold = base + variance

        self.log(f"Reposition threshold: {self._reposition_threshold*100:.2f}%")

    def on_tick(self, price: float) -> Signal:
        """
        Process price update and return signal.

        First tick: calculate entry and return OPEN_BOTH
        Subsequent ticks: check for reposition
        """
        # First tick of cycle - calculate entry and open positions
        if self._entry_price == 0:
            self._calculate_entry(price)
            return Signal.OPEN_BOTH

        # Check if we need to reposition
        if self._should_reposition(price):
            self.log(f"Price moved too far - repositioning")
            return Signal.REPOSITION

        return Signal.NONE

    def _calculate_entry(self, current_price: float):
        """Calculate entry price and direction."""
        # Random offset
        offset = random.uniform(
            self.config.entry_offset_min,
            self.config.entry_offset_max
        )

        # Random direction
        self._direction = random.choice(["ABOVE", "BELOW"])

        if self._direction == "ABOVE":
            self._entry_price = current_price * (1 + offset)
        else:
            self._entry_price = current_price * (1 - offset)

        self.log(f"Direction: {self._direction} | Offset: {offset*100:.3f}%")
        self.log(f"Entry: ${self._entry_price:.2f}")

        # Calculate TP/SL
        long_tp, long_sl = self.calc_tp_sl_price(self._entry_price, is_long=True)
        short_tp, short_sl = self.calc_tp_sl_price(self._entry_price, is_long=False)

        # Vary collateral
        collateral = self._vary_amount(self.config.position_size)
        self.log(f"Collateral: ${collateral:.2f}")

        # Store order params
        self._order_params = [
            OrderParams(
                pair_index=self.config.pair_index,
                is_long=True,
                collateral=collateral,
                leverage=self.config.leverage,
                entry_price=self._entry_price,
                tp_price=long_tp,
                sl_price=long_sl,
                direction=self._direction,
            ),
            OrderParams(
                pair_index=self.config.pair_index,
                is_long=False,
                collateral=collateral,
                leverage=self.config.leverage,
                entry_price=self._entry_price,
                tp_price=short_tp,
                sl_price=short_sl,
                direction=self._direction,
            ),
        ]

    def _vary_amount(self, amount: float) -> float:
        """Apply variance and rounding to collateral."""
        variance = self.config.deposit_variance
        step = self.config.deposit_step

        if step <= 0:
            step = 0.5

        factor = 1 + random.uniform(-variance, variance)
        varied = amount * factor
        return round(varied / step) * step

    def _should_reposition(self, current_price: float) -> bool:
        """Check if price moved too far from anchor."""
        anchor = self.state.anchor_price
        if anchor <= 0:
            return False

        diff = abs(current_price - anchor) / anchor
        return diff > self._reposition_threshold

    def get_order_params(self) -> List[OrderParams]:
        """Return order parameters for engine to execute."""
        return self._order_params


# Factory function for easy creation
def create_delta_neutral_strategy(
    pair_name: str = "BTC/USD",
    pair_index: int = 1,
    position_size: float = 10.0,
    leverage: int = 75,
    take_profit_pct: float = 0.80,
    stop_loss_pct: float = 0.80,
    entry_offset_min: float = 0.0025,
    entry_offset_max: float = 0.01,
    reposition_threshold: float = 0.01,
    check_interval_min: float = 10,
    check_interval_max: float = 30,
    trading_start_hour: int = 8,
    trading_end_hour: int = 24,
    trading_variance: int = 15,
    dry_run: bool = True,
) -> DeltaNeutralStrategy:
    """Create a delta-neutral strategy with the given parameters."""
    config = DeltaNeutralConfig(
        pair_name=pair_name,
        pair_index=pair_index,
        position_size=position_size,
        leverage=leverage,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        entry_offset_min=entry_offset_min,
        entry_offset_max=entry_offset_max,
        reposition_threshold=reposition_threshold,
        check_interval_min=check_interval_min,
        check_interval_max=check_interval_max,
        trading_start_hour=trading_start_hour,
        trading_end_hour=trading_end_hour,
        trading_variance=trading_variance,
        dry_run=dry_run,
    )
    return DeltaNeutralStrategy(config)
