import asyncio
import logging
import os

import yaml
from aiohttp import web


logger = logging.basicConfig(level=logging.INFO)
config = yaml.load(open(os.environ['APP_SETTINGS_YAML']))
PORT = int(os.environ.get('PORT', 8765))
DEBUG = config.get('debug', False)


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
