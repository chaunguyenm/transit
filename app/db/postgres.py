from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import (POSTGRES_USER, POSTGRES_PASSWORD,
                        POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, DEBUG)

Base = declarative_base()
CONNECTION_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(CONNECTION_URL, echo=DEBUG)
Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("PostgreSQL tables created/verified.")
