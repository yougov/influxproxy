#!/usr/bin/env python

import asyncio
import base64
import logging
import os
from uuid import uuid4

import aiohttp_jinja2
import jinja2
import uvloop
from aiohttp import web

from influxproxy.configuration import DEBUG, PORT, PROJECT_ROOT, config
from influxproxy.drivers import InfluxDriver, MalformedDataError


ALL_ALLOWED_ORIGINS = [
    allowed
    for db_conf in config['databases'].values()
    for allowed in db_conf['allow_from']
]
MANUAL_TEST_HOST = os.environ.get('HOST', 'localhost')


logger = logging.getLogger('influxdb.app')
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def create_app(loop):
    app = web.Application(logger=logger, loop=loop, debug=DEBUG)

    app.router.add_route('GET', '/ping', ping)
    app.router.add_route('OPTIONS', '/metric', preflight_metric)
    app.router.add_route('POST', '/metric', send_metric)
    app.router.add_route('GET', '/manual-test', manual_test)
    app.router.add_static('/static', PROJECT_ROOT / 'influxproxy' / 'static')
    aiohttp_jinja2.setup(
        app, loader=jinja2.FileSystemLoader(
            str(PROJECT_ROOT / 'influxproxy' / 'templates')))

    return app


def ensure_headers(request, expected_headers):
    for header in expected_headers:
        if header not in request.headers:
            raise web.HTTPBadRequest(
                reason='{} header is missing'.format(header))


async def ping(request):
    return web.Response(body=b'pong')


async def preflight_metric(request):
    ensure_headers(request, ['Origin', 'Access-Control-Request-Method'])

    origin = request.headers['Origin']
    method = request.headers['Access-Control-Request-Method']

    if method != 'POST':
        raise web.HTTPMethodNotAllowed(method, ['POST'])

    if origin not in ALL_ALLOWED_ORIGINS:
        raise web.HTTPForbidden(reason='Origin not allowed')

    return web.Response(headers={
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Max-Age': str(config['preflight_expiration']),
        'Content-Type': 'text/plain',
    })


async def send_metric(request):
    ensure_headers(request, ['Origin', 'Authorization'])

    authorization = request.headers['Authorization']
    origin = request.headers['Origin']
    request_id = uuid4()

    try:
        auth_type, auth = authorization.split(maxsplit=1)
        b64_decoded = base64.b64decode(auth)
        database, public_key = b64_decoded.decode('utf-8').split(':')
    except:
        raise web.HTTPBadRequest(reason='Bad Authorization string: {}'.format(
            authorization
        ))

    if auth_type != 'Basic':
        raise web.HTTPBadRequest(reason='Authorization must be Basic')

    try:
        db_conf = config['databases'][database]
    except KeyError:
        raise web.HTTPUnauthorized()

    if public_key != db_conf['public_key']:
        raise web.HTTPUnauthorized()

    if origin not in db_conf['allow_from']:
        raise web.HTTPForbidden(reason='Origin not allowed')

    points = await request.json()

    try:
        driver = InfluxDriver(udp_port=db_conf.get('udp_port'))
        driver.write(database, points)
    except MalformedDataError as e:
        raise web.HTTPBadRequest(reason=str(e))
    except Exception as e:
        logger.error('Metric for request %s failed', request_id)
        logger.exception(e)
        reason = (
            'Internal Server Error. Please provide this ID to the system '
            'administrators: {}').format(request_id)
        raise web.HTTPInternalServerError(reason=reason)

    raise web.HTTPNoContent(headers={
        'Access-Control-Allow-Origin': origin,
    })


@aiohttp_jinja2.template('manual-test.html')
async def manual_test(request):
    if not config['manual_test_page']:
        raise web.HTTPNotFound()

    database = list(config['databases'])[0]
    public_key = config['databases'][database]['public_key']

    return {
        'database': database,
        'public_key': public_key,
        'host': MANUAL_TEST_HOST,
        'port': PORT,
    }


if __name__ == '__main__':  # pragma: no cover
    driver = InfluxDriver()
    driver.create_databases()
    loop = asyncio.get_event_loop()
    app = create_app(loop)
    web.run_app(app, host=config['host'], port=PORT)
