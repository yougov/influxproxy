from .base import AppTestCase, asynctest
from influxproxy.configuration import config


DB_CONF = config['databases']['testing']


class PingTest(AppTestCase):
    @asynctest
    async def receives_a_pong(self):
        response = await self.client.get('/ping')

        self.assertEqual(response.status, 200)
        content = await response.text()
        expected = 'pong'
        self.assertEqual(content, expected)


class PreflightTest(AppTestCase):
    def assert_control(self, response, access_control, expected):
        self.assertEqual(
            response.headers['Access-Control-{}'.format(access_control)],
            expected)

    @asynctest
    async def sends_a_metric_preflight(self):
        response = await self.client.options('/metric', headers={
            'Origin': DB_CONF['allow_from'][0],
            'Access-Control-Request-Method': 'POST',
        })

        self.assertEqual(response.status, 200)
        self.assert_control(response, 'Allow-Origin', DB_CONF['allow_from'][0])
        self.assert_control(response, 'Allow-Credentials', 'true')
        self.assert_control(response, 'Allow-Methods', 'POST')
        self.assert_control(response, 'Max-Age', '600')

    @asynctest
    async def cannot_accept_preflight_if_origin_not_expected(self):
        response = await self.client.options('/metric', headers={
            'Origin': 'some-bogus_origin',
            'Access-Control-Request-Method': 'POST',
        })

        self.assertEqual(response.status, 403)

    @asynctest
    async def cannot_accept_preflight_if_method_not_expected(self):
        response = await self.client.options('/metric', headers={
            'Origin': DB_CONF['allow_from'][0],
            'Access-Control-Request-Method': 'GET',
        })

        self.assertEqual(response.status, 405)

    @asynctest
    async def cannot_accept_preflight_if_missing_origin(self):
        response = await self.client.options('/metric', headers={
            'Access-Control-Request-Method': 'POST',
        })

        self.assertEqual(response.status, 400)

    @asynctest
    async def cannot_accept_preflight_if_missing_method(self):
        response = await self.client.options('/metric', headers={
            'Origin': DB_CONF['allow_from'][0],
        })

        self.assertEqual(response.status, 400)
