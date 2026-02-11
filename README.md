# Public Transit Monitoring

This project monitors public transport operations in real time using GTFS static
and GTFS-realtime data. It exposes operational and service-quality metrics via
Prometheus.

## Usage

Clone the project to your local machine.

```bash
git clone https://github.com/chaunguyenm/transit.git
cd transit
```

Provide the required environment variables in a `.env` file with the following
example format.

```
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=transit

DEBUG=true
POLL_INTERVAL_SECONDS=15
PROMETHEUS_PORT=9100
```

Run the Docker containers.

```bash
docker-compose up --build
```

The app will be running at port 9100, and Prometheus at port 9090.

## Roadmap

- Export additional service performance metrics.
- Add Grafana dashboarding.
- Implement reasoning/prediction based on past data.
