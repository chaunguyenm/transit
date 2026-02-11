from app.static.loader import Loader
from app.config import GTFS_STATIC_PATH
from sqlalchemy.exc import OperationalError
from app.db.postgres import init_db
import time
from fastapi import FastAPI, Request
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

app = FastAPI()

REQUEST_COUNT = Counter("http_requests_total", "Total number of HTTP requests")

@app.get("/")
def home():
    return {"message": "Hello!"}

@app.middleware("http")
async def count_requests(request: Request, call_next):
    REQUEST_COUNT.inc()
    response = await call_next(request)
    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# def main():
#     print("Starting!")
#     print(GTFS_STATIC_PATH)
#     for _ in range(10):
#         try:
#             init_db()

#             loader = Loader(GTFS_STATIC_PATH)
#             loader.load()
#             print("GTFS static data loaded into PostgreSQL.")
            
#             break
#         except OperationalError:
#             print("Waiting for PostgreSQL to be ready...")
#             time.sleep(3)


# if __name__ == "__main__":
#     main()