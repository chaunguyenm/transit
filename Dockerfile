FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code
COPY . /code

ENV PYTHONPATH=/code:/code/gtfsdb:/code/gtfsdb/gtfsdb
ENV PATH="/code/.venv/bin:$PATH"

RUN uv sync --locked

EXPOSE 9100

CMD ["fastapi", "run", "app/main.py", "--port", "9100"]
