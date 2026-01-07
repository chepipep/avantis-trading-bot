import asyncio
from dex import get_client

async def main():
    client = get_client()
    snapshot = await client.snapshot.get_snapshot()

    print("TYPE:", type(snapshot))
    print("DIR:", dir(snapshot))
    print("REPR:", snapshot)

asyncio.run(main())
