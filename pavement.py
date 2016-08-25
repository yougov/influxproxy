import getpass
import os

from paver.easy import (
    BuildFailure,
    Bunch,
    call_task,
    cmdopts,
    consume_args,
    needs,
    options,
    path,
    sh,
    task,
)


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
    env_do('flake8 influxproxy tests --max-complexity 12')


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
@consume_args
def bump(args):
    """A thin wrapper around bumpversion."""
    env_do('bumpversion %s' % ' '.join(args))


@task
@consume_args
def release(args):
    """Peform a release.

    This will:

      - check there are no unpushed/unpulled commits
      - bump the version number and commit
      - release the package to the cheeseshop

    Example:

      $> paver release patch

    """
    # Check we don't have pending commits
    sh('git diff --quiet HEAD')

    # Check we don't have unstaged changes
    sh('git diff --cached --quiet HEAD')

    # Tag
    bumptypes = ['major', 'minor', 'patch']
    bumptype = args.pop()

    if not bumptype or bumptype not in bumptypes:
        raise BuildFailure('Unknown bumptype: %s != %s' % (
            bumptype, bumptypes))

    call_task('bump', args=['--verbose', bumptype])

    # Push
    sh('git push')
    sh('git push --tags')


@task
def run():
    env_do('gunicorn -c python:influxproxy.gunicorn influxproxy.main:app')


@task
def run_dev():
    os.environ['APP_SETTINGS_YAML'] = 'development.yaml'
    os.environ['RELOAD'] = '1'
    os.environ['DEBUG'] = '1'
    call_task('run')
