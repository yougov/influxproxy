from influxdb import InfluxDBClient

from influxproxy.configuration import config


class InfluxDriver:
    def __init__(self):
        backend_conf = config['backend']
        self.client = InfluxDBClient(
            backend_conf['host'], backend_conf['port'],
            backend_conf['username'], backend_conf['password'],
            use_udp=True, udp_port=backend_conf['udp_port'])

    def create_databases(self):
        for db in sorted(config['databases']):
            self.client.create_database(db)

    def write(self, database, points):
        if not isinstance(points, list):
            points = [points]
        self.client.write_points(points, database=database)
