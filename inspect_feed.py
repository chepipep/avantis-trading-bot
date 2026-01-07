from dex import get_client

client = get_client()
feed = client.feed_client

print("=== FeedClient attributes ===")
for name in dir(feed):
    if not name.startswith("_"):
        print(name)
