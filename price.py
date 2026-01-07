from avantis_trader_sdk.feed.feed_client import FeedClient


# Global feed client instance
_feed_client = None


def get_feed_client():
    """Get or create FeedClient instance."""
    global _feed_client
    if _feed_client is None:
        _feed_client = FeedClient()
    return _feed_client


async def get_btc_price() -> float:
    """
    Get BTC/USD price from Avantis feed (same source as trading).
    This ensures TP/SL calculations match exactly.
    """
    feed = get_feed_client()
    price_data = await feed.get_latest_price_updates(["BTC/USD"])
    return price_data.parsed[0].converted_price


async def get_pair_price(pair_name: str) -> float:
    """
    Get price for any trading pair from Avantis feed.
    """
    feed = get_feed_client()
    try:
        price_data = await feed.get_latest_price_updates([pair_name])
        if price_data.parsed and len(price_data.parsed) > 0:
            return price_data.parsed[0].converted_price
    except:
        pass
    return 0.0


