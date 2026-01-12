"""
Example Strategy Template.

Copy this file and modify to create your own strategy.
"""

from dataclasses import dataclass
from typing import List

from .base import BaseStrategy, StrategyConfig, Signal, OrderParams


@dataclass
class MyStrategyConfig(StrategyConfig):
    """Configuration for your strategy."""
    name: str = "my_strategy"

    # Add your custom parameters here
    my_param_1: float = 0.5
    my_param_2: int = 10


class MyStrategy(BaseStrategy):
    """
    Your Strategy Description.

    Explain what your strategy does:
    1. How it decides when to open positions
    2. How it decides when to close
    3. Any special logic

    Example use cases:
    - Trend following
    - Mean reversion
    - Grid trading
    - Scalping
    """

    def __init__(self, config: MyStrategyConfig):
        super().__init__(config)
        self.config: MyStrategyConfig = config

        # Initialize your strategy-specific state
        self._my_state_var = 0

    def on_start(self):
        """Called once when bot starts. Initialize anything needed."""
        self.log(f"Starting with param1={self.config.my_param_1}")

    def on_stop(self):
        """Called when bot stops. Cleanup if needed."""
        self.log("Strategy stopped")

    def on_cycle_start(self, cycle: int):
        """Called at the beginning of each trading cycle."""
        super().on_cycle_start(cycle)
        # Reset cycle-specific state
        self._my_state_var = 0

    def on_tick(self, price: float) -> Signal:
        """
        Called on each price update. Return a Signal.

        Available signals:
        - Signal.NONE: Do nothing
        - Signal.OPEN_LONG: Open a long position
        - Signal.OPEN_SHORT: Open a short position
        - Signal.OPEN_BOTH: Open both (delta-neutral)
        - Signal.CLOSE_LONG: Close long position
        - Signal.CLOSE_SHORT: Close short position
        - Signal.CLOSE_ALL: Close all positions
        - Signal.CANCEL_ORDERS: Cancel pending orders
        - Signal.REPOSITION: Cancel and reposition

        Example logic:
        """
        # Access current state
        anchor = self.state.anchor_price
        positions = self.state.open_trades
        pending = self.state.pending_orders

        # Example: Open long if price dropped 1% from anchor
        if anchor > 0:
            change = (price - anchor) / anchor

            if change < -0.01 and not self.has_open_positions():
                self.log(f"Price dropped {change*100:.2f}% - opening LONG")
                return Signal.OPEN_LONG

            if change > 0.01 and not self.has_open_positions():
                self.log(f"Price rose {change*100:.2f}% - opening SHORT")
                return Signal.OPEN_SHORT

        return Signal.NONE

    def get_order_params(self) -> List[OrderParams]:
        """
        Called when opening positions. Return order parameters.

        This is called after on_tick returns OPEN_LONG, OPEN_SHORT, or OPEN_BOTH.
        """
        current_price = self.state.current_price

        # Calculate TP/SL using helper method
        tp, sl = self.calc_tp_sl_price(current_price, is_long=True)

        return [
            OrderParams(
                pair_index=self.config.pair_index,
                is_long=True,  # or False for short
                collateral=self.config.position_size,
                leverage=self.config.leverage,
                entry_price=current_price,
                tp_price=tp,
                sl_price=sl,
                direction="BELOW",  # or "ABOVE"
            )
        ]


# Factory function for easy creation
def create_my_strategy(
    pair_name: str = "BTC/USD",
    position_size: float = 10.0,
    leverage: int = 75,
    my_param_1: float = 0.5,
    my_param_2: int = 10,
    dry_run: bool = True,
) -> MyStrategy:
    """Create your strategy with given parameters."""
    config = MyStrategyConfig(
        pair_name=pair_name,
        position_size=position_size,
        leverage=leverage,
        my_param_1=my_param_1,
        my_param_2=my_param_2,
        dry_run=dry_run,
    )
    return MyStrategy(config)
