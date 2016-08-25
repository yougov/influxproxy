import json
from unittest.mock import patch

from .base import AppTestCase, asynctest
from influxproxy.configuration import config
from influxproxy.drivers import MalformedDataError


DB_USER = 'testing'
DB_CONF = config['databases'][DB_USER]


class PingTest(AppTestCase):
    @asynctest
    async def receives_a_pong(self):
        response = await self.client.get('/ping')

        self.assertEqual(response.status, 200)
        content = await response.text()
        expected = 'pong'
        self.assertEqual(content, expected)


class PreflightTest(AppTestCase):
    def setUp(self):
        super().setUp()
        self.user = DB_USER
        self.public_key = DB_CONF['public_key']
        self.headers = {
            'Origin': DB_CONF['allow_from'][0],
            'Access-Control-Request-Method': 'POST',
        }

    async def do_preflight(self, headers=None):
        url = '/metric/{}/{}'.format(self.user, self.public_key)
        if headers is not None:
            self.headers.update(headers)

        return await self.client.options(url, headers=self.headers)

    @asynctest
    async def sends_a_metric_preflight(self):
        response = await self.do_preflight()

        self.assertEqual(response.status, 200)
        self.assert_control(response, 'Allow-Origin', DB_CONF['allow_from'][0])
        self.assert_control(response, 'Allow-Methods', 'POST')
        self.assert_control(
            response, 'Allow-Headers', 'Content-Type')
        self.assert_control(
            response, 'Max-Age', str(config['preflight_expiration']))

    @asynctest
    async def sends_a_metric_preflight_to_generic_database(self):
        self.user = 'udp'
        self.public_key = config['databases']['udp']['public_key']
        origin = 'http://some-unregistered-website.com'
        self.headers['Origin'] = origin
        response = await self.do_preflight()

        self.assertEqual(response.status, 200)
        self.assert_control(response, 'Allow-Origin', origin)
        self.assert_control(response, 'Allow-Methods', 'POST')
        self.assert_control(
            response, 'Allow-Headers', 'Content-Type')
        self.assert_control(
            response, 'Max-Age', str(config['preflight_expiration']))

    @asynctest
    async def cannot_accept_preflight_if_origin_not_expected(self):
        response = await self.do_preflight(headers={
            'Origin': 'some-bogus_origin',
        })

        self.assertEqual(response.status, 403)

    @asynctest
    async def cannot_accept_preflight_if_wrong_database(self):
        self.user = 'bogus-user'

        response = await self.do_preflight()

        self.assertEqual(response.status, 401)

    @asynctest
    async def cannot_accept_preflight_if_wrong_public_key(self):
        self.public_key = 'bogus-key'

        response = await self.do_preflight()

        self.assertEqual(response.status, 401)

    @asynctest
    async def cannot_accept_preflight_if_method_not_expected(self):
        response = await self.do_preflight(headers={
            'Access-Control-Request-Method': 'GET',
        })

        self.assertEqual(response.status, 405)

    @asynctest
    async def cannot_accept_preflight_if_missing_origin(self):
        del self.headers['Origin']

        response = await self.do_preflight()

        self.assertEqual(response.status, 400)

    @asynctest
    async def cannot_accept_preflight_if_missing_method(self):
        del self.headers['Access-Control-Request-Method']

        response = await self.do_preflight()

        self.assertEqual(response.status, 400)


class MetricPostTest(AppTestCase):
    def setUp(self):
        super().setUp()

        self.origin = DB_CONF['allow_from'][0]
        self.points = ['point1', 'point2']
        self.data = json.dumps(self.points).encode('utf-8')
        self.headers = {
            'Content-Type': 'application/json',
            'Origin': self.origin,
        }
        self.set_auth(DB_USER, DB_CONF['public_key'])

    def set_auth(self, user, public_key):
        self.user = user
        self.public_key = public_key

    def set_origin(self, origin):
        self.origin = origin
        self.headers['Origin'] = origin

    async def send_metric(self, headers=None):
        url = '/metric/{}/{}'.format(self.user, self.public_key)

        return await self.client.post(
            url, data=self.data, headers=self.headers)

    @asynctest
    async def sends_metric_to_driver(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value

            response = await self.send_metric()

            self.assertEqual(response.status, 204)
            self.assert_control(response, 'Allow-Origin', self.origin)
            MockDriver.assert_called_once_with(udp_port=DB_CONF['udp_port'])
            driver.write.assert_called_once_with(DB_USER, self.points)

    @asynctest
    async def sends_metric_to_generic_database(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            self.user = 'udp'
            self.public_key = config['databases']['udp']['public_key']
            origin = 'http://some-unregistered-website.com'
            self.headers['Origin'] = origin
            driver = MockDriver.return_value

            response = await self.send_metric()

            self.assertEqual(response.status, 204)
            self.assert_control(response, 'Allow-Origin', origin)
            MockDriver.assert_called_once_with(
                udp_port=config['databases']['udp']['udp_port'])
            driver.write.assert_called_once_with(self.user, self.points)

    @asynctest
    async def cant_send_metric_if_wrong_public_key(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            self.set_auth(DB_USER, 'bogus-key')
            driver = MockDriver.return_value

            response = await self.send_metric()

            self.assertEqual(response.status, 401)
            self.assertFalse(driver.write.called)

    @asynctest
    async def cant_send_metric_if_wrong_origin(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            self.set_origin('bogus-origin')
            driver = MockDriver.return_value

            response = await self.send_metric()

            self.assertEqual(response.status, 403)
            self.assertFalse(driver.write.called)

    @asynctest
    async def cant_send_metric_if_database_not_found(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            self.set_auth('bogus-db', DB_CONF['public_key'])
            driver = MockDriver.return_value

            response = await self.send_metric()

            self.assertEqual(response.status, 401)
            self.assertFalse(driver.write.called)

    @asynctest
    async def cant_send_metric_if_bad_metric_format(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            driver.write.side_effect = MalformedDataError('oops...')

            response = await self.send_metric()

            self.assertEqual(response.status, 400)

    @asynctest
    async def cant_send_metric_if_backend_fails(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            driver.write.side_effect = RuntimeError('oops...')

            response = await self.send_metric()

            self.assertEqual(response.status, 500)


class ManualTest(AppTestCase):
    @asynctest
    async def loads_manual_test_page(self):
        response = await self.client.get('/manual-test')
        content = await response.text()

        self.assertEqual(response.status, 200)
        self.assertIn('<body', content)

    @asynctest
    async def cannot_load_manual_test_if_not_configured(self):
        with patch.dict(config, {'manual_test_page': False}):
            response = await self.client.get('/manual-test')

            self.assertEqual(response.status, 404)


class StaticTest(AppTestCase):
    @asynctest
    async def loads_js_file(self):
        response = await self.client.get('/static/js/jquery-3.1.0.min.js')
        content = await response.text()

        self.assertEqual(response.status, 200)
        self.assertIn('jQuery', content)
