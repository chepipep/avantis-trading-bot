"""
Base Strategy Class for Trading Bot.
All strategies should inherit from this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class Signal(Enum):
    """Trading signals that strategies can emit."""
    NONE = "none"
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    OPEN_BOTH = "open_both"          # Delta-neutral: open both sides
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    CLOSE_ALL = "close_all"
    CANCEL_ORDERS = "cancel_orders"
    REPOSITION = "reposition"        # Cancel and place new orders


@dataclass
class OrderParams:
    """Parameters for placing an order."""
    pair_index: int
    is_long: bool
    collateral: float
    leverage: int
    entry_price: float
    tp_price: float
    sl_price: float
    direction: str = "BELOW"         # ABOVE or BELOW current price
    order_type: str = "LIMIT"        # LIMIT or MARKET


@dataclass
class StrategyState:
    """Current state available to strategy."""
    current_price: float = 0
    anchor_price: float = 0          # Reference price for the cycle
    open_trades: List[Any] = field(default_factory=list)
    pending_orders: List[Any] = field(default_factory=list)
    cycle: int = 0
    last_signal: Signal = Signal.NONE
    custom: Dict[str, Any] = field(default_factory=dict)  # Strategy-specific data


@dataclass
class StrategyConfig:
    """Base configuration for strategies."""
    name: str = "base"
    pair_name: str = "BTC/USD"
    pair_index: int = 1
    position_size: float = 10.0
    leverage: int = 75
    take_profit_pct: float = 0.80
    stop_loss_pct: float = 0.80
    check_interval_min: float = 10
    check_interval_max: float = 30
    trading_start_hour: int = 8
    trading_end_hour: int = 24
    trading_variance: int = 15
    dry_run: bool = True


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    Lifecycle:
    1. on_start() - Called once when bot starts
    2. on_cycle_start() - Called at the beginning of each trading cycle
    3. on_tick() - Called on each price update
    4. on_signal_executed() - Called after a signal is executed
    5. on_cycle_end() - Called at the end of each trading cycle
    6. on_stop() - Called when bot stops
    """

    def __init__(self, config: StrategyConfig):
        self.config = config
        self.state = StrategyState()
        self._enabled = True

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    # === Lifecycle Methods ===

    def on_start(self):
        """Called once when the bot starts. Override for initialization."""
        pass

    def on_stop(self):
        """Called when the bot stops. Override for cleanup."""
        pass

    def on_cycle_start(self, cycle: int):
        """Called at the beginning of each trading cycle."""
        self.state.cycle = cycle

    def on_cycle_end(self):
        """Called at the end of each trading cycle."""
        pass

    def on_signal_executed(self, signal: Signal, success: bool):
        """Called after a signal is executed by the engine."""
        self.state.last_signal = signal

    # === Abstract Methods (must be implemented) ===

    @abstractmethod
    def on_tick(self, price: float) -> Signal:
        """
        Called on each price update.

        Args:
            price: Current market price

        Returns:
            Signal indicating what action to take
        """
        pass

    @abstractmethod
    def get_order_params(self) -> List[OrderParams]:
        """
        Get parameters for orders to be placed.
        Called when signal is OPEN_LONG, OPEN_SHORT, or OPEN_BOTH.

        Returns:
            List of OrderParams for orders to place
        """
        pass

    # === Helper Methods ===

    def update_state(
        self,
        current_price: Optional[float] = None,
        anchor_price: Optional[float] = None,
        open_trades: Optional[List] = None,
        pending_orders: Optional[List] = None,
    ):
        """Update the strategy state with new data."""
        if current_price is not None:
            self.state.current_price = current_price
        if anchor_price is not None:
            self.state.anchor_price = anchor_price
        if open_trades is not None:
            self.state.open_trades = open_trades
        if pending_orders is not None:
            self.state.pending_orders = pending_orders

    def has_open_positions(self) -> bool:
        """Check if there are any open positions."""
        return len(self.state.open_trades) > 0

    def has_pending_orders(self) -> bool:
        """Check if there are any pending orders."""
        return len(self.state.pending_orders) > 0

    def calc_tp_sl_price(
        self,
        entry_price: float,
        is_long: bool,
        tp_pct: Optional[float] = None,
        sl_pct: Optional[float] = None,
    ) -> tuple:
        """
        Calculate TP and SL prices.

        Args:
            entry_price: Entry price
            is_long: True for long, False for short
            tp_pct: Take profit PnL % (default from config)
            sl_pct: Stop loss PnL % (default from config)

        Returns:
            Tuple of (tp_price, sl_price)
        """
        tp_pct = tp_pct or self.config.take_profit_pct
        sl_pct = sl_pct or self.config.stop_loss_pct
        leverage = self.config.leverage

        tp_move = tp_pct / leverage
        sl_move = sl_pct / leverage

        if is_long:
            tp_price = entry_price * (1 + tp_move)
            sl_price = entry_price * (1 - sl_move)
        else:
            tp_price = entry_price * (1 - tp_move)
            sl_price = entry_price * (1 + sl_move)

        return tp_price, sl_price

    def calc_pnl(
        self,
        entry_price: float,
        current_price: float,
        collateral: float,
        is_long: bool,
    ) -> float:
        """Calculate current PnL in USD."""
        leverage = self.config.leverage

        if is_long:
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price

        return pnl_pct * leverage * collateral

    def log(self, message: str):
        """Log a message with strategy name prefix."""
        print(f"[{self.name.upper()}] {message}")
