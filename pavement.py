import getpass
import os

from paver.easy import (
    task, sh, cmdopts, consume_args, Bunch, options, call_task, path, needs)


VR_URL = os.environ.get('VELOCIRAPTOR_URL', 'https://deploy.yougov.net')
CURRENT_VENV = os.environ.get('VIRTUAL_ENV')
CHEESESHOP = 'https://devpi.yougov.net/root/yg/+simple/'
APP = 'influxproxy'
REQUIREMENTS = 'requirements.txt'
REQUIREMENTS_TESTS = 'requirements_tests.txt'
REQUIREMENTS_JENKINS = 'requirements_jenkins.txt'
REQUIREMENTS_DEV = 'requirements_dev.txt'


if 'APP_SETTINGS_YAML' not in os.environ:
    os.environ['APP_SETTINGS_YAML'] = 'testing.yaml'


options(
    venv=Bunch(dir=CURRENT_VENV or 'venv'),
    yg_username=getpass.getuser(),
)


def env_do(tail, capture=False, **kw):
    """Run a command from the virtualenv."""
    command = '%s/bin/%s' % (options.venv.dir, tail)
    return sh(command, capture=capture, **kw)


@task
def lint():
    env_do('flake8 influxproxy --max-complexity 12')


@task
@consume_args
def test(args):
    if not args:
        args = ['tests']
    env_do('nosetests -c nose.cfg {}'.format(','.join(args)))


@task
@consume_args
@needs(['test', 'lint'])
def build(args):
    pass


@task
def run_dev():
    os.environ['APP_SETTINGS_YAML'] = 'development.yaml'
    env_do('python influxproxy/app.py')
