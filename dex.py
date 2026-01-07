# dex.py

from avantis_trader_sdk import TraderClient
from config import RPC_URL


def get_client():
    client = TraderClient(RPC_URL)
    return client
