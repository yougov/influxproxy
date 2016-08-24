import base64
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


class MetricPostTest(AppTestCase):
    @asynctest
    async def sends_metric_to_driver(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            origin = DB_CONF['allow_from'][0]
            public_key = DB_CONF['public_key']
            authorization = base64.b64encode(
                '{}:{}'.format(DB_USER, public_key).encode('utf-8'))
            points = ['point1', 'point2']
            data = json.dumps(points).encode('utf-8')

            response = await self.client.post('/metric', data=data, headers={
                'Authorization': 'Basic {}'.format(
                    authorization.decode('utf-8')),
                'Content-Type': 'application/json',
                'Origin': origin,
            })

            self.assertEqual(response.status, 204)
            driver.write.assert_called_once_with(DB_USER, points)

    @asynctest
    async def cant_send_metric_if_wrong_public_key(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            origin = DB_CONF['allow_from'][0]
            public_key = 'bogus-key'
            authorization = base64.b64encode(
                '{}:{}'.format(DB_USER, public_key).encode('utf-8'))
            points = ['point1', 'point2']
            data = json.dumps(points).encode('utf-8')

            response = await self.client.post('/metric', data=data, headers={
                'Authorization': 'Basic {}'.format(
                    authorization.decode('utf-8')),
                'Content-Type': 'application/json',
                'Origin': origin,
            })

            self.assertEqual(response.status, 401)
            self.assertFalse(driver.write.called)

    @asynctest
    async def cant_send_metric_if_wrong_origin(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            origin = 'bogus-origin'
            public_key = DB_CONF['public_key']
            authorization = base64.b64encode(
                '{}:{}'.format(DB_USER, public_key).encode('utf-8'))
            points = ['point1', 'point2']
            data = json.dumps(points).encode('utf-8')

            response = await self.client.post('/metric', data=data, headers={
                'Authorization': 'Basic {}'.format(
                    authorization.decode('utf-8')),
                'Content-Type': 'application/json',
                'Origin': origin,
            })

            self.assertEqual(response.status, 403)
            self.assertFalse(driver.write.called)

    @asynctest
    async def cant_send_metric_if_database_not_found(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            origin = DB_CONF['allow_from'][0]
            public_key = DB_CONF['public_key']
            authorization = base64.b64encode(
                '{}:{}'.format('bogus-db', public_key).encode('utf-8'))
            points = ['point1', 'point2']
            data = json.dumps(points).encode('utf-8')

            response = await self.client.post('/metric', data=data, headers={
                'Authorization': 'Basic {}'.format(
                    authorization.decode('utf-8')),
                'Content-Type': 'application/json',
                'Origin': origin,
            })

            self.assertEqual(response.status, 401)
            self.assertFalse(driver.write.called)

    @asynctest
    async def cant_send_metric_if_auth_not_basic(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            origin = DB_CONF['allow_from'][0]
            public_key = DB_CONF['public_key']
            authorization = base64.b64encode(
                '{}:{}'.format(DB_USER, public_key).encode('utf-8'))
            points = ['point1', 'point2']
            data = json.dumps(points).encode('utf-8')

            response = await self.client.post('/metric', data=data, headers={
                'Authorization': 'Bearer {}'.format(
                    authorization.decode('utf-8')),
                'Content-Type': 'application/json',
                'Origin': origin,
            })

            self.assertEqual(response.status, 400)
            self.assertFalse(driver.write.called)

    @asynctest
    async def cant_send_metric_if_auth_not_decodable(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            origin = DB_CONF['allow_from'][0]
            points = ['point1', 'point2']
            data = json.dumps(points).encode('utf-8')

            response = await self.client.post('/metric', data=data, headers={
                'Authorization': 'Basic {}'.format('bogus-auth'),
                'Content-Type': 'application/json',
                'Origin': origin,
            })

            self.assertEqual(response.status, 400)
            self.assertFalse(driver.write.called)

    @asynctest
    async def cant_send_metric_if_auth_not_splittable(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            origin = DB_CONF['allow_from'][0]
            public_key = DB_CONF['public_key']
            authorization = base64.b64encode(
                '{}:{}'.format(DB_USER, public_key).encode('utf-8'))
            points = ['point1', 'point2']
            data = json.dumps(points).encode('utf-8')

            response = await self.client.post('/metric', data=data, headers={
                'Authorization': authorization.decode('utf-8'),
                'Content-Type': 'application/json',
                'Origin': origin,
            })

            self.assertEqual(response.status, 400)
            self.assertFalse(driver.write.called)

    @asynctest
    async def cant_send_metric_if_bad_metric_format(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            origin = DB_CONF['allow_from'][0]
            public_key = DB_CONF['public_key']
            authorization = base64.b64encode(
                '{}:{}'.format(DB_USER, public_key).encode('utf-8'))
            points = ['point1', 'point2']
            data = json.dumps(points).encode('utf-8')
            driver.write.side_effect = MalformedDataError('oops...')

            response = await self.client.post('/metric', data=data, headers={
                'Authorization': 'Basic {}'.format(
                    authorization.decode('utf-8')),
                'Content-Type': 'application/json',
                'Origin': origin,
            })

            self.assertEqual(response.status, 400)

    @asynctest
    async def cant_send_metric_if_backend_fails(self):
        with patch('influxproxy.app.InfluxDriver') as MockDriver:
            driver = MockDriver.return_value
            origin = DB_CONF['allow_from'][0]
            public_key = DB_CONF['public_key']
            authorization = base64.b64encode(
                '{}:{}'.format(DB_USER, public_key).encode('utf-8'))
            points = ['point1', 'point2']
            data = json.dumps(points).encode('utf-8')
            driver.write.side_effect = RuntimeError('oops...')

            response = await self.client.post('/metric', data=data, headers={
                'Authorization': 'Basic {}'.format(
                    authorization.decode('utf-8')),
                'Content-Type': 'application/json',
                'Origin': origin,
            })

            self.assertEqual(response.status, 500)
