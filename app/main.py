import asyncio
import time

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.exc import OperationalError

from app.db.postgres import init_db
from app.metrics.registry import REQUEST_COUNT
from app.realtime.loader import worker

app = FastAPI()


@app.on_event("startup")
async def startup():
    print("Starting up...")
    # Initialize database with session ready for query
    for _ in range(10):
        try:
            init_db()
            print("PostgreSQL initialized.")
            break
        except OperationalError:
            print("Waiting for PostgreSQL to be ready...")
            time.sleep(3)

    # Start cronjob to update real-time data
    print("Starting cronjob to poll GTFS real-time data...")
    asyncio.create_task(worker())


@app.middleware("http")
async def count_requests(request: Request, call_next):
    REQUEST_COUNT.inc()
    response = await call_next(request)
    return response


@app.get("/")
def home():
    return {"message": "Hello!"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
