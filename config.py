# ============================================================
#                    DELTA-NEUTRAL BOT CONFIG
# ============================================================
# Configure your settings below
# ============================================================

# ------------------------------------------------------------
# NETWORK & WALLET
# ------------------------------------------------------------
RPC_URL = "https://mainnet.base.org"
PRIVATE_KEY = ""  # Set via GUI or settings.json

# ------------------------------------------------------------
# MODE
# ------------------------------------------------------------
DRY_RUN = True  # True = simulation, False = live trading

# ------------------------------------------------------------
# TRADING PAIR
# ------------------------------------------------------------
PAIR_NAME = "BTC/USD"
PAIR_INDEX = 1  # Pair index on Avantis (BTC/USD = 1)

# ------------------------------------------------------------
# POSITION SIZE
# ------------------------------------------------------------
POSITION_SIZE_USDC = 10.0  # Collateral in USDC per position
LEVERAGE = 75              # Leverage (1-150)
DEPOSIT_VARIANCE = 0.05    # 5% variance for collateral randomization
DEPOSIT_STEP = 0.5         # Rounding step for collateral (0.5 = 10.0, 10.5, 11.0...)

# ------------------------------------------------------------
# TAKE PROFIT / STOP LOSS (% of PnL)
# ------------------------------------------------------------
TAKE_PROFIT_PNL = 0.80  # +80% = close with profit
STOP_LOSS_PNL = 0.80    # -80% = close with loss

# ------------------------------------------------------------
# ENTRY LEVELS
# ------------------------------------------------------------
ENTRY_OFFSET_MIN = 0.0025   # 0.25% minimum
ENTRY_OFFSET_MAX = 0.01     # 1.0% maximum

# ------------------------------------------------------------
# REPOSITIONING
# ------------------------------------------------------------
REPOSITION_THRESHOLD_PCT = 0.01   # 1% - if price moved, cancel and reposition
REPOSITION_RANDOM = 0.002         # ±0.2% randomness

# ------------------------------------------------------------
# INTERVALS
# ------------------------------------------------------------
CHECK_INTERVAL_MIN = 10   # Minimum seconds between checks
CHECK_INTERVAL_MAX = 30   # Maximum seconds between checks

# ------------------------------------------------------------
# TRADING HOURS (UTC)
# ------------------------------------------------------------
TRADING_START_HOUR = 8    # Start trading at 8:00
TRADING_END_HOUR = 24     # End trading at 00:00 (24 = midnight)
TRADING_HOURS_VARIANCE = 15  # ±15 minutes variance
