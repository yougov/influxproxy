import asyncio

from aiohttp import web

from influxproxy.configuration import DEBUG, PORT, config, logger
from influxproxy.drivers import InfluxDriver


ALL_ALLOWED_ORIGINS = [
    allowed
    for db_conf in config['databases'].values()
    for allowed in db_conf['allow_from']
]


class RequestError(RuntimeError):
    """Raised when there's a request error."""


def create_app(loop):
    app = web.Application(logger=logger, loop=loop, debug=DEBUG)

    app.router.add_route('GET', '/ping', ping)
    app.router.add_route('OPTIONS', '/metric', preflight_metric)

    return app


def ensure_headers(request):
    expected_headers = ['Origin', 'Access-Control-Request-Method']
    for header in expected_headers:
        if header not in request.headers:
            raise RequestError('{} header is missing'.format(header))


async def ping(request):
    return web.Response(body=b'pong')


async def preflight_metric(request):
    try:
        ensure_headers(request)
    except RequestError as e:
        return web.Response(status=400, reason=str(e).encode('utf-8'))

    origin = request.headers['Origin']

    if request.headers['Access-Control-Request-Method'] != 'POST':
        return web.Response(status=405, reason=b'Only POST allowed')

    if origin not in ALL_ALLOWED_ORIGINS:
        return web.Response(status=403, reason=b'Origin not allowed')

    return web.Response(body=b'', headers={
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Request-Headers': 'Content-Type',
        'Access-Control-Max-Age': '600',
        'Access-Control-Allow-Origin': origin,
    })


if __name__ == '__main__':  # pragma: no cover
    driver = InfluxDriver()
    driver.create_databases()
    loop = asyncio.get_event_loop()
    app = create_app(loop)
    web.run_app(app, host=config['host'], port=PORT)
