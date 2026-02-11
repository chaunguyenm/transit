import os
from pathlib import Path

def getenv_required(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


BASE_DIR = Path(__file__).resolve().parent

# Path to GTFS static files (trips.txt, stop_times.txt, etc.)
GTFS_STATIC_PATH = Path(
    os.getenv("GTFS_STATIC_PATH", BASE_DIR / "static")
)

# Poll interval for fetching GTFS-RT feeds (in seconds)
POLL_INTERVAL_SECONDS = int(
    os.getenv("POLL_INTERVAL_SECONDS", "15")
)

PROMETHEUS_PORT = int(
    os.getenv("PROMETHEUS_PORT", "9100")
)

POSTGRES_USER = getenv_required("POSTGRES_USER")
POSTGRES_PASSWORD = getenv_required("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "transit")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

GTFS_RT_FEEDS = {
    "trips": os.getenv(
        "GTFS_RT_TRIPS",
        str(BASE_DIR / "realtime" / "TripUpdates.pb"),
    ),
    "vehicle_positions": os.getenv(
        "GTFS_RT_VEHICLES",
        str(BASE_DIR / "realtime" / "VehiclePositions.pb"),
    ),
}

DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
