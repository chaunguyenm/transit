from app.config import (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, DEBUG)
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Trip(Base):
    __tablename__ = 'trips'

    route_id = Column(String, nullable=False)
    trip_id = Column(String, primary_key=True)
    direction_id = Column(Integer)


class StopTime(Base):
    __tablename__ = 'stop_times'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String, nullable=False)
    stop_id = Column(String, nullable=False)
    arrival_time = Column(Integer, nullable=False)
    stop_sequence = Column(Integer, nullable=False)


CONNECTION_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(CONNECTION_URL, echo=DEBUG)
Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("PostgreSQL tables created/verified.")
