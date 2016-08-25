#!/usr/bin/env python

import sys
import requests


def check(name, actual, expected):
    assert expected == actual, 'Expected {} {}, was actually {}'.format(
        name, expected, actual)


def host_running(host, port):
    r = requests.get(
        'http://{}:{}/ping'.format(host, port), allow_redirects=False)
    check('status_code', r.status_code, 200)
    check('content', r.content, b'pong')


def main():
    host, port = sys.argv[1], sys.argv[2]
    host_running(host, port)


if __name__ == '__main__':
    main()
