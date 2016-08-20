import asyncio

from aiohttp import web

from influxproxy.configuration import DEBUG, PORT, config, logger


def create_app(loop):
    app = web.Application(logger=logger, loop=loop, debug=DEBUG)

    app.router.add_route('GET', '/ping', ping)

    return app


async def ping(request):
    return web.Response(body=b'pong')


if __name__ == '__main__':  # pragma: no cover
    loop = asyncio.get_event_loop()
    app = create_app(loop)
    web.run_app(app, host=config['host'], port=PORT)
