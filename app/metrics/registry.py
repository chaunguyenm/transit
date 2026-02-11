from prometheus_client import Gauge, Counter, Histogram


# Active vehicle is defined as a vehicle with an update within a certain time.
vehicles_active = Gauge(
    "gtfs_vehicles_active",
    "Number of active vehicles"
)

# Active trip is defined as a trip being served by an active vehicle.
trips_active = Gauge(
    "gtfs_trips_active",
    "Number of active trips"
)

# Active route is defined as a route of an active trip.
routes_active = Gauge(
    "gtfs_routes_active",
    "Number of active routes"
)

gtfs_trip_delay_seconds = Gauge(
    "gtfs_trip_delay_seconds",
    "Current average trip delay in seconds",
    ["route_id"]
)

gtfs_stop_skipped = Gauge(
    "gtfs_stop_skipped",
    "Current average number of stops skipped per trip",
    ["route_id"]
)

gtfs_trip_on_time_total = Gauge(
    "gtfs_trip_on_time_total",
    "Trips by on-time status",
    ["route_id", "status"]  # early | on_time | late
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

REQUEST_COUNT = Counter("http_requests_total", "Total number of HTTP requests")
