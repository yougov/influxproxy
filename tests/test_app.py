from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from nose.tools import istest

from influxproxy.app import create_app
from influxproxy.configuration import config


DB_CONF = config['databases']['testing']


class PingTest(AioHTTPTestCase):
    def get_app(self, loop):
        return create_app(loop)

    @istest
    @unittest_run_loop
    async def receives_a_pong(self):
        response = await self.client.get('/ping')

        self.assertEqual(response.status, 200)
        content = await response.text()
        expected = 'pong'
        self.assertEqual(content, expected)

    @istest
    @unittest_run_loop
    async def sends_a_metric_preflight(self):
        response = await self.client.options('/metric', headers={
            'Origin': DB_CONF['allow_from'][0],
            'Access-Control-Request-Method': 'POST',
        })

        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'],
                         DB_CONF['allow_from'][0])
        self.assertEqual(response.headers['Access-Control-Allow-Credentials'],
                         'true')
        self.assertEqual(response.headers['Access-Control-Allow-Methods'],
                         'POST')
        self.assertEqual(response.headers['Access-Control-Request-Headers'],
                         'Content-Type')

    @istest
    @unittest_run_loop
    async def cannot_accept_preflight_if_origin_not_expected(self):
        response = await self.client.options('/metric', headers={
            'Origin': 'some-bogus_origin',
            'Access-Control-Request-Method': 'POST',
        })

        self.assertEqual(response.status, 403)

    @istest
    @unittest_run_loop
    async def cannot_accept_preflight_if_method_not_expected(self):
        response = await self.client.options('/metric', headers={
            'Origin': DB_CONF['allow_from'][0],
            'Access-Control-Request-Method': 'GET',
        })

        self.assertEqual(response.status, 405)

    @istest
    @unittest_run_loop
    async def cannot_accept_preflight_if_missing_origin(self):
        response = await self.client.options('/metric', headers={
            'Access-Control-Request-Method': 'POST',
        })

        self.assertEqual(response.status, 400)

    @istest
    @unittest_run_loop
    async def cannot_accept_preflight_if_missing_method(self):
        response = await self.client.options('/metric', headers={
            'Origin': DB_CONF['allow_from'][0],
        })

        self.assertEqual(response.status, 400)
