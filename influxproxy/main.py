from influxproxy.app import create_app
from influxproxy.drivers import InfluxDriver


driver = InfluxDriver()
driver.create_databases()
app = create_app(loop=None)
