import csv

from app.db.postgres import Session, Trip, StopTime


class Loader:
    def __init__(self, path):
        self.path = path

    def load(self):
        session = Session()
        try:
            self._load_trips(session)
            self._load_stop_times(session)
            session.commit()
        finally:
            session.close()

    def _load_trips(self, session):
        trips_file = f"{self.path}/trips.txt"
        with open(trips_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trip = Trip(
                    trip_id=row["trip_id"],
                    route_id=row["route_id"],
                    direction_id=int(row["direction_id"]) if row.get(
                        "direction_id") else None
                )
                session.merge(trip)

    def _load_stop_times(self, session):
        stop_times_file = f"{self.path}/stop_times.txt"
        with open(stop_times_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                st = StopTime(
                    trip_id=row["trip_id"],
                    stop_id=row["stop_id"],
                    arrival_time=self._parse_time(row["arrival_time"]),
                    stop_sequence=int(row["stop_sequence"])
                )
                session.add(st)

    @staticmethod
    def _parse_time(time_str: str) -> int:
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
