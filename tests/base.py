from functools import wraps

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from nose.tools import istest

from influxproxy.app import create_app


class AppTestCase(AioHTTPTestCase):
    def get_app(self, loop):
        return create_app(loop)

    def assert_control(self, response, access_control, expected):
        self.assertEqual(
            response.headers['Access-Control-{}'.format(access_control)],
            expected)


def asynctest(f):
    return wraps(f)(
        istest(
            unittest_run_loop(f)
        )
    )
