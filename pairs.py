"""
Trading pairs configuration for Avantis DEX.
"""

# All available trading pairs with their indexes
# Format: (index, name, category)
TRADING_PAIRS = [
    # Crypto - Major
    (1, "BTC/USD", "Crypto"),
    (2, "ETH/USD", "Crypto"),

    # Crypto - Layer 1
    (3, "SOL/USD", "Crypto"),
    (4, "BNB/USD", "Crypto"),
    (5, "AVAX/USD", "Crypto"),
    (6, "NEAR/USD", "Crypto"),
    (7, "SUI/USD", "Crypto"),
    (8, "SEI/USD", "Crypto"),
    (9, "INJ/USD", "Crypto"),
    (10, "TIA/USD", "Crypto"),

    # Crypto - Layer 2 & Scaling
    (11, "ARB/USD", "Crypto"),
    (12, "OP/USD", "Crypto"),
    (13, "STX/USD", "Crypto"),

    # Crypto - DeFi
    (14, "LINK/USD", "Crypto"),
    (15, "AAVE/USD", "Crypto"),
    (16, "LDO/USD", "Crypto"),

    # Crypto - Meme
    (17, "DOGE/USD", "Crypto"),
    (18, "SHIB/USD", "Crypto"),
    (19, "PEPE/USD", "Crypto"),
    (20, "WIF/USD", "Crypto"),
    (21, "BONK/USD", "Crypto"),

    # Crypto - Other
    (22, "XRP/USD", "Crypto"),
    (23, "APE/USD", "Crypto"),
    (24, "JUP/USD", "Crypto"),
    (25, "WLD/USD", "Crypto"),
    (26, "ORDI/USD", "Crypto"),

    # Forex
    (51, "EUR/USD", "Forex"),
    (52, "GBP/USD", "Forex"),

    # Commodities
    (61, "XAU/USD", "Commodities"),
    (62, "XAG/USD", "Commodities"),
]

# Quick lookup dict: name -> (index, category)
PAIRS_DICT = {name: (idx, cat) for idx, name, cat in TRADING_PAIRS}

# List of pair names only
PAIR_NAMES = [name for _, name, _ in TRADING_PAIRS]


def get_pair_index(pair_name: str) -> int:
    """Get pair index by name."""
    if pair_name in PAIRS_DICT:
        return PAIRS_DICT[pair_name][0]
    raise ValueError(f"Unknown pair: {pair_name}")


def get_pair_category(pair_name: str) -> str:
    """Get pair category by name."""
    if pair_name in PAIRS_DICT:
        return PAIRS_DICT[pair_name][1]
    return "Unknown"


async def get_pair_price(pair_name: str) -> float:
    """Get current price for a pair."""
    from avantis_trader_sdk.feed.feed_client import FeedClient

    feed = FeedClient()
    try:
        data = await feed.get_latest_price_updates([pair_name])
        if data.parsed and len(data.parsed) > 0:
            return data.parsed[0].converted_price
    except:
        pass
    return 0.0


async def get_multiple_prices(pair_names: list) -> dict:
    """Get prices for multiple pairs at once."""
    from avantis_trader_sdk.feed.feed_client import FeedClient

    feed = FeedClient()
    prices = {}

    try:
        data = await feed.get_latest_price_updates(pair_names)
        for i, pair in enumerate(pair_names):
            if data.parsed and i < len(data.parsed):
                prices[pair] = data.parsed[i].converted_price
            else:
                prices[pair] = 0.0
    except:
        for pair in pair_names:
            prices[pair] = 0.0

    return prices
