import asyncio
from app.metrics.registry import vehicles_active, trips_active, routes_active
from google.transit import gtfs_realtime_pb2
from app.config import GTFS_RT_FEEDS
from app.db.postgres import Session, Trip
from sqlalchemy import select
from app.config import DEBUG

session = Session()

async def worker():
    while True:
        feed = fetch()
        # process_trip_updates(feed.trip_updates, static_trip_lookup)
        # process_cancellations(feed.trip_updates, static_trip_lookup)
        # process_headways(feed.vehicle_positions)
        process_vehicle_positions(feed["vehicle_positions"])

        await asyncio.sleep(15)


def fetch():
    trip_feed = gtfs_realtime_pb2.FeedMessage()
    vehicle_feed = gtfs_realtime_pb2.FeedMessage()

    trip_updates_pb = GTFS_RT_FEEDS["trips"]
    vehicle_positions_pb = GTFS_RT_FEEDS["vehicle_positions"]

    trip_updates = []
    with open(trip_updates_pb, "rb") as f:
        trip_feed.ParseFromString(f.read())
        for entity in trip_feed.entity:
            if entity.HasField("trip_update"):
                trip_updates.append(entity.trip_update)

    vehicle_positions = []
    with open(vehicle_positions_pb, "rb") as f:
        vehicle_feed.ParseFromString(f.read())
        for entity in vehicle_feed.entity:
            if entity.HasField("vehicle"):
                vehicle_positions.append(entity.vehicle)

    return {
        "trip_updates": trip_updates,
        "vehicle_positions": vehicle_positions,
    }


def process_vehicle_positions(vehicle_positions):
    updated_active_vehicles, updated_active_trips, updated_active_routes = set(), set(), set()
    for vp in vehicle_positions:
        if vp.vehicle.id:
            updated_active_vehicles.add(vp.vehicle.id)
        if vp.trip.trip_id:
            updated_active_trips.add(vp.trip.trip_id)
            statement = select(Trip.route_id).where(Trip.trip_id == vp.trip.trip_id)
            routes = session.scalars(statement).all()
            for route in routes:
                updated_active_routes.add(route)
    vehicles_active.set(len(updated_active_vehicles))
    trips_active.set(len(updated_active_trips))
    routes_active.set(len(updated_active_routes))

    if DEBUG:
        print("active_vehicles", updated_active_vehicles)
        print("active_trips", updated_active_trips)
        print("active_routes", updated_active_routes)
        

# def process_trip_updates(trip_updates, static_trip_lookup):
#     """
#     trip_updates: list of GTFS-RT TripUpdate messages
#     static_trip_lookup: dict[trip_id] -> {route_id, stop_times}
#     """

#     delays_by_route = {}

#     for tu in trip_updates:
#         trip_id = tu.trip.trip_id
#         if trip_id not in static_trip_lookup:
#             continue

#         route_id = static_trip_lookup[trip_id]["route_id"]

#         # pick a reference stop (first upcoming stop is common)
#         if not tu.stop_time_update:
#             continue

#         stu = tu.stop_time_update[0]

#         if not stu.arrival or not stu.arrival.time:
#             continue

#         scheduled = static_trip_lookup[trip_id]["stop_times"][0]["arrival_time"]
#         realtime = stu.arrival.time

#         delay = realtime - scheduled

#         delays_by_route.setdefault(route_id, []).append(delay)

#         status = classify_delay(delay)
#         gtfs_trip_on_time_total.labels(
#             route_id=route_id,
#             status=status
#         ).inc()

#     # update average delay gauges
#     for route_id, delays in delays_by_route.items():
#         avg_delay = sum(delays) / len(delays)
#         gtfs_trip_delay_seconds.labels(
#             route_id=route_id
#         ).set(avg_delay)

# def process_cancellations(trip_updates, static_trip_lookup):
#     for tu in trip_updates:
#         if tu.trip.schedule_relationship != 2:  # CANCELED
#             continue

#         trip_id = tu.trip.trip_id
#         if trip_id not in static_trip_lookup:
#             continue

#         route_id = static_trip_lookup[trip_id]["route_id"]

#         gtfs_trip_cancelled_total.labels(
#             route_id=route_id
#         ).inc()

# def process_headways(
#     vehicle_positions,
#     bunching_threshold: int
# ):
#     """
#     vehicle_positions:
#       dict[(route_id, direction_id)] -> list of vehicle timestamps
#     """

#     for (route_id, direction_id), times in vehicle_positions.items():
#         if len(times) < 2:
#             continue

#         times.sort()
#         headways = [
#             times[i + 1] - times[i]
#             for i in range(len(times) - 1)
#         ]

#         avg_headway = sum(headways) / len(headways)

#         gtfs_headway_seconds.labels(
#             route_id=route_id,
#             direction_id=direction_id
#         ).set(avg_headway)

#         for h in headways:
#             if h < bunching_threshold:
#                 gtfs_bunching_events_total.labels(
#                     route_id=route_id
#                 ).inc()
