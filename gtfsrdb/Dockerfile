FROM python:3.11-slim

RUN pip install protobuf==3.20.3 psycopg2-binary sqlalchemy

WORKDIR /code
COPY . /code

ENV PYTHONPATH=/code

ENTRYPOINT ["python", "gtfsrdb.py"]
