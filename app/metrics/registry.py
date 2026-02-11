from prometheus_client import Gauge, Counter, Histogram

EARLY_THRESHOLD = -60     # seconds
LATE_THRESHOLD = 300      # seconds
BUNCHING_THRESHOLD = 120  # seconds

def classify_delay(delay_seconds: float) -> str:
    if delay_seconds < EARLY_THRESHOLD:
        return "early"
    elif delay_seconds > LATE_THRESHOLD:
        return "late"
    return "on_time"

vehicles_active = Gauge(
    "gtfs_vehicles_active",
    "Number of active vehicles"
)

trips_active = Gauge(
    "gtfs_trips_active",
    "Number of active trips"
)

routes_active = Gauge(
    "gtfs_routes_active",
    "Number of active routes"
)

gtfs_trip_delay_seconds = Gauge(
    "gtfs_trip_delay_seconds",
    "Current average trip delay in seconds",
    ["agency_id", "route_id"]
)

gtfs_trip_on_time_total = Counter(
    "gtfs_trip_on_time_total",
    "Trips by on-time status",
    ["agency_id", "route_id", "status"]  # early | on_time | late
)

gtfs_trip_cancelled_total = Counter(
    "gtfs_trip_cancelled_total",
    "Cancelled trips",
    ["agency_id", "route_id"]
)

gtfs_headway_seconds = Gauge(
    "gtfs_headway_seconds",
    "Current average headway between vehicles",
    ["agency_id", "route_id", "direction_id"]
)

gtfs_bunching_events_total = Counter(
    "gtfs_bunching_events_total",
    "Detected vehicle bunching events",
    ["agency_id", "route_id"]
)

