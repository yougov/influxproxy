import sys
import os

from setuptools import setup, find_packages


version = '0.1.1'


setup(name='influxproxy',
      version=version,
      description="A proxy to InfluxDB",
      long_description="""""",
      classifiers=[],
      keywords='influxdb metrics python',
      author='Diogo Baeder',
      author_email='diogo.baeder@yougov.com',
      url='',
      license='MIT License',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          'aiohttp>=0.22.5',
          'aiohttp_jinja2>=0.8.0',
          'influxdb>=3.0.0',
          'PyYAML>=3.11',
          #'uvloop>=0.5.2',  # Breaks static file serving. Will try later.
          'cchardet>=1.0.0',
          'gunicorn>=19.6.0',
      ],
      dependency_links=['https://devpi.yougov.net/root/yg/'],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
