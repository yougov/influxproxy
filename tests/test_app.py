from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from nose.tools import istest

from influxproxy.app import create_app


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
