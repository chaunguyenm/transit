import asyncio
from collections import defaultdict
from datetime import datetime, date, time, timedelta
import requests

from google.transit import gtfs_realtime_pb2
from sqlalchemy import select

from app.config import DEBUG, GTFS_RT_FEEDS
from app.db.postgres import Session, Trip, StopTime
from app.metrics.registry import vehicles_active, trips_active, routes_active, gtfs_trip_on_time_total, gtfs_trip_delay_seconds, gtfs_stop_skipped


session = Session()
trip_route_map = dict(
    session.execute(select(Trip.trip_id, Trip.route_id)).all()
)

stop_time_lookup = {}
rows = session.execute(
    select(
        StopTime.trip_id,
        StopTime.stop_id,
        StopTime.stop_sequence,
        StopTime.arrival_time
    )
).all()
for trip_id, stop_id, stop_seq, arrival in rows:
    stop_time_lookup.setdefault(trip_id, {})
    stop_time_lookup[trip_id][stop_id or stop_seq] = arrival


async def worker():
    while True:
        feed = fetch()
        process_vehicle_positions(feed["vehicle_positions"])
        process_trip_updates(feed["trip_updates"])
        if DEBUG:
            print("Finished updating metrics!")
        await asyncio.sleep(30)


def fetch():
    trip_feed = gtfs_realtime_pb2.FeedMessage()
    vehicle_feed = gtfs_realtime_pb2.FeedMessage()

    trip_updates_pb = GTFS_RT_FEEDS["trip_updates"]
    vehicle_positions_pb = GTFS_RT_FEEDS["vehicle_positions"]

    trip_updates = []
    trip_response = requests.get(trip_updates_pb)
    trip_feed.ParseFromString(trip_response.content)
    if DEBUG:
        print("TripUpdates feed timestamp:", trip_feed.header.timestamp)
        print("TripUpdates entity count:", len(trip_feed.entity))
    for entity in trip_feed.entity:
        if entity.HasField("trip_update"):
            trip_updates.append(entity.trip_update)

    vehicle_positions = []
    vehicle_response = requests.get(vehicle_positions_pb)
    vehicle_feed.ParseFromString(vehicle_response.content)
    if DEBUG:
        print("VehiclePositions feed timestamp:",
              vehicle_feed.header.timestamp)
        print("VehiclePositions entity count:", len(vehicle_feed.entity))
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
                arrival_time = None
                if stu.stop_id:
                    arrival_time = stop_time_lookup[trip_id][stu.stop_id]
                else:
                    arrival_time = stop_time_lookup[trip_id][stu.stop_sequence]
                if arrival_time is None:
                    print(
                        f"arrival_time not found for trip_id={trip_id} stop_id={stu.stop_id} stop_sequence={stu.stop_sequence}")
                    continue
                scheduled = scheduled_to_epoch(arrival_time)
                delay = realtime - scheduled
                total_delay += delay

            if not stu.arrival and not stu.departure:
                skips += 1
            stops += 1

        if stops != 0:
            avg_delay_per_stop = float(total_delay) / stops
            statement = select(Trip.route_id).where(Trip.trip_id == trip_id)
            route = trip_route_map.get(trip_id)
            delays_by_route[route].append(avg_delay_per_stop)

            skip_ratio = float(skips) / stops
            skips_by_route[route].append(skip_ratio)
        else:
            print(f"Skipped trip_id={trip_id}, no data found!")

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
    if seconds_since_midnight is None:
        raise TypeError()
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
