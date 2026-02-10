import asyncio

from aiohttp import web


async def hello(request):
    return web.Response(text='{"Hello": "World"}', content_type='application/json')

async def main():
    app = web.Application()
    app.router.add_get('/', hello)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8004)
    await site.start()
    print("Server started on http://0.0.0.0:8004")

    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
