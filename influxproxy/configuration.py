import logging
import os
from pathlib import Path

import yaml


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('influxproxy')
config = yaml.load(open(os.environ['APP_SETTINGS_YAML']))


PORT = int(os.environ.get('PORT', None) or config.get('port', 8765))
DEBUG = bool(os.environ.get('DEBUG', False) or config.get('debug', False))
PROJECT_ROOT = Path(__file__).parent.parent
