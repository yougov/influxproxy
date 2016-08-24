import socket
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from influxdb.client import InfluxDBClient
from nose.tools import istest

from influxproxy.configuration import config
from influxproxy.drivers import InfluxDriver, MalformedDataError


class InfluxDriverTest(TestCase):
    def setUp(self):
        self.driver = InfluxDriver()
        self.driver.client = MagicMock()

    def create_points(self):
        points = [
            {
                'measurement': 'my_metrics',
                'time': datetime.utcnow().isoformat(),
                'fields': {
                    'value': 1234,
                }
            },
            {
                'measurement': 'my_metrics_2',
                'time': datetime.utcnow().isoformat(),
                'fields': {
                    'value': 2345,
                }
            },
        ]

        return points

    @istest
    def starts_with_influx_client(self):
        backend_conf = config['backend']

        driver = InfluxDriver()

        host = socket.gethostbyname(backend_conf['host'])
        self.assertIsInstance(driver.client, InfluxDBClient)
        self.assertEqual(driver.client._host, host)
        self.assertEqual(driver.client._port, backend_conf['port'])
        self.assertEqual(driver.client.udp_port, backend_conf['udp_port'])
        self.assertEqual(driver.client._username, backend_conf['username'])
        self.assertEqual(driver.client._password, backend_conf['password'])

    @istest
    def starts_with_alternative_udp_port(self):
        driver = InfluxDriver(udp_port=1234)

        self.assertEqual(driver.client.udp_port, 1234)

    @istest
    def creates_databases(self):
        with patch.dict(
                config['databases'], {'db1': 'foo', 'db2': 'bar'}, clear=True):
            self.driver.create_databases()

        self.assertEqual(self.driver.client.create_database.mock_calls, [
            call('db1'),
            call('db2'),
        ])

    @istest
    def writes_points_to_backend(self):
        points = self.create_points()

        self.driver.write('my_database', points)

        self.driver.client.write_points.assert_called_once_with(
            points, database='my_database')

    @istest
    def writes_single_point_to_backend(self):
        points = self.create_points()[0]

        self.driver.write('my_database', points)

        self.driver.client.write_points.assert_called_once_with(
            [points], database='my_database')

    @istest
    def cant_write_if_measurement_missing(self):
        points = self.create_points()
        del points[1]['measurement']

        with self.assertRaises(MalformedDataError):
            self.driver.write('my_database', points)
