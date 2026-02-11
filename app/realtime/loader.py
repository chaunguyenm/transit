import asyncio
from app.metrics.registry import vehicles_active, trips_active, routes_active, gtfs_trip_on_time_total, gtfs_trip_delay_seconds, gtfs_stop_skipped
from google.transit import gtfs_realtime_pb2
from app.config import GTFS_RT_FEEDS
from app.db.postgres import Session, Trip, StopTime
from sqlalchemy import select
from app.config import DEBUG
from collections import defaultdict
from datetime import datetime, date, time, timedelta

session = Session()


async def worker():
    while True:
        feed = fetch()
        process_vehicle_positions(feed["vehicle_positions"])
        process_trip_updates(feed["trip_updates"])

        await asyncio.sleep(15)


def fetch():
    trip_feed = gtfs_realtime_pb2.FeedMessage()
    vehicle_feed = gtfs_realtime_pb2.FeedMessage()

    trip_updates_pb = GTFS_RT_FEEDS["trip_updates"]
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
            statement = select(Trip.route_id).where(
                Trip.trip_id == vp.trip.trip_id)
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


EARLY_THRESHOLD = -60     # seconds
LATE_THRESHOLD = 300      # seconds
BUNCHING_THRESHOLD = 120  # seconds


def classify_delay(delay_seconds: float) -> str:
    if delay_seconds < EARLY_THRESHOLD:
        return "early"
    elif delay_seconds > LATE_THRESHOLD:
        return "late"
    return "on_time"


def process_trip_updates(trip_updates):
    delays_by_route = defaultdict(list)
    skips_by_route = defaultdict(list)

    for tu in trip_updates:
        total_delay, stops, skips = 0, 0, 0

        if not tu.trip.trip_id:
            continue
        trip_id = tu.trip.trip_id

        for stu in tu.stop_time_update:
            stops += 1
            if not stu.arrival and not stu.departure:
                skips += 1
            realtime = None
            if stu.arrival:
                if stu.arrival.time:
                    realtime = stu.arrival.time
                else:
                    total_delay += stu.arrival.delay
            else:
                if stu.departure.time:
                    realtime = stu.departure.time
                else:
                    total_delay += stu.departure.delay

            if realtime is not None:
                if stu.stop_id:
                    statement = select(StopTime.arrival_time).where(
                        StopTime.trip_id == trip_id,
                        StopTime.stop_id == stu.stop_id)
                else:
                    statement = select(StopTime.arrival_time).where(
                        StopTime.trip_id == trip_id,
                        StopTime.stop_sequence == stu.stop_sequence)
                arrival_time = session.scalars(statement).first()
                scheduled = scheduled_to_epoch(arrival_time)

                delay = realtime - scheduled
                total_delay += delay

        avg_delay_per_stop = float(total_delay) / stops
        statement = select(Trip.route_id).where(Trip.trip_id == trip_id)
        route = session.scalars(statement).first()
        delays_by_route[route].append(avg_delay_per_stop)

        skip_ratio = float(skips) / stops
        skips_by_route[route].append(skip_ratio)

    if DEBUG:
        print("delays_by_route", delays_by_route)
        print("skips_by_route", skips_by_route)

    # update route status count
    for route, avg_delays in delays_by_route.items():
        on_time_per_route, early_per_route, late_per_route = 0, 0, 0
        for avg_delay in avg_delays:
            status = classify_delay(avg_delay)
            if status == "on_time":
                on_time_per_route += 1
            elif status == "early":
                early_per_route += 1
            else:
                late_per_route += 1
        gtfs_trip_on_time_total.labels(
            route_id=route, status="on_time").set(on_time_per_route)
        gtfs_trip_on_time_total.labels(
            route_id=route, status="early").set(early_per_route)
        gtfs_trip_on_time_total.labels(
            route_id=route, status="late").set(late_per_route)

    # update average delay
    for route, avg_delays in delays_by_route.items():
        avg_delay = sum(avg_delays) / len(avg_delays)
        gtfs_trip_delay_seconds.labels(
            route_id=route
        ).set(avg_delay)

    # update average number of stops skipped
    for route, skip_ratios in skips_by_route.items():
        avg_skip_ratio = sum(skip_ratios) / len(skip_ratios)
        gtfs_stop_skipped.labels(route_id=route).set(avg_skip_ratio)


def scheduled_to_epoch(seconds_since_midnight):
    today = date.today()
    dt = datetime.combine(today, time(0, 0)) + \
        timedelta(seconds=seconds_since_midnight)
    return int(dt.timestamp())

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
