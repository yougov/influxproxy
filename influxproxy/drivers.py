from influxdb import InfluxDBClient

from influxproxy.configuration import config


MANDATORY_FIELDS = ('measurement', 'time', 'fields')


class MalformedDataError(ValueError):
    """Raised when the data is malformed."""


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
        self._validate_points(points)
        self.client.write_points(points, database=database)

    def _validate_points(self, points):
        try:
            for point in points:
                self._validate_point(point)
        except Exception as e:
            raise MalformedDataError(str(e))

    def _validate_point(self, point):
        if not all(field in point for field in MANDATORY_FIELDS):
            raise ValueError('Point %s should contain these fields: %s',
                             point, MANDATORY_FIELDS)
