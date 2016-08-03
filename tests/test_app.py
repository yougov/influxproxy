from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from influxproxy.app import create_app


class PingTest(AioHTTPTestCase):
    def get_app(self, loop):
        return create_app(loop)

    async def get(self, path):
        response = await self.client.request('GET', path)
        return response

    @unittest_run_loop
    async def test_receives_a_pong(self):
        response = await self.get('/ping')

        self.assertEqual(response.status, 200)
        content = await response.text()
        expected = 'pong'
        self.assertEqual(content, expected)
