import asyncio
from dex import get_client

async def main():
    client = get_client()
    pairs_info = await client.pairs_cache.get_pairs_info()

    print("AVAILABLE PAIRS:")
    for key in pairs_info.keys():
        print(key)

asyncio.run(main())
